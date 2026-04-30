-- PotholeNet v2.2 - PostgreSQL/PostGIS Database Migration
-- Spatial Aggregation Schema for Road Events

-- Enable PostGIS extension if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- ==========================================
-- RAW TELEMETRY TABLE (Enhanced)
-- ==========================================
CREATE TABLE IF NOT EXISTS raw_telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    z_axis_acceleration DECIMAL(8, 4) NOT NULL,
    x_axis_acceleration DECIMAL(8, 4),
    y_axis_acceleration DECIMAL(8, 4),
    z_magnitude DECIMAL(8, 4) NOT NULL,
    speed_kmh DECIMAL(6, 2),
    heading DECIMAL(6, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- PostGIS geometry column for spatial queries
    geom GEOMETRY(POINT, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
    ) STORED
);

-- Create spatial index on telemetry points
CREATE INDEX IF NOT EXISTS idx_raw_telemetry_geom ON raw_telemetry USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_raw_telemetry_timestamp ON raw_telemetry (timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_telemetry_device ON raw_telemetry (device_id);

-- ==========================================
-- ROAD EVENTS TABLE (New for v2.2)
-- ==========================================
CREATE TABLE IF NOT EXISTS road_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(100) UNIQUE NOT NULL,
    center_latitude DECIMAL(10, 8) NOT NULL,
    center_longitude DECIMAL(11, 8) NOT NULL,
    radius_meters DECIMAL(8, 2) NOT NULL,
    point_count INTEGER NOT NULL,
    avg_z_magnitude DECIMAL(8, 4) NOT NULL,
    max_z_magnitude DECIMAL(8, 4) NOT NULL,
    confidence_score DECIMAL(5, 4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    severity VARCHAR(10) NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    device_ids TEXT[], -- Array of device IDs that contributed to this event
    road_health_impact DECIMAL(5, 2) NOT NULL CHECK (road_health_impact >= 0 AND road_health_impact <= 100),
    cluster_algorithm VARCHAR(20) DEFAULT 'DBSCAN',
    eps_meters DECIMAL(6, 2) DEFAULT 5.0,
    min_samples INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- PostGIS geometry column for spatial queries
    center_geom GEOMETRY(POINT, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_MakePoint(center_longitude, center_latitude), 4326)
    ) STORED,
    
    -- PostGIS circle geometry for spatial queries
    cluster_geom GEOMETRY(POLYGON, 4326) GENERATED ALWAYS AS (
        ST_Buffer(center_geom, radius_meters)
    ) STORED
);

-- Create spatial indexes on road events
CREATE INDEX IF NOT EXISTS idx_road_events_center_geom ON road_events USING GIST (center_geom);
CREATE INDEX IF NOT EXISTS idx_road_events_cluster_geom ON road_events USING GIST (cluster_geom);
CREATE INDEX IF NOT EXISTS idx_road_events_severity ON road_events (severity);
CREATE INDEX IF NOT EXISTS idx_road_events_confidence ON road_events (confidence_score);
CREATE INDEX IF NOT EXISTS idx_road_events_created_at ON road_events (created_at);

-- ==========================================
-- EVENT-TELEMETRY RELATIONSHIP TABLE
-- Links road events to their constituent telemetry points
-- ==========================================
CREATE TABLE IF NOT EXISTS event_telemetry_links (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT REFERENCES road_events(id) ON DELETE CASCADE,
    telemetry_id BIGINT REFERENCES raw_telemetry(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(event_id, telemetry_id)
);

CREATE INDEX IF NOT EXISTS idx_event_links_event_id ON event_telemetry_links (event_id);
CREATE INDEX IF NOT EXISTS idx_event_links_telemetry_id ON event_telemetry_links (telemetry_id);

-- ==========================================
-- ROAD HEALTH ZONES TABLE
-- For calculating health scores in specific areas
-- ==========================================
CREATE TABLE IF NOT EXISTS road_health_zones (
    id BIGSERIAL PRIMARY KEY,
    zone_name VARCHAR(100) NOT NULL,
    bounds_lat_min DECIMAL(10, 8) NOT NULL,
    bounds_lat_max DECIMAL(10, 8) NOT NULL,
    bounds_lng_min DECIMAL(11, 8) NOT NULL,
    bounds_lng_max DECIMAL(11, 8) NOT NULL,
    health_score DECIMAL(5, 2) NOT NULL CHECK (health_score >= 0 AND health_score <= 100),
    event_count INTEGER DEFAULT 0,
    last_calculated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- PostGIS geometry for zone boundaries
    zone_geom GEOMETRY(POLYGON, 4326) GENERATED ALWAYS AS (
        ST_SetSRID(ST_MakeEnvelope(
            bounds_lng_min, bounds_lat_min,
            bounds_lng_max, bounds_lat_max,
            4326
        ), 4326)
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_health_zones_geom ON road_health_zones USING GIST (zone_geom);
CREATE INDEX IF NOT EXISTS idx_health_zones_score ON road_health_zones (health_score);

-- ==========================================
-- CLUSTERING CONFIGURATION TABLE
-- Store clustering parameters for different runs
-- ==========================================
CREATE TABLE IF NOT EXISTS clustering_config (
    id BIGSERIAL PRIMARY KEY,
    config_name VARCHAR(50) UNIQUE NOT NULL,
    eps_meters DECIMAL(6, 2) NOT NULL DEFAULT 5.0,
    min_samples INTEGER NOT NULL DEFAULT 3,
    cluster_algorithm VARCHAR(20) DEFAULT 'DBSCAN',
    active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert default clustering configuration
INSERT INTO clustering_config (config_name, eps_meters, min_samples, active)
VALUES 
    ('default', 5.0, 3, TRUE),
    ('high_density', 3.0, 5, FALSE),
    ('low_density', 10.0, 2, FALSE)
ON CONFLICT (config_name) DO NOTHING;

-- ==========================================
-- VIEWS FOR COMMON QUERIES
-- ==========================================

-- View for recent road events with enhanced data
CREATE OR REPLACE VIEW v_recent_road_events AS
SELECT 
    re.*,
    CASE 
        WHEN re.created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 'recent'
        WHEN re.created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 'today'
        ELSE 'older'
    END as time_category,
    -- Calculate event density (events per km²)
    (re.point_count::DECIMAL / (PI * (re.radius_meters^2) / 1000000)) as events_per_km2
FROM road_events re
WHERE re.created_at > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- View for road health statistics
CREATE OR REPLACE VIEW v_road_health_stats AS
SELECT 
    rhz.zone_name,
    rhz.health_score,
    rhz.event_count,
    rhz.last_calculated,
    COUNT(re.id) as current_events_in_zone,
    AVG(re.road_health_impact) as avg_impact_in_zone,
    MAX(re.road_health_impact) as max_impact_in_zone
FROM road_health_zones rhz
LEFT JOIN road_events re ON ST_Contains(rhz.zone_geom, re.center_geom)
GROUP BY rhz.id, rhz.zone_name, rhz.health_score, rhz.event_count, rhz.last_calculated;

-- ==========================================
-- STORED PROCEDURES FOR CLUSTERING OPERATIONS
-- ==========================================

-- Function to get telemetry points for clustering
CREATE OR REPLACE FUNCTION get_telemetry_for_clustering(
    p_device_ids TEXT[] DEFAULT NULL,
    p_start_time DOUBLE PRECISION DEFAULT NULL,
    p_end_time DOUBLE PRECISION DEFAULT NULL,
    p_limit INTEGER DEFAULT 10000
)
RETURNS TABLE (
    id BIGINT,
    device_id VARCHAR(50),
    timestamp DOUBLE PRECISION,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    z_magnitude DECIMAL(8, 4),
    speed_kmh DECIMAL(6, 2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rt.id,
        rt.device_id,
        rt.timestamp,
        rt.latitude,
        rt.longitude,
        rt.z_magnitude,
        rt.speed_kmh
    FROM raw_telemetry rt
    WHERE 
        (p_device_ids IS NULL OR rt.device_id = ANY(p_device_ids))
        AND (p_start_time IS NULL OR rt.timestamp >= p_start_time)
        AND (p_end_time IS NULL OR rt.timestamp <= p_end_time)
    ORDER BY rt.timestamp DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to create road events from clustering results
CREATE OR REPLACE FUNCTION create_road_event(
    p_event_id VARCHAR(100),
    p_center_lat DECIMAL(10, 8),
    p_center_lng DECIMAL(11, 8),
    p_radius DECIMAL(8, 2),
    p_point_count INTEGER,
    p_avg_z DECIMAL(8, 4),
    p_max_z DECIMAL(8, 4),
    p_confidence DECIMAL(5, 4),
    p_severity VARCHAR(10),
    p_start_time DOUBLE PRECISION,
    p_end_time DOUBLE PRECISION,
    p_device_ids TEXT[],
    p_health_impact DECIMAL(5, 2)
)
RETURNS BIGINT AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    INSERT INTO road_events (
        event_id, center_latitude, center_longitude, radius_meters,
        point_count, avg_z_magnitude, max_z_magnitude,
        confidence_score, severity, start_time, end_time,
        device_ids, road_health_impact
    ) VALUES (
        p_event_id, p_center_lat, p_center_lng, p_radius,
        p_point_count, p_avg_z, p_max_z,
        p_confidence, p_severity, p_start_time, p_end_time,
        p_device_ids, p_health_impact
    ) 
    RETURNING id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate road health for a bounding box
CREATE OR REPLACE FUNCTION calculate_road_health(
    p_lat_min DECIMAL(10, 8),
    p_lat_max DECIMAL(10, 8),
    p_lng_min DECIMAL(11, 8),
    p_lng_max DECIMAL(11, 8)
)
RETURNS DECIMAL(5, 2) AS $$
DECLARE
    v_bounds GEOMETRY(POLYGON, 4326);
    v_total_impact DECIMAL(10, 2);
    v_area DECIMAL(12, 2);
    v_health_score DECIMAL(5, 2);
BEGIN
    -- Create bounding box geometry
    v_bounds := ST_SetSRID(ST_MakeEnvelope(
        p_lng_min, p_lat_min, p_lng_max, p_lat_max, 4326
    ), 4326);
    
    -- Calculate total impact within bounds
    SELECT COALESCE(SUM(road_health_impact), 0) INTO v_total_impact
    FROM road_events
    WHERE ST_Contains(v_bounds, center_geom);
    
    -- Calculate area in km²
    v_area := ST_Area(v_bounds::geography) / 1000000; -- Convert m² to km²
    
    -- Calculate health score (100 - impact density)
    IF v_area > 0 THEN
        v_health_score := GREATEST(0, LEAST(100, 100 - (v_total_impact / v_area)));
    ELSE
        v_health_score := 100.0;
    END IF;
    
    RETURN v_health_score;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ==========================================

-- Update road health zones when new events are created
CREATE OR REPLACE FUNCTION update_road_health_zones()
RETURNS TRIGGER AS $$
BEGIN
    -- Update health scores for zones that contain this event
    UPDATE road_health_zones 
    SET 
        event_count = event_count + 1,
        health_score = calculate_road_health(
            bounds_lat_min, bounds_lat_max,
            bounds_lng_min, bounds_lng_max
        ),
        last_calculated = CURRENT_TIMESTAMP
    WHERE ST_Contains(zone_geom, NEW.center_geom);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger
CREATE TRIGGER trg_update_road_health
    AFTER INSERT ON road_events
    FOR EACH ROW
    EXECUTE FUNCTION update_road_health_zones();

-- ==========================================
-- INDEX OPTIMIZATIONS
-- ==========================================

-- Composite index for common event queries
CREATE INDEX IF NOT EXISTS idx_road_events_composite ON road_events 
(severity, created_at DESC, confidence_score DESC);

-- Partial index for high-confidence events
CREATE INDEX IF NOT EXISTS idx_road_events_high_confidence ON road_events (center_geom) 
WHERE confidence_score >= 0.8;

-- Partial index for recent events
CREATE INDEX IF NOT EXISTS idx_road_events_recent ON road_events (created_at) 
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days';

-- ==========================================
-- SAMPLE DATA FOR TESTING
-- ==========================================

-- Insert sample road health zones (Ghaziabad area)
INSERT INTO road_health_zones (zone_name, bounds_lat_min, bounds_lat_max, bounds_lng_min, bounds_lng_max, health_score)
VALUES 
    ('Ghaziabad Central', 28.6000, 28.7000, 77.4000, 77.5000, 85.5),
    ('Ghaziabad North', 28.7000, 28.8000, 77.4000, 77.5000, 92.1),
    ('Ghaziabad South', 28.5000, 28.6000, 77.4000, 77.5000, 78.3),
    ('Ghaziabad East', 28.6000, 28.7000, 77.5000, 77.6000, 81.7),
    ('Ghaziabad West', 28.6000, 28.7000, 77.3000, 77.4000, 88.9)
ON CONFLICT (zone_name) DO NOTHING;

COMMIT;

-- Migration completed successfully
-- Version: 2.2 - Spatial Aggregation
-- Features: DBSCAN clustering, PostGIS integration, Road Health scoring
