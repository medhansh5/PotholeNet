"""
PotholeNet Engine Demo

Demonstrates the complete PotholeNet Engine functionality:
1. Signal processing with 4th-order Butterworth filter
2. Real-time classification
3. GPS coordinate integration
4. Map API integration
"""

import time
import numpy as np
import pandas as pd
from api import get_api, process_real_time_data
from engine import create_engine, SensorReading
import matplotlib.pyplot as plt

def demo_signal_processing():
    """Demonstrate signal processing capabilities"""
    print("=== Signal Processing Demo ===")
    
    # Create engine
    engine = create_engine()
    
    # Load real pothole data
    try:
        df = pd.read_csv('data/pothole_events.csv')
        print(f"Loaded {len(df)} pothole samples")
        
        # Extract first 100 samples (1 second)
        window_data = df.iloc[:100].values
        
        # Extract features
        features = engine.signal_processor.extract_features(window_data)
        
        print(f"Extracted {len(features)} features:")
        feature_names = ['Z Variance', 'Z Peak-to-Peak', 'Z RMS', 'Z Max Abs', 
                        'XY RMS', 'High Freq Power', 'Spectral Centroid']
        
        for i, (name, value) in enumerate(zip(feature_names, features)):
            print(f"  {name}: {value:.4f}")
            
        # Show filtering effect
        print("\nFiltering Analysis:")
        z_raw = window_data[:, 3]
        z_filtered = engine.signal_processor.apply_butterworth_highpass(z_raw)
        
        print(f"  Raw Z variance: {np.var(z_raw):.4f}")
        print(f"  Filtered Z variance: {np.var(z_filtered):.4f}")
        print(f"  Variance reduction: {np.var(z_raw)/np.var(z_filtered):.2f}x")
        
    except FileNotFoundError:
        print("No pothole data found in data/pothole_events.csv")

def demo_real_time_classification():
    """Demonstrate real-time classification"""
    print("\n=== Real-time Classification Demo ===")
    
    # Create API with trained model
    api = get_api('models/potholenet_v2.pkl')
    
    # Simulate real-time data stream
    print("Simulating 3 seconds of sensor data...")
    
    detections = []
    start_time = time.time()
    
    for i in range(300):  # 3 seconds at 100Hz
        timestamp = start_time + i * 0.01
        
        # Generate realistic sensor data
        x = np.random.randn() * 0.1
        y = np.random.randn() * 0.1
        
        # Add pothole simulation at 1.5 seconds
        if 150 <= i < 170:
            z = 2.0 * np.exp(-((i - 160) / 10)**2)
        else:
            z = np.random.randn() * 0.1
        
        # Simulate GPS movement
        lat = 40.7128 + i * 0.00001
        lng = -74.0060 + i * 0.00001
        
        # Process data
        api.add_sensor_data(timestamp, x, y, z, lat, lng)
        
        # Check for detections every 50 samples
        if i % 50 == 49:
            batch_detections = api.process_and_get_detections()
            detections.extend(batch_detections)
    
    print(f"Total detections: {len(detections)}")
    
    for detection in detections:
        print(f"  Pothole detected!")
        print(f"    Confidence: {detection['confidence']:.2f}")
        print(f"    Severity: {detection['severity']}")
        print(f"    Location: {detection['latitude']:.6f}, {detection['longitude']:.6f}")
        print(f"    Time: {time.strftime('%H:%M:%S', time.localtime(detection['timestamp']))}")

def demo_api_integration():
    """Demonstrate simple API integration"""
    print("\n=== API Integration Demo ===")
    
    # Simple one-shot processing
    detections = process_real_time_data(
        timestamp=time.time(),
        x=0.1, y=0.2, z=2.5,  # High Z value = potential pothole
        latitude=40.7128,
        longitude=-74.0060
    )
    
    if detections:
        print(f"Detected {len(detections)} potholes:")
        for detection in detections:
            print(f"  {detection['severity']} severity at {detection['confidence']:.2f} confidence")
    else:
        print("No potholes detected (model may need more training data)")

def demo_coordinate_processing():
    """Demonstrate coordinate processing"""
    print("\n=== Coordinate Processing Demo ===")
    
    from api import CoordinateProcessor
    
    # Test coordinate validation
    print("Coordinate Validation:")
    print(f"  Valid (40.7128, -74.0060): {CoordinateProcessor.validate_coordinates(40.7128, -74.0060)}")
    print(f"  Invalid (91.0, 0.0): {CoordinateProcessor.validate_coordinates(91.0, 0.0)}")
    
    # Test distance calculation
    print("\nDistance Calculation:")
    distance = CoordinateProcessor.calculate_distance(
        40.7128, -74.0060,  # Times Square
        40.7580, -73.9855   # Central Park
    )
    print(f"  Times Square to Central Park: {distance:.0f} meters")
    
    # Test detection clustering
    print("\nDetection Clustering:")
    detections = [
        {'latitude': 40.7128, 'longitude': -74.0060, 'confidence': 0.8, 'severity': 'medium', 'timestamp': time.time()},
        {'latitude': 40.7129, 'longitude': -74.0061, 'confidence': 0.9, 'severity': 'high', 'timestamp': time.time()},
        {'latitude': 40.7500, 'longitude': -73.9800, 'confidence': 0.7, 'severity': 'low', 'timestamp': time.time()},
    ]
    
    clustered = CoordinateProcessor.cluster_nearby_detections(detections, radius_meters=100.0)
    print(f"  Original detections: {len(detections)}")
    print(f"  Clustered detections: {len(clustered)}")
    print(f"  Largest cluster size: {max(d.get('cluster_size', 1) for d in clustered)}")

def demo_performance():
    """Demonstrate performance capabilities"""
    print("\n=== Performance Demo ===")
    
    engine = create_engine()
    
    # Test processing speed
    n_samples = 10000
    readings = []
    
    # Generate test data
    for i in range(n_samples):
        reading = SensorReading(
            timestamp=i * 0.01,
            x=np.random.randn() * 0.1,
            y=np.random.randn() * 0.1,
            z=np.random.randn() * 0.1
        )
        readings.append(reading)
    
    # Process in chunks
    start_time = time.time()
    chunk_size = 100
    total_detections = 0
    
    for i in range(0, len(readings), chunk_size):
        chunk = readings[i:i+chunk_size]
        detections = engine.process_sensor_data(chunk)
        total_detections += len(detections)
    
    processing_time = time.time() - start_time
    
    print(f"Processed {n_samples} samples in {processing_time:.3f} seconds")
    print(f"Processing speed: {n_samples/processing_time:.0f} samples/second")
    print(f"Real-time capability: {n_samples/processing_time/100:.1f}x real-time")
    print(f"Total detections: {total_detections}")

def demo_visualization():
    """Demonstrate signal visualization"""
    print("\n=== Signal Visualization Demo ===")
    
    try:
        # Load data
        df = pd.read_csv('data/pothole_events.csv')
        
        # Take first 200 samples (2 seconds)
        data = df.iloc[:200]
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot raw signal
        ax1.plot(data['time'], data['z'], 'b-', label='Raw Z-axis')
        ax1.set_title('Raw Accelerometer Signal (Z-axis)')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Acceleration (m/s²)')
        ax1.grid(True)
        ax1.legend()
        
        # Apply filtering
        engine = create_engine()
        z_filtered = engine.signal_processor.apply_butterworth_highpass(data['z'].values)
        
        # Plot filtered signal
        ax2.plot(data['time'], z_filtered, 'r-', label='Filtered Z-axis')
        ax2.set_title('Filtered Signal (4th-order Butterworth High-Pass)')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Acceleration (m/s²)')
        ax2.grid(True)
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig('signal_processing_demo.png', dpi=150, bbox_inches='tight')
        print("Signal visualization saved as 'signal_processing_demo.png'")
        
    except FileNotFoundError:
        print("No data available for visualization")
    except Exception as e:
        print(f"Visualization error: {e}")

if __name__ == "__main__":
    print("PotholeNet Engine v2.0 - Complete Demo")
    print("=" * 50)
    
    # Run all demos
    demo_signal_processing()
    demo_real_time_classification()
    demo_api_integration()
    demo_coordinate_processing()
    demo_performance()
    demo_visualization()
    
    print("\n" + "=" * 50)
    print("Demo completed! PotholeNet Engine is ready for integration.")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Review app_integration_example.py for mobile app integration")
    print("3. Test with real sensor data from Oppo F23 5G")
    print("4. Deploy to production environment")
