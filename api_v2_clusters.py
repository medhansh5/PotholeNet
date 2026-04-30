"""
PotholeNet v2.2 - Clusters API Endpoint

GET /v2/map/clusters endpoint returning GeoJSON formatted
road event data for frontend rendering with spatial aggregation.
"""

from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from clustering_service import ClusteringService, TelemetryPoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClustersAPI:
    """API handler for road events clustering"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.clustering_service = ClusteringService(eps_meters=5.0, min_samples=3)
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config.get('port', 5432)
            )
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return None
    
    def get_road_events_geojson(self, bounds: Optional[Dict] = None,
                              severity_filter: Optional[str] = None,
                              confidence_min: Optional[float] = None,
                              time_range: Optional[str] = None) -> Dict:
        """
        Get road events as GeoJSON
        
        Args:
            bounds: {'min_lat', 'max_lat', 'min_lng', 'max_lng'}
            severity_filter: 'low', 'medium', 'high'
            confidence_min: Minimum confidence score (0-1)
            time_range: '1h', '24h', '7d', '30d'
            
        Returns:
            GeoJSON FeatureCollection
        """
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build WHERE clause
                where_conditions = []
                params = []
                
                if bounds:
                    where_conditions.append("""
                        ST_Contains(
                            ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                            center_geom
                        )
                    """)
                    params.extend([
                        bounds['min_lng'], bounds['min_lat'],
                        bounds['max_lng'], bounds['max_lat']
                    ])
                
                if severity_filter:
                    where_conditions.append("severity = %s")
                    params.append(severity_filter)
                
                if confidence_min:
                    where_conditions.append("confidence_score >= %s")
                    params.append(confidence_min)
                
                if time_range:
                    time_condition = self._get_time_condition(time_range)
                    where_conditions.append(time_condition)
                    params.append(datetime.utcnow())
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"
                
                # Query for road events
                query = f"""
                    SELECT 
                        id,
                        event_id,
                        center_latitude,
                        center_longitude,
                        radius_meters,
                        point_count,
                        avg_z_magnitude,
                        max_z_magnitude,
                        confidence_score,
                        severity,
                        start_time,
                        end_time,
                        device_ids,
                        road_health_impact,
                        created_at,
                        -- GeoJSON geometry
                        ST_AsGeoJSON(
                            ST_Transform(center_geom, 4326),
                            6
                        ) as geometry,
                        -- Cluster circle for visualization
                        ST_AsGeoJSON(
                            ST_Transform(cluster_geom, 4326),
                            6
                        ) as cluster_geometry
                    FROM road_events
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT 1000
                """
                
                cur.execute(query, params)
                events = cur.fetchall()
                
                # Convert to GeoJSON FeatureCollection
                geojson = self._events_to_geojson(events)
                
                return geojson
                
        except Exception as e:
            logger.error(f"Error fetching road events: {str(e)}")
            return {"error": f"Database query failed: {str(e)}"}
        finally:
            conn.close()
    
    def _get_time_condition(self, time_range: str) -> str:
        """Generate time condition based on range"""
        time_conditions = {
            '1h': "created_at > %s - INTERVAL '1 hour'",
            '24h': "created_at > %s - INTERVAL '24 hours'",
            '7d': "created_at > %s - INTERVAL '7 days'",
            '30d': "created_at > %s - INTERVAL '30 days'"
        }
        return time_conditions.get(time_range, "TRUE")
    
    def _events_to_geojson(self, events: List[Dict]) -> Dict:
        """Convert road events to GeoJSON FeatureCollection"""
        features = []
        
        for event in events:
            # Main feature (center point)
            center_feature = {
                "type": "Feature",
                "geometry": json.loads(event['geometry']),
                "properties": {
                    "id": event['event_id'],
                    "type": "road_event_center",
                    "severity": event['severity'],
                    "confidence": float(event['confidence_score']),
                    "point_count": event['point_count'],
                    "avg_z_magnitude": float(event['avg_z_magnitude']),
                    "max_z_magnitude": float(event['max_z_magnitude']),
                    "radius_meters": float(event['radius_meters']),
                    "road_health_impact": float(event['road_health_impact']),
                    "device_count": len(event['device_ids']) if event['device_ids'] else 0,
                    "start_time": event['start_time'],
                    "end_time": event['end_time'],
                    "created_at": event['created_at'].isoformat() if event['created_at'] else None
                }
            }
            features.append(center_feature)
            
            # Optional: Cluster boundary feature
            if event.get('cluster_geometry'):
                boundary_feature = {
                    "type": "Feature",
                    "geometry": json.loads(event['cluster_geometry']),
                    "properties": {
                        "id": f"{event['event_id']}_boundary",
                        "type": "road_event_boundary",
                        "parent_event_id": event['event_id'],
                        "severity": event['severity'],
                        "confidence": float(event['confidence_score']),
                        "is_boundary": True
                    }
                }
                features.append(boundary_feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_events": len(events),
                "api_version": "2.2",
                "spatial_aggregation": "DBSCAN"
            }
        }
    
    def get_road_health_score(self, bounds: Dict[str, float]) -> Dict:
        """
        Calculate road health score for a specific bounding box
        
        Args:
            bounds: {'min_lat', 'max_lat', 'min_lng', 'max_lng'}
            
        Returns:
            Health score and related metrics
        """
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Call PostgreSQL function for health calculation
                query = """
                    SELECT 
                        calculate_road_health(%s, %s, %s, %s) as health_score,
                        COUNT(*) as event_count,
                        AVG(road_health_impact) as avg_impact,
                        MAX(road_health_impact) as max_impact,
                        AVG(point_count) as avg_points_per_event
                    FROM road_events
                    WHERE ST_Contains(
                        ST_SetSRID(ST_MakeEnvelope(%s, %s, %s, %s, 4326), 4326),
                        center_geom
                    )
                """
                
                cur.execute(query, [
                    bounds['min_lat'], bounds['max_lat'],
                    bounds['min_lng'], bounds['max_lng'],
                    bounds['min_lng'], bounds['min_lat'],
                    bounds['max_lng'], bounds['max_lat']
                ])
                
                result = cur.fetchone()
                
                if result:
                    return {
                        "health_score": float(result['health_score']),
                        "event_count": result['event_count'],
                        "avg_impact": float(result['avg_impact']) if result['avg_impact'] else 0,
                        "max_impact": float(result['max_impact']) if result['max_impact'] else 0,
                        "avg_points_per_event": float(result['avg_points_per_event']) if result['avg_points_per_event'] else 0,
                        "bounds": bounds,
                        "calculated_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "health_score": 100.0,
                        "event_count": 0,
                        "bounds": bounds,
                        "calculated_at": datetime.utcnow().isoformat()
                    }
                
        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            return {"error": f"Health calculation failed: {str(e)}"}
        finally:
            conn.close()
    
    def get_clustering_stats(self) -> Dict:
        """Get clustering statistics and performance metrics"""
        conn = self.get_db_connection()
        if not conn:
            return {"error": "Database connection failed"}
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get clustering statistics
                query = """
                    SELECT 
                        COUNT(*) as total_events,
                        AVG(point_count) as avg_points_per_cluster,
                        MAX(point_count) as max_points_in_cluster,
                        AVG(radius_meters) as avg_cluster_radius,
                        COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_severity_count,
                        COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium_severity_count,
                        COUNT(CASE WHEN severity = 'low' THEN 1 END) as low_severity_count,
                        AVG(confidence_score) as avg_confidence,
                        MAX(created_at) as latest_event,
                        MIN(created_at) as earliest_event
                    FROM road_events
                    WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
                """
                
                cur.execute(query)
                stats = cur.fetchone()
                
                if stats:
                    return {
                        "total_events": stats['total_events'],
                        "avg_points_per_cluster": float(stats['avg_points_per_cluster']) if stats['avg_points_per_cluster'] else 0,
                        "max_points_in_cluster": stats['max_points_in_cluster'],
                        "avg_cluster_radius": float(stats['avg_cluster_radius']) if stats['avg_cluster_radius'] else 0,
                        "severity_distribution": {
                            "high": stats['high_severity_count'],
                            "medium": stats['medium_severity_count'],
                            "low": stats['low_severity_count']
                        },
                        "avg_confidence": float(stats['avg_confidence']) if stats['avg_confidence'] else 0,
                        "latest_event": stats['latest_event'].isoformat() if stats['latest_event'] else None,
                        "earliest_event": stats['earliest_event'].isoformat() if stats['earliest_event'] else None,
                        "generated_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {"generated_at": datetime.utcnow().isoformat()}
                
        except Exception as e:
            logger.error(f"Error getting clustering stats: {str(e)}")
            return {"error": f"Stats query failed: {str(e)}"}
        finally:
            conn.close()

# Flask application for v2.2 API
app = Flask(__name__)

# Database configuration (should be environment variables in production)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'potholenet'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'port': int(os.getenv('DB_PORT', 5432))
}

# Initialize API
clusters_api = ClustersAPI(DB_CONFIG)

@app.route('/v2/map/clusters', methods=['GET'])
def get_clusters():
    """GET /v2/map/clusters - Return road events as GeoJSON"""
    
    # Parse query parameters
    bounds = None
    if request.args.get('bounds'):
        try:
            bounds_data = json.loads(request.args.get('bounds'))
            bounds = {
                'min_lat': float(bounds_data.get('min_lat')),
                'max_lat': float(bounds_data.get('max_lat')),
                'min_lng': float(bounds_data.get('min_lng')),
                'max_lng': float(bounds_data.get('max_lng'))
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return jsonify({"error": f"Invalid bounds parameter: {str(e)}"}), 400
    
    severity_filter = request.args.get('severity')
    if severity_filter and severity_filter not in ['low', 'medium', 'high']:
        return jsonify({"error": "Invalid severity filter. Use: low, medium, high"}), 400
    
    confidence_min = request.args.get('confidence_min')
    if confidence_min:
        try:
            confidence_min = float(confidence_min)
            if not (0 <= confidence_min <= 1):
                raise ValueError("Confidence must be between 0 and 1")
        except ValueError as e:
            return jsonify({"error": f"Invalid confidence_min: {str(e)}"}), 400
    
    time_range = request.args.get('time_range')
    if time_range and time_range not in ['1h', '24h', '7d', '30d']:
        return jsonify({"error": "Invalid time_range. Use: 1h, 24h, 7d, 30d"}), 400
    
    # Get road events
    result = clusters_api.get_road_events_geojson(
        bounds=bounds,
        severity_filter=severity_filter,
        confidence_min=confidence_min,
        time_range=time_range
    )
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/v2/health/score', methods=['GET'])
def get_health_score():
    """GET /v2/health/score - Calculate road health for bounds"""
    
    bounds = request.args.get('bounds')
    if not bounds:
        return jsonify({"error": "bounds parameter required"}), 400
    
    try:
        bounds_data = json.loads(bounds)
        bounds = {
            'min_lat': float(bounds_data.get('min_lat')),
            'max_lat': float(bounds_data.get('max_lat')),
            'min_lng': float(bounds_data.get('min_lng')),
            'max_lng': float(bounds_data.get('max_lng'))
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid bounds parameter: {str(e)}"}), 400
    
    result = clusters_api.get_road_health_score(bounds)
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/v2/clustering/stats', methods=['GET'])
def get_clustering_stats():
    """GET /v2/clustering/stats - Get clustering statistics"""
    result = clusters_api.get_clustering_stats()
    
    if 'error' in result:
        return jsonify(result), 500
    
    return jsonify(result)

@app.route('/v2/status', methods=['GET'])
def get_api_status():
    """GET /v2/status - API status and configuration"""
    return jsonify({
        "status": "healthy",
        "version": "2.2",
        "features": {
            "spatial_aggregation": True,
            "dbscan_clustering": True,
            "postgis_support": True,
            "road_health_scoring": True,
            "geojson_output": True
        },
        "endpoints": {
            "clusters": "/v2/map/clusters",
            "health_score": "/v2/health/score",
            "stats": "/v2/clustering/stats"
        },
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5001)
