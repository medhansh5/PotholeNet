"""
PotholeNet Engine - Real-time Signal Processing and Classification Module

Role: Processes tri-axial accelerometer telemetry from Oppo F23 5G at 100Hz
Core Logic: 4th-order Butterworth High-Pass Filter eliminates drift and engine vibrations
Model: ML classifier trained on Z-axis variance and peak-to-peak amplitude
Integration: Clean Python API for app.py to ingest sensor data and output coordinates
"""

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
import time
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    """Tri-axial accelerometer reading with timestamp"""
    timestamp: float
    x: float
    y: float
    z: float
    
@dataclass
class PotholeDetection:
    """Pothole detection result with coordinates"""
    latitude: float
    longitude: float
    confidence: float
    severity: str  # 'low', 'medium', 'high'
    timestamp: float

class SignalProcessor:
    """Advanced signal processing for tri-axial accelerometer data"""
    
    def __init__(self, sampling_rate: int = 100):
        self.fs = sampling_rate
        self.scaler = StandardScaler()
        
    def apply_butterworth_highpass(self, data: np.ndarray, cutoff: float = 12.0, order: int = 4) -> np.ndarray:
        """
        Apply 4th-order Butterworth High-Pass Filter
        Eliminates low-frequency drift (bike lean/acceleration) and engine vibrations
        Isolates high-frequency vertical impacts from potholes
        """
        nyq = 0.5 * self.fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, data)
    
    def apply_tri_axial_filtering(self, data: np.ndarray) -> np.ndarray:
        """
        Apply filtering to all three axes
        Focuses on Z-axis for vertical impacts while using X,Y for noise rejection
        """
        filtered_data = np.zeros_like(data)
        
        # Primary filtering on Z-axis (vertical impacts)
        if data.shape[1] >= 4:  # time, x, y, z format
            filtered_data[:, 1] = self.apply_butterworth_highpass(data[:, 1], cutoff=8.0)  # X-axis
            filtered_data[:, 2] = self.apply_butterworth_highpass(data[:, 2], cutoff=8.0)  # Y-axis  
            filtered_data[:, 3] = self.apply_butterworth_highpass(data[:, 3], cutoff=12.0) # Z-axis (primary)
        else:  # x, y, z format
            filtered_data[:, 0] = self.apply_butterworth_highpass(data[:, 0], cutoff=8.0)  # X-axis
            filtered_data[:, 1] = self.apply_butterworth_highpass(data[:, 1], cutoff=8.0)  # Y-axis
            filtered_data[:, 2] = self.apply_butterworth_highpass(data[:, 2], cutoff=12.0) # Z-axis (primary)
            
        return filtered_data
    
    def extract_features(self, window: np.ndarray) -> np.ndarray:
        """
        Extract features from filtered sensor window
        Features: Z-axis variance, peak-to-peak amplitude, RMS energy, spectral characteristics
        """
        # Determine data format and extract Z-axis
        if window.shape[1] >= 4:  # time, x, y, z format
            z_data = window[:, 3]
            x_data = window[:, 1] 
            y_data = window[:, 2]
        else:  # x, y, z format
            z_data = window[:, 2]
            x_data = window[:, 0]
            y_data = window[:, 1]
        
        # Apply filtering
        if window.shape[1] >= 4:
            filtered = self.apply_tri_axial_filtering(window)
            z_filtered = filtered[:, 3]
            x_filtered = filtered[:, 1]
            y_filtered = filtered[:, 2]
        else:
            filtered_window = np.column_stack([x_data, y_data, z_data])
            filtered = self.apply_tri_axial_filtering(filtered_window)
            z_filtered = filtered[:, 2]
            x_filtered = filtered[:, 0]
            y_filtered = filtered[:, 1]
        
        # Primary features from Z-axis (vertical impacts)
        z_variance = np.var(z_filtered)
        z_peak_to_peak = np.ptp(z_filtered)
        z_rms = np.sqrt(np.mean(z_filtered**2))
        z_max_abs = np.max(np.abs(z_filtered))
        
        # Secondary features from X,Y axes (noise rejection)
        xy_magnitude = np.sqrt(x_filtered**2 + y_filtered**2)
        xy_rms = np.sqrt(np.mean(xy_magnitude**2))
        
        # Spectral features
        if len(z_filtered) > 0:
            fft = np.fft.fft(z_filtered)
            freqs = np.fft.fftfreq(len(z_filtered), 1.0/self.fs)
            power_spectrum = np.abs(fft)**2
            
            # Power in high-frequency band (20-50 Hz - typical pothole impacts)
            high_freq_mask = (freqs >= 20) & (freqs <= 50)
            high_freq_power = np.sum(power_spectrum[high_freq_mask])
            
            # Spectral centroid
            spectral_centroid = np.sum(freqs[:len(freqs)//2] * power_spectrum[:len(freqs)//2]) / np.sum(power_spectrum[:len(freqs)//2])
        else:
            high_freq_power = 0
            spectral_centroid = 0
        
        return np.array([
            z_variance,
            z_peak_to_peak, 
            z_rms,
            z_max_abs,
            xy_rms,
            high_freq_power,
            spectral_centroid
        ])

class PotholeClassifier:
    """Machine learning classifier for road anomaly detection"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=12,
            random_state=42,
            class_weight='balanced'
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def train(self, features: List[np.ndarray], labels: List[int]) -> Dict[str, float]:
        """Train the classifier on extracted features"""
        X = np.array(features)
        y = np.array(labels)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate training metrics
        train_score = self.model.score(X_scaled, y)
        
        return {
            'training_accuracy': train_score,
            'n_samples': len(X),
            'n_features': X.shape[1]
        }
    
    def predict(self, features: np.ndarray) -> Tuple[int, float]:
        """
        Predict road anomaly class and confidence
        Returns: (class_id, confidence_score)
        Class IDs: 0 = Smooth Road, 1 = Pothole/Rough Road
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        prediction = self.model.predict(features_scaled)[0]
        confidence = np.max(self.model.predict_proba(features_scaled))
        
        return prediction, confidence
    
    def save_model(self, path: str):
        """Save trained model and scaler"""
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained
        }
        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model and scaler"""
        model_data = joblib.load(path)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']
        logger.info(f"Model loaded from {path}")

class PotholeNetEngine:
    """
    PotholeNet Engine - Main API for real-time signal processing and classification
    
    Provides clean interface for app.py to:
    1. Ingest raw tri-axial accelerometer data (100Hz)
    2. Process with 4th-order Butterworth High-Pass Filter
    3. Classify road anomalies using ML model
    4. Output localized coordinates for mapping
    """
    
    def __init__(self, model_path: Optional[str] = None, sampling_rate: int = 100):
        self.signal_processor = SignalProcessor(sampling_rate)
        self.classifier = PotholeClassifier(model_path)
        self.window_size = 100  # 1 second of data at 100Hz
        self.detection_buffer = []
        self.last_detection_time = 0
        self.detection_cooldown = 2.0  # seconds between detections
        
    def process_sensor_data(self, readings: List[SensorReading]) -> List[PotholeDetection]:
        """
        Process raw sensor data and return pothole detections
        Main API method for app.py integration
        """
        if len(readings) < self.window_size:
            logger.warning(f"Insufficient data: {len(readings)} readings, need {self.window_size}")
            return []
        
        # Convert to numpy array
        data_array = np.array([[r.timestamp, r.x, r.y, r.z] for r in readings])
        
        # Extract features
        features = self.signal_processor.extract_features(data_array)
        
        # Classify
        try:
            prediction, confidence = self.classifier.predict(features)
        except ValueError as e:
            logger.error(f"Classification failed: {e}")
            return []
        
        detections = []
        current_time = time.time()
        
        # Check for pothole detection
        if prediction == 1 and confidence > 0.7:  # Pothole detected
            if current_time - self.last_detection_time > self.detection_cooldown:
                # Get location from last reading (app should provide GPS)
                last_reading = readings[-1]
                
                # Determine severity based on confidence and feature magnitude
                severity = self._determine_severity(confidence, features)
                
                detection = PotholeDetection(
                    latitude=0.0,  # To be filled by app with GPS data
                    longitude=0.0,  # To be filled by app with GPS data
                    confidence=confidence,
                    severity=severity,
                    timestamp=current_time
                )
                
                detections.append(detection)
                self.last_detection_time = current_time
                
                logger.info(f"Pothole detected: confidence={confidence:.2f}, severity={severity}")
        
        return detections
    
    def _determine_severity(self, confidence: float, features: np.ndarray) -> str:
        """Determine pothole severity based on confidence and feature values"""
        z_variance = features[0]
        z_peak_to_peak = features[1]
        
        if confidence > 0.9 or z_peak_to_peak > 2.0:
            return 'high'
        elif confidence > 0.8 or z_peak_to_peak > 1.0:
            return 'medium'
        else:
            return 'low'
    
    def train_model(self, data_file: str, labels_file: Optional[str] = None):
        """Train model from data files"""
        logger.info(f"Training model from {data_file}")
        
        # Load training data
        df = pd.read_csv(data_file)
        
        # Create sliding windows
        windows = []
        labels = []
        
        window_step = 50  # Overlapping windows
        
        for i in range(0, len(df) - self.window_size, window_step):
            window = df.iloc[i:i+self.window_size].values
            windows.append(window)
            
            # Determine label from filename or separate labels file
            if 'pothole' in data_file.lower():
                labels.append(1)
            else:
                labels.append(0)
        
        # Extract features
        features = [self.signal_processor.extract_features(window) for window in windows]
        
        # Train classifier
        metrics = self.classifier.train(features, labels)
        
        # Save model
        model_path = 'models/potholenet_v2.pkl'
        os.makedirs('models', exist_ok=True)
        self.classifier.save_model(model_path)
        
        logger.info(f"Training completed: {metrics}")
        return metrics
    
    def get_detection_summary(self) -> Dict[str, Union[int, float, List]]:
        """Get summary of recent detections"""
        return {
            'total_detections': len(self.detection_buffer),
            'last_detection': self.last_detection_time,
            'detection_rate': len(self.detection_buffer) / max(1, time.time() - (self.detection_buffer[0] if self.detection_buffer else time.time())),
            'recent_detections': self.detection_buffer[-10:] if self.detection_buffer else []
        }

# Convenience function for app.py integration
def create_engine(model_path: Optional[str] = None) -> PotholeNetEngine:
    """Create and return PotholeNetEngine instance"""
    return PotholeNetEngine(model_path)

if __name__ == "__main__":
    # Example usage
    engine = create_engine()
    
    # Train model if available data
    if os.path.exists('data/pothole_events.csv'):
        engine.train_model('data/pothole_events.csv')
    
    print("PotholeNet Engine v2.0 - Ready for real-time processing")
