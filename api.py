"""
PotholeNet API - Clean interface for app.py integration

Provides simplified API for mobile app to:
1. Ingest raw accelerometer data from Oppo F23 5G
2. Process in real-time at 100Hz sampling rate
3. Output pothole detections with GPS coordinates
4. Handle data buffering and classification
"""

import time
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict
import json
from engine import PotholeNetEngine, SensorReading, PotholeDetection, create_engine

class PotholeNetAPI:
    """
    Simplified API for mobile app integration
    
    Usage:
        api = PotholeNetAPI()
        api.add_sensor_data(timestamp, x, y, z, lat, lng)
        detections = api.process_and_get_detections()
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.engine = create_engine(model_path)
        self.sensor_buffer = []
        self.gps_buffer = []
        self.buffer_size = 200  # 2 seconds of data at 100Hz
        self.processing_enabled = True
        
    def add_sensor_data(self, timestamp: float, x: float, y: float, z: float, 
                       latitude: float = None, longitude: float = None):
        """
        Add new sensor reading to buffer
        
        Args:
            timestamp: Unix timestamp
            x, y, z: Accelerometer values in m/s²
            latitude, longitude: GPS coordinates (optional)
        """
        reading = SensorReading(timestamp, x, y, z)
        
        # Add to sensor buffer
        self.sensor_buffer.append(reading)
        
        # Add GPS data if provided
        if latitude is not None and longitude is not None:
            self.gps_buffer.append((timestamp, latitude, longitude))
        
        # Maintain buffer size
        if len(self.sensor_buffer) > self.buffer_size:
            self.sensor_buffer.pop(0)
            
        if len(self.gps_buffer) > self.buffer_size:
            self.gps_buffer.pop(0)
    
    def process_and_get_detections(self) -> List[Dict]:
        """
        Process buffered sensor data and return pothole detections
        Returns list of detection dictionaries with GPS coordinates
        """
        if not self.processing_enabled or len(self.sensor_buffer) < 100:
            return []
        
        # Process data through engine
        detections = self.engine.process_sensor_data(self.sensor_buffer)
        
        # Enhance detections with GPS coordinates
        enhanced_detections = []
        for detection in detections:
            # Find closest GPS reading
            closest_gps = self._find_closest_gps(detection.timestamp)
            
            detection_dict = asdict(detection)
            if closest_gps:
                detection_dict['latitude'] = closest_gps[1]
                detection_dict['longitude'] = closest_gps[2]
            
            enhanced_detections.append(detection_dict)
        
        return enhanced_detections
    
    def _find_closest_gps(self, target_timestamp: float) -> Optional[Tuple[float, float, float]]:
        """Find GPS reading closest to target timestamp"""
        if not self.gps_buffer:
            return None
        
        min_diff = float('inf')
        closest_gps = None
        
        for gps_timestamp, lat, lng in self.gps_buffer:
            diff = abs(gps_timestamp - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_gps = (gps_timestamp, lat, lng)
        
        return closest_gps if min_diff < 1.0 else None  # Within 1 second
    
    def get_buffer_status(self) -> Dict:
        """Get current buffer status for monitoring"""
        return {
            'sensor_buffer_size': len(self.sensor_buffer),
            'gps_buffer_size': len(self.gps_buffer),
            'processing_enabled': self.processing_enabled,
            'engine_ready': self.engine.classifier.is_trained
        }
    
    def clear_buffers(self):
        """Clear all buffers"""
        self.sensor_buffer.clear()
        self.gps_buffer.clear()
    
    def enable_processing(self, enabled: bool = True):
        """Enable or disable processing"""
        self.processing_enabled = enabled

class CoordinateProcessor:
    """Handles coordinate processing and map integration"""
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> bool:
        """Validate GPS coordinates"""
        return -90 <= latitude <= 90 and -180 <= longitude <= 180
    
    @staticmethod
    def round_coordinates(latitude: float, longitude: float, precision: int = 5) -> Tuple[float, float]:
        """
        Round coordinates to specified precision
        5 decimal places = ~1.1 meter precision
        """
        return round(latitude, precision), round(longitude, precision)
    
    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates in meters"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth's radius in meters
        
        lat1_rad, lng1_rad = radians(lat1), radians(lng1)
        lat2_rad, lng2_rad = radians(lat2), radians(lng2)
        
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def cluster_nearby_detections(detections: List[Dict], radius_meters: float = 10.0) -> List[Dict]:
        """
        Cluster nearby detections to avoid duplicates
        Returns representative detection for each cluster
        """
        if not detections:
            return []
        
        clusters = []
        used_indices = set()
        
        for i, detection in enumerate(detections):
            if i in used_indices:
                continue
            
            # Start new cluster
            cluster = [detection]
            used_indices.add(i)
            
            # Find nearby detections
            for j, other_detection in enumerate(detections):
                if j in used_indices:
                    continue
                
                distance = CoordinateProcessor.calculate_distance(
                    detection['latitude'], detection['longitude'],
                    other_detection['latitude'], other_detection['longitude']
                )
                
                if distance <= radius_meters:
                    cluster.append(other_detection)
                    used_indices.add(j)
            
            # Create representative detection
            rep_detection = CoordinateProcessor._create_representative_detection(cluster)
            clusters.append(rep_detection)
        
        return clusters
    
    @staticmethod
    def _create_representative_detection(cluster: List[Dict]) -> Dict:
        """Create representative detection from cluster"""
        if len(cluster) == 1:
            return cluster[0]
        
        # Average coordinates
        avg_lat = np.mean([d['latitude'] for d in cluster])
        avg_lng = np.mean([d['longitude'] for d in cluster])
        
        # Highest confidence
        max_confidence = max([d['confidence'] for d in cluster])
        
        # Highest severity
        severity_order = {'low': 1, 'medium': 2, 'high': 3}
        max_severity = max(cluster, key=lambda d: severity_order[d['severity']])['severity']
        
        # Latest timestamp
        latest_timestamp = max([d['timestamp'] for d in cluster])
        
        return {
            'latitude': avg_lat,
            'longitude': avg_lng,
            'confidence': max_confidence,
            'severity': max_severity,
            'timestamp': latest_timestamp,
            'cluster_size': len(cluster)
        }

# Global API instance for easy access
_api_instance = None

def get_api(model_path: Optional[str] = None) -> PotholeNetAPI:
    """Get or create global API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = PotholeNetAPI(model_path)
    return _api_instance

def process_real_time_data(timestamp: float, x: float, y: float, z: float,
                          latitude: float = None, longitude: float = None) -> List[Dict]:
    """
    Convenience function for real-time processing
    
    Args:
        timestamp: Unix timestamp
        x, y, z: Accelerometer values
        latitude, longitude: GPS coordinates
    
    Returns:
        List of pothole detections with coordinates
    """
    api = get_api()
    api.add_sensor_data(timestamp, x, y, z, latitude, longitude)
    return api.process_and_get_detections()

# Example usage for app.py integration
if __name__ == "__main__":
    # Initialize API
    api = get_api()
    
    # Simulate real-time data
    print("PotholeNet API v2.0 - Ready for integration")
    print("Usage:")
    print("  api = get_api()")
    print("  api.add_sensor_data(timestamp, x, y, z, lat, lng)")
    print("  detections = api.process_and_get_detections()")
