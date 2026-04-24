"""
PotholeNet App Integration Example

This file demonstrates how to integrate PotholeNet Engine with a mobile application (app.py)
for real-time pothole detection using accelerometer data from Oppo F23 5G.

Key Features:
- Real-time sensor data processing at 100Hz
- GPS coordinate integration
- Pothole detection with confidence scores
- Map integration ready output
"""

import time
import numpy as np
from typing import List, Dict, Optional
import json

# Import PotholeNet API
from api import get_api, process_real_time_data
from engine import SensorReading

class PotholeDetectorApp:
    """
    Main application class for pothole detection
    
    Integration steps:
    1. Initialize detector with trained model
    2. Feed real-time sensor data from phone
    3. Get pothole detections with GPS coordinates
    4. Upload detections to map API
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize the pothole detector"""
        self.api = get_api(model_path)
        self.detection_callback = None
        self.is_running = False
        
    def set_detection_callback(self, callback):
        """Set callback function for pothole detections"""
        self.detection_callback = callback
        
    def start_detection(self):
        """Start real-time detection"""
        self.is_running = True
        self.api.clear_buffers()
        print("PotholeNet detection started")
        
    def stop_detection(self):
        """Stop real-time detection"""
        self.is_running = False
        print("PotholeNet detection stopped")
        
    def process_sensor_reading(self, timestamp: float, x: float, y: float, z: float,
                             latitude: float = None, longitude: float = None):
        """
        Process individual sensor reading
        This method should be called for each accelerometer reading from the phone
        """
        if not self.is_running:
            return
            
        # Add data to API buffer
        self.api.add_sensor_data(timestamp, x, y, z, latitude, longitude)
        
        # Process and get detections periodically
        buffer_status = self.api.get_buffer_status()
        if buffer_status['sensor_buffer_size'] >= 100 and buffer_status['sensor_buffer_size'] % 50 == 0:
            detections = self.api.process_and_get_detections()
            
            # Handle detections
            for detection in detections:
                self._handle_detection(detection)
    
    def _handle_detection(self, detection: Dict):
        """Handle pothole detection"""
        print(f"Pothole detected! Confidence: {detection['confidence']:.2f}, Severity: {detection['severity']}")
        print(f"Location: {detection['latitude']:.6f}, {detection['longitude']:.6f}")
        
        # Call callback if set
        if self.detection_callback:
            self.detection_callback(detection)
        
        # Upload to map API
        self._upload_to_map(detection)
    
    def _upload_to_map(self, detection: Dict):
        """Upload detection to map API"""
        try:
            # Import here to avoid circular imports
            import requests
            
            API_URL = "https://shadowmap-api.onrender.com/upload"
            
            payload = {
                "lat": round(detection['latitude'], 5),
                "lng": round(detection['longitude'], 5),
                "quality": int(detection['confidence'] * 100),
                "severity": detection['severity'],
                "timestamp": detection['timestamp']
            }
            
            # Non-blocking upload
            response = requests.post(API_URL, json=payload, timeout=10)
            if response.status_code == 201:
                print("Detection uploaded to map")
            else:
                print(f"Upload failed: {response.status_code}")
                
        except Exception as e:
            print(f"Upload error: {e}")

class SensorSimulator:
    """Simulate sensor data for testing"""
    
    def __init__(self, detector: PotholeDetectorApp):
        self.detector = detector
        self.is_simulating = False
        
    def start_simulation(self, duration_seconds: int = 60):
        """Start sensor simulation"""
        self.is_simulating = True
        start_time = time.time()
        
        print(f"Starting {duration_seconds} second simulation...")
        
        while self.is_simulating and (time.time() - start_time) < duration_seconds:
            current_time = time.time()
            
            # Simulate sensor data
            x, y, z = self._generate_sensor_data(current_time - start_time)
            
            # Simulate GPS (moving along a path)
            lat, lng = self._generate_gps_data(current_time - start_time)
            
            # Process reading
            self.detector.process_sensor_reading(current_time, x, y, z, lat, lng)
            
            # 100Hz sampling rate
            time.sleep(0.01)
        
        self.is_simulating = False
        print("Simulation completed")
    
    def stop_simulation(self):
        """Stop sensor simulation"""
        self.is_simulating = False
    
    def _generate_sensor_data(self, t: float) -> tuple:
        """Generate realistic sensor data"""
        # Base noise
        x = np.random.randn() * 0.1
        y = np.random.randn() * 0.1
        z = np.random.randn() * 0.1
        
        # Simulate potholes at specific times
        if 10 <= t < 12:  # First pothole
            z += 2.0 * np.exp(-((t - 11) / 0.5)**2)
        elif 25 <= t < 27:  # Second pothole
            z += 1.5 * np.exp(-((t - 26) / 0.4)**2)
        elif 40 <= t < 41:  # Third pothole (smaller)
            z += 1.0 * np.exp(-((t - 40.5) / 0.3)**2)
        
        # Add bike vibration
        z += 0.05 * np.sin(2 * np.pi * 15 * t)  # 15Hz engine vibration
        
        return x, y, z
    
    def _generate_gps_data(self, t: float) -> tuple:
        """Generate GPS data along a path"""
        # Simple straight line path
        base_lat = 40.7128
        base_lng = -74.0060
        
        # Move at ~10 m/s (36 km/h)
        lat = base_lat + (t * 0.00009)  # ~1 meter per 0.00009 degrees
        lng = base_lng + (t * 0.00012)  # ~1 meter per 0.00012 degrees
        
        return lat, lng

# Example usage functions
def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Initialize detector
    detector = PotholeDetectorApp()
    
    # Start detection
    detector.start_detection()
    
    # Process some sample data
    for i in range(150):
        timestamp = time.time() + i * 0.01
        
        # Simulate pothole in the middle
        if 50 <= i < 70:
            z = 2.0 * np.exp(-((i - 60) / 10)**2)
        else:
            z = np.random.randn() * 0.1
        
        detector.process_sensor_reading(
            timestamp,
            np.random.randn() * 0.1,  # x
            np.random.randn() * 0.1,  # y
            z,                        # z
            40.7128,                 # lat
            -74.0060                 # lng
        )
    
    # Stop detection
    detector.stop_detection()

def example_with_callback():
    """Example with detection callback"""
    print("\n=== Callback Example ===")
    
    def my_detection_callback(detection):
        """Custom callback for handling detections"""
        print(f"🚨 POTHOLE DETECTED!")
        print(f"   Confidence: {detection['confidence']*100:.1f}%")
        print(f"   Severity: {detection['severity'].upper()}")
        print(f"   Location: {detection['latitude']:.6f}, {detection['longitude']:.6f}")
        print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(detection['timestamp']))}")
        print("-" * 40)
    
    detector = PotholeDetectorApp()
    detector.set_detection_callback(my_detection_callback)
    
    # Run simulation
    simulator = SensorSimulator(detector)
    simulator.start_simulation(duration_seconds=30)

def example_real_time_processing():
    """Example of real-time processing function"""
    print("\n=== Real-time Processing Example ===")
    
    # This is how you would use the convenience function
    detections = process_real_time_data(
        timestamp=time.time(),
        x=0.1, y=0.2, z=2.5,  # High Z value = potential pothole
        latitude=40.7128,
        longitude=-74.0060
    )
    
    if detections:
        print(f"Detected {len(detections)} potholes")
        for detection in detections:
            print(f"  - {detection['severity']} severity at {detection['confidence']:.2f} confidence")
    else:
        print("No potholes detected")

def example_batch_processing():
    """Example of batch processing existing data"""
    print("\n=== Batch Processing Example ===")
    
    # Load existing sensor data
    try:
        import pandas as pd
        df = pd.read_csv('data/pothole_events.csv')
        
        detector = PotholeDetectorApp()
        detector.start_detection()
        
        # Process all data
        for _, row in df.iterrows():
            detector.process_sensor_reading(
                timestamp=row['time'],
                x=row['x'],
                y=row['y'],
                z=row['z'],
                latitude=40.7128,  # Would need actual GPS data
                longitude=-74.0060
            )
        
        detector.stop_detection()
        
    except FileNotFoundError:
        print("No sample data found in data/pothole_events.csv")

if __name__ == "__main__":
    print("PotholeNet App Integration Examples")
    print("=" * 50)
    
    # Run examples
    example_basic_usage()
    example_with_callback()
    example_real_time_processing()
    example_batch_processing()
    
    print("\nIntegration Summary:")
    print("1. Initialize PotholeDetectorApp")
    print("2. Call process_sensor_reading() for each accelerometer reading")
    print("3. Handle detections via callback or direct processing")
    print("4. Detections automatically include GPS coordinates")
    print("5. Upload to map API handled automatically")
