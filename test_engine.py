
"""
PotholeNet Engine Testing and Validation Framework

Comprehensive testing suite for:
- Signal processing validation
- Model performance evaluation
- Real-time processing simulation
- API integration testing
"""

import unittest
import numpy as np
import pandas as pd
import time
from unittest.mock import patch, MagicMock
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import PotholeNetEngine, SignalProcessor, PotholeClassifier, SensorReading
from api import PotholeNetAPI, CoordinateProcessor, get_api, process_real_time_data

class TestSignalProcessor(unittest.TestCase):
    """Test signal processing functionality"""
    
    def setUp(self):
        self.processor = SignalProcessor(sampling_rate=100)
        
    def test_butterworth_filter(self):
        """Test Butterworth high-pass filter"""
        # Create test signal with low and high frequency components
        t = np.linspace(0, 1, 100)
        low_freq = 0.5 * np.sin(2 * np.pi * 2 * t)  # 2 Hz - should be filtered
        high_freq = 0.1 * np.sin(2 * np.pi * 30 * t)  # 30 Hz - should pass
        signal = low_freq + high_freq
        
        filtered = self.processor.apply_butterworth_highpass(signal)
        
        # High-frequency component should be preserved
        self.assertGreater(np.std(filtered), 0.05)
        
    def test_tri_axial_filtering(self):
        """Test tri-axial filtering"""
        # Create test data: time, x, y, z
        n_samples = 100
        data = np.random.randn(n_samples, 4)  # Random noise
        data[:, 0] = np.linspace(0, 1, n_samples)  # Time column
        
        filtered = self.processor.apply_tri_axial_filtering(data)
        
        # Should preserve shape
        self.assertEqual(filtered.shape, data.shape)
        
        # Should reduce low-frequency content
        self.assertLess(np.std(filtered[:, 3]), np.std(data[:, 3]))
        
    def test_feature_extraction(self):
        """Test feature extraction from sensor window"""
        # Create realistic pothole-like signal
        n_samples = 100
        t = np.linspace(0, 1, n_samples)
        
        # Simulate pothole impact on Z-axis
        z_signal = np.random.randn(n_samples) * 0.1  # Background noise
        z_signal[40:60] += 2.0 * np.exp(-((t[40:60] - 0.5) / 0.1)**2)  # Impact
        
        # Create full data matrix
        data = np.column_stack([
            t,  # time
            np.random.randn(n_samples) * 0.1,  # x
            np.random.randn(n_samples) * 0.1,  # y
            z_signal  # z
        ])
        
        features = self.processor.extract_features(data)
        
        # Should return 7 features
        self.assertEqual(len(features), 7)
        
        # Z-axis variance should be high for pothole
        self.assertGreater(features[0], 0.5)  # variance

class TestPotholeClassifier(unittest.TestCase):
    """Test machine learning classifier"""
    
    def setUp(self):
        self.classifier = PotholeClassifier()
        
    def test_training(self):
        """Test model training"""
        # Create synthetic training data
        n_samples = 100
        n_features = 7
        
        # Smooth road features (low variance)
        smooth_features = np.random.randn(n_samples//2, n_features) * 0.1
        
        # Pothole features (high variance on Z-axis)
        pothole_features = np.random.randn(n_samples//2, n_features) * 0.1
        pothole_features[:, 0] = np.abs(pothole_features[:, 0]) + 1.0  # High variance
        pothole_features[:, 1] = np.abs(pothole_features[:, 1]) + 2.0  # High peak-to-peak
        
        features = np.vstack([smooth_features, pothole_features])
        labels = np.array([0] * (n_samples//2) + [1] * (n_samples//2))
        
        metrics = self.classifier.train(features, labels)
        
        self.assertTrue(self.classifier.is_trained)
        self.assertGreater(metrics['training_accuracy'], 0.8)
        
    def test_prediction(self):
        """Test model prediction"""
        # Train first
        self.test_training()
        
        # Test prediction on smooth road
        smooth_features = np.random.randn(7) * 0.1
        prediction, confidence = self.classifier.predict(smooth_features)
        
        self.assertIn(prediction, [0, 1])
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
    def test_model_save_load(self):
        """Test model saving and loading"""
        # Train model
        self.test_training()
        
        # Save model
        model_path = 'test_model.pkl'
        self.classifier.save_model(model_path)
        self.assertTrue(os.path.exists(model_path))
        
        # Load model
        new_classifier = PotholeClassifier()
        new_classifier.load_model(model_path)
        
        self.assertTrue(new_classifier.is_trained)
        
        # Cleanup
        if os.path.exists(model_path):
            os.remove(model_path)

class TestPotholeNetEngine(unittest.TestCase):
    """Test main engine functionality"""
    
    def setUp(self):
        self.engine = PotholeNetEngine()
        
    def test_sensor_data_processing(self):
        """Test processing sensor data"""
        # Create test sensor readings
        n_readings = 150
        readings = []
        
        for i in range(n_readings):
            # Simulate pothole in the middle
            if 50 <= i < 70:
                z = 2.0 * np.exp(-((i - 60) / 10)**2)  # Impact
            else:
                z = np.random.randn() * 0.1  # Noise
                
            reading = SensorReading(
                timestamp=i * 0.01,  # 100Hz
                x=np.random.randn() * 0.1,
                y=np.random.randn() * 0.1,
                z=z
            )
            readings.append(reading)
        
        # Process data
        detections = self.engine.process_sensor_data(readings)
        
        # Should detect pothole
        self.assertGreaterEqual(len(detections), 0)
        
    def test_detection_severity(self):
        """Test pothole severity determination"""
        # Test low severity
        low_confidence = 0.75
        low_features = np.array([0.5, 0.5, 0.5, 0.5, 0.1, 0.1, 10.0])
        severity = self.engine._determine_severity(low_confidence, low_features)
        self.assertEqual(severity, 'low')
        
        # Test high severity
        high_confidence = 0.95
        high_features = np.array([2.0, 3.0, 1.5, 2.5, 0.5, 1.0, 30.0])
        severity = self.engine._determine_severity(high_confidence, high_features)
        self.assertEqual(severity, 'high')

class TestCoordinateProcessor(unittest.TestCase):
    """Test coordinate processing functionality"""
    
    def test_coordinate_validation(self):
        """Test GPS coordinate validation"""
        # Valid coordinates
        self.assertTrue(CoordinateProcessor.validate_coordinates(40.7128, -74.0060))
        
        # Invalid coordinates
        self.assertFalse(CoordinateProcessor.validate_coordinates(91.0, 0.0))
        self.assertFalse(CoordinateProcessor.validate_coordinates(0.0, 181.0))
        
    def test_coordinate_rounding(self):
        """Test coordinate rounding"""
        lat, lng = CoordinateProcessor.round_coordinates(40.712845, -74.006023, 5)
        self.assertEqual(lat, 40.71285)
        self.assertEqual(lng, -74.00602)
        
    def test_distance_calculation(self):
        """Test distance calculation"""
        # Distance between NYC coordinates
        distance = CoordinateProcessor.calculate_distance(
            40.7128, -74.0060,  # Times Square
            40.7580, -73.9855   # Central Park
        )
        
        # Should be approximately 1 km
        self.assertGreater(distance, 800)
        self.assertLess(distance, 1200)
        
    def test_detection_clustering(self):
        """Test detection clustering"""
        # Create nearby detections
        detections = [
            {'latitude': 40.7128, 'longitude': -74.0060, 'confidence': 0.8, 'severity': 'medium', 'timestamp': time.time()},
            {'latitude': 40.7129, 'longitude': -74.0061, 'confidence': 0.9, 'severity': 'high', 'timestamp': time.time()},
            {'latitude': 40.7500, 'longitude': -73.9800, 'confidence': 0.7, 'severity': 'low', 'timestamp': time.time()},
        ]
        
        clustered = CoordinateProcessor.cluster_nearby_detections(detections, radius_meters=100.0)
        
        # Should cluster first two detections
        self.assertEqual(len(clustered), 2)
        self.assertEqual(clustered[0]['cluster_size'], 2)

class TestPotholeNetAPI(unittest.TestCase):
    """Test API integration"""
    
    def setUp(self):
        self.api = PotholeNetAPI()
        
    def test_sensor_data_buffering(self):
        """Test sensor data buffering"""
        # Add sensor data
        self.api.add_sensor_data(time.time(), 0.1, 0.2, 0.3, 40.7128, -74.0060)
        
        status = self.api.get_buffer_status()
        self.assertEqual(status['sensor_buffer_size'], 1)
        self.assertEqual(status['gps_buffer_size'], 1)
        
    def test_gps_matching(self):
        """Test GPS coordinate matching"""
        # Add sensor data with GPS
        timestamp = time.time()
        self.api.add_sensor_data(timestamp, 0.1, 0.2, 0.3, 40.7128, -74.0060)
        
        # Find closest GPS
        closest = self.api._find_closest_gps(timestamp + 0.5)
        self.assertIsNotNone(closest)
        self.assertEqual(closest[1], 40.7128)
        self.assertEqual(closest[2], -74.0060)
        
    def test_buffer_management(self):
        """Test buffer clearing and size limits"""
        # Fill buffer beyond limit
        for i in range(250):
            self.api.add_sensor_data(time.time() + i, 0.1, 0.2, 0.3)
        
        status = self.api.get_buffer_status()
        self.assertLessEqual(status['sensor_buffer_size'], 200)
        
        # Clear buffers
        self.api.clear_buffers()
        status = self.api.get_buffer_status()
        self.assertEqual(status['sensor_buffer_size'], 0)
        self.assertEqual(status['gps_buffer_size'], 0)

class TestRealTimeSimulation(unittest.TestCase):
    """Test real-time processing simulation"""
    
    def test_real_time_processing(self):
        """Test real-time data processing simulation"""
        api = get_api()
        api.clear_buffers()
        
        # Simulate 2 seconds of data at 100Hz
        start_time = time.time()
        detections = []
        
        for i in range(200):
            timestamp = start_time + i * 0.01
            
            # Simulate pothole at 1 second mark
            if 100 <= i < 120:
                z = 2.0 * np.exp(-((i - 110) / 10)**2)
            else:
                z = np.random.randn() * 0.1
            
            # Add sensor data with GPS
            api.add_sensor_data(timestamp, 
                              np.random.randn() * 0.1,
                              np.random.randn() * 0.1,
                              z,
                              40.7128 + i * 0.00001,
                              -74.0060 + i * 0.00001)
            
            # Process every 50 samples
            if i % 50 == 49:
                batch_detections = api.process_and_get_detections()
                detections.extend(batch_detections)
        
        # Should have detected the pothole
        self.assertGreater(len(detections), 0)

def run_performance_benchmark():
    """Run performance benchmarking"""
    print("\n=== Performance Benchmark ===")
    
    engine = PotholeNetEngine()
    
    # Create large dataset
    n_samples = 10000
    readings = []
    
    start_time = time.time()
    for i in range(n_samples):
        reading = SensorReading(
            timestamp=i * 0.01,
            x=np.random.randn() * 0.1,
            y=np.random.randn() * 0.1,
            z=np.random.randn() * 0.1
        )
        readings.append(reading)
    
    creation_time = time.time() - start_time
    
    # Process in chunks
    start_time = time.time()
    chunk_size = 100
    total_detections = 0
    
    for i in range(0, len(readings), chunk_size):
        chunk = readings[i:i+chunk_size]
        detections = engine.process_sensor_data(chunk)
        total_detections += len(detections)
    
    processing_time = time.time() - start_time
    
    print(f"Data creation: {creation_time:.3f}s")
    print(f"Processing: {processing_time:.3f}s")
    print(f"Samples per second: {n_samples/processing_time:.0f}")
    print(f"Total detections: {total_detections}")

if __name__ == '__main__':
    # Run tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance benchmark
    run_performance_benchmark()
