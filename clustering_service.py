"""
PotholeNet v2.2 - Spatial Aggregation Service

DBSCAN clustering implementation for aggregating raw telemetry points 
into actionable "Road Events" with spatial accuracy and performance optimization.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cdist
import math
import time
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TelemetryPoint:
    """Raw telemetry data point"""
    latitude: float
    longitude: float
    z_magnitude: float
    timestamp: float
    device_id: Optional[str] = None
    speed: Optional[float] = None

@dataclass
class RoadEvent:
    """Clustered road event with aggregated properties"""
    event_id: str
    center_lat: float
    center_lng: float
    radius_meters: float
    point_count: int
    avg_z_magnitude: float
    max_z_magnitude: float
    confidence_score: float
    severity: str  # 'low', 'medium', 'high'
    start_time: float
    end_time: float
    device_ids: List[str]
    road_health_impact: float  # 0-100 scale

class HaversineDistance:
    """Haversine distance calculator for accurate Earth curvature calculations"""
    
    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth
        Returns distance in meters
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in meters
        earth_radius = 6371000
        return earth_radius * c
    
    @staticmethod
    def distance_matrix(points: List[Tuple[float, float]]) -> np.ndarray:
        """
        Calculate distance matrix for all points using Haversine
        """
        n = len(points)
        distances = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = HaversineDistance.haversine(
                    points[i][0], points[i][1], points[j][0], points[j][1]
                )
                distances[i][j] = dist
                distances[j][i] = dist
        
        return distances

class DBSCANClusterer:
    """DBSCAN clustering with spatial distance metrics"""
    
    def __init__(self, eps_meters: float = 5.0, min_samples: int = 3):
        """
        Initialize DBSCAN clusterer
        
        Args:
            eps_meters: Maximum distance between points in same cluster (meters)
            min_samples: Minimum points required to form a cluster
        """
        self.eps_meters = eps_meters
        self.min_samples = min_samples
        self.last_cluster_time = 0
        
    def cluster_telemetry_points(self, telemetry_data: List[TelemetryPoint]) -> List[RoadEvent]:
        """
        Cluster telemetry points into road events
        
        Args:
            telemetry_data: List of raw telemetry points
            
        Returns:
            List of clustered road events
        """
        start_time = time.time()
        logger.info(f"Starting clustering for {len(telemetry_data)} points")
        
        if len(telemetry_data) < self.min_samples:
            logger.warning("Insufficient points for clustering")
            return []
        
        # Extract coordinates for clustering
        coords = [(point.latitude, point.longitude) for point in telemetry_data]
        
        # Calculate distance matrix using Haversine
        distance_matrix = HaversineDistance.distance_matrix(coords)
        
        # Apply DBSCAN with precomputed distance matrix
        dbscan = DBSCAN(
            eps=self.eps_meters,
            min_samples=self.min_samples,
            metric='precomputed'
        )
        
        cluster_labels = dbscan.fit_predict(distance_matrix)
        
        # Convert clusters to road events
        road_events = self._create_road_events(telemetry_data, cluster_labels)
        
        clustering_time = time.time() - start_time
        logger.info(f"Clustering completed in {clustering_time:.2f}s - {len(road_events)} events")
        
        self.last_cluster_time = time.time()
        return road_events
    
    def _create_road_events(self, telemetry_data: List[TelemetryPoint], 
                          cluster_labels: np.ndarray) -> List[RoadEvent]:
        """Convert cluster labels to road events"""
        events = []
        unique_labels = set(cluster_labels)
        
        # Remove noise points (label = -1)
        unique_labels.discard(-1)
        
        for label in unique_labels:
            # Get points in this cluster
            cluster_mask = cluster_labels == label
            cluster_points = [telemetry_data[i] for i in range(len(telemetry_data)) if cluster_mask[i]]
            
            if len(cluster_points) >= self.min_samples:
                event = self._create_road_event(cluster_points, label)
                events.append(event)
        
        return events
    
    def _create_road_event(self, cluster_points: List[TelemetryPoint], cluster_id: int) -> RoadEvent:
        """Create a road event from clustered points"""
        # Calculate center (weighted by Z-magnitude)
        total_z = sum(point.z_magnitude for point in cluster_points)
        weights = [point.z_magnitude / total_z for point in cluster_points]
        
        center_lat = sum(point.latitude * weight for point, weight in zip(cluster_points, weights))
        center_lng = sum(point.longitude * weight for point, weight in zip(cluster_points, weights))
        
        # Calculate cluster radius
        distances = [
            HaversineDistance.haversine(center_lat, center_lng, point.latitude, point.longitude)
            for point in cluster_points
        ]
        radius = max(distances)
        
        # Calculate Z-magnitude statistics
        z_magnitudes = [point.z_magnitude for point in cluster_points]
        avg_z = np.mean(z_magnitudes)
        max_z = np.max(z_magnitudes)
        
        # Calculate confidence based on cluster density and intensity
        confidence = self._calculate_confidence(cluster_points, radius)
        
        # Determine severity
        severity = self._determine_severity(avg_z, max_z, len(cluster_points))
        
        # Time range
        timestamps = [point.timestamp for point in cluster_points]
        start_time = min(timestamps)
        end_time = max(timestamps)
        
        # Device IDs
        device_ids = list(set(point.device_id for point in cluster_points if point.device_id))
        
        # Road health impact
        health_impact = self._calculate_health_impact(avg_z, len(cluster_points), radius)
        
        return RoadEvent(
            event_id=f"event_{int(start_time)}_{cluster_id}",
            center_lat=center_lat,
            center_lng=center_lng,
            radius_meters=radius,
            point_count=len(cluster_points),
            avg_z_magnitude=avg_z,
            max_z_magnitude=max_z,
            confidence_score=confidence,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
            device_ids=device_ids,
            road_health_impact=health_impact
        )
    
    def _calculate_confidence(self, cluster_points: List[TelemetryPoint], radius: float) -> float:
        """Calculate confidence score based on cluster density and intensity"""
        point_density = len(cluster_points) / (math.pi * radius * radius)  # points per m²
        
        # Normalize density (0-1 scale)
        density_score = min(point_density / 0.1, 1.0)  # 0.1 points per m² as reference
        
        # Intensity score based on average Z-magnitude
        avg_z = np.mean([point.z_magnitude for point in cluster_points])
        intensity_score = min(avg_z / 10.0, 1.0)  # 10.0 as reference max
        
        # Combined confidence
        confidence = (density_score * 0.6) + (intensity_score * 0.4)
        return min(confidence, 1.0)
    
    def _determine_severity(self, avg_z: float, max_z: float, point_count: int) -> str:
        """Determine severity based on intensity and cluster size"""
        # Weighted score combining intensity and cluster size
        intensity_score = max_z
        size_score = min(point_count / 10.0, 1.0) * 3.0  # Normalize to 0-3 scale
        
        combined_score = intensity_score + size_score
        
        if combined_score >= 8.0:
            return 'high'
        elif combined_score >= 5.0:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_health_impact(self, avg_z: float, point_count: int, radius: float) -> float:
        """Calculate road health impact score (0-100)"""
        # Base impact from average intensity
        intensity_impact = min(avg_z * 10, 80)  # Scale to 0-80
        
        # Additional impact from cluster density
        density_factor = min(point_count / 5.0, 1.0) * 20  # Up to 20 points
        
        # Spatial impact (larger radius = more widespread issue)
        spatial_impact = min(radius / 10.0, 1.0) * 10  # Up to 10 for 10m+ radius
        
        total_impact = intensity_impact + density_factor + spatial_impact
        return min(total_impact, 100.0)

class RoadHealthCalculator:
    """Calculate road health scores for geographical areas"""
    
    @staticmethod
    def calculate_health_score(events: List[RoadEvent], 
                           bounds: Dict[str, float]) -> float:
        """
        Calculate road health score for a bounding box
        
        Args:
            events: List of road events in the area
            bounds: {'min_lat', 'max_lat', 'min_lng', 'max_lng'}
            
        Returns:
            Health score (0-100, where 100 = perfect road)
        """
        if not events:
            return 100.0
        
        # Filter events within bounds
        bounded_events = [
            event for event in events
            if (bounds['min_lat'] <= event.center_lat <= bounds['max_lat'] and
                bounds['min_lng'] <= event.center_lng <= bounds['max_lng'])
        ]
        
        if not bounded_events:
            return 100.0
        
        # Calculate weighted impact
        total_impact = sum(event.road_health_impact for event in bounded_events)
        area_size = RoadHealthCalculator._calculate_area(bounds)
        
        # Normalize by area (impact per km²)
        impact_density = total_impact / (area_size / 1000000)  # Convert m² to km²
        
        # Health score (inverse of impact)
        health_score = max(0, 100 - impact_density)
        return min(health_score, 100.0)
    
    @staticmethod
    def _calculate_area(bounds: Dict[str, float]) -> float:
        """Calculate area of bounding box in square meters"""
        lat_diff = bounds['max_lat'] - bounds['min_lat']
        lng_diff = bounds['max_lng'] - bounds['min_lng']
        
        # Approximate area using rectangular approximation
        # 1 degree latitude ≈ 111,132 meters
        # 1 degree longitude ≈ 111,320 * cos(latitude) meters
        avg_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        lat_meters = lat_diff * 111132
        lng_meters = lng_diff * 111320 * math.cos(math.radians(avg_lat))
        
        return abs(lat_meters * lng_meters)

class ClusteringService:
    """Main clustering service for background processing"""
    
    def __init__(self, eps_meters: float = 5.0, min_samples: int = 3):
        self.clusterer = DBSCANClusterer(eps_meters, min_samples)
        self.health_calculator = RoadHealthCalculator()
        
    async def process_pending_telemetry(self, telemetry_data: List[TelemetryPoint]) -> List[RoadEvent]:
        """Process pending telemetry data and return road events"""
        try:
            # Cluster the telemetry data
            events = self.clusterer.cluster_telemetry_points(telemetry_data)
            
            # Log processing summary
            logger.info(f"Processed {len(telemetry_data)} points into {len(events)} road events")
            
            return events
            
        except Exception as e:
            logger.error(f"Error in clustering service: {str(e)}")
            return []
    
    def get_health_score(self, events: List[RoadEvent], bounds: Dict[str, float]) -> float:
        """Get road health score for a specific area"""
        return self.health_calculator.calculate_health_score(events, bounds)

# Performance optimization for background worker
class BackgroundClusterWorker:
    """Optimized background worker for clustering operations"""
    
    def __init__(self, clustering_service: ClusteringService):
        self.clustering_service = clustering_service
        self.is_running = False
        self.batch_size = 1000  # Process in batches to avoid memory issues
        
    async def start_worker(self):
        """Start the background clustering worker"""
        self.is_running = True
        logger.info("Background clustering worker started")
        
        while self.is_running:
            try:
                # Process telemetry in batches
                # This would connect to your telemetry database/stream
                await self._process_batch()
                
                # Sleep to prevent CPU overload
                await asyncio.sleep(30)  # 30-second intervals
                
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
        
        logger.info("Background clustering worker stopped")
    
    async def _process_batch(self):
        """Process a batch of telemetry data"""
        # This would fetch from your telemetry source
        # For now, return empty as this is a framework
        pass
    
    def stop_worker(self):
        """Stop the background worker"""
        self.is_running = False

if __name__ == "__main__":
    # Test the clustering service
    test_telemetry = [
        TelemetryPoint(28.6692, 77.4538, 5.2, time.time(), "device_001", 25.0),
        TelemetryPoint(28.6693, 77.4539, 6.1, time.time() + 1, "device_001", 24.5),
        TelemetryPoint(28.6691, 77.4537, 4.8, time.time() + 2, "device_002", 26.0),
        TelemetryPoint(28.7000, 77.4800, 8.5, time.time() + 10, "device_003", 30.0),
        TelemetryPoint(28.7001, 77.4801, 7.9, time.time() + 11, "device_003", 29.5),
        TelemetryPoint(28.6999, 77.4799, 9.2, time.time() + 12, "device_004", 31.0),
    ]
    
    clustering_service = ClusteringService(eps_meters=5.0, min_samples=3)
    events = asyncio.run(clustering_service.process_pending_telemetry(test_telemetry))
    
    print(f"Generated {len(events)} road events:")
    for event in events:
        print(f"Event {event.event_id}: {event.point_count} points, "
              f"severity={event.severity}, confidence={event.confidence_score:.2f}")
