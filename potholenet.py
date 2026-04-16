import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os
import requests
import json
import time

def upload_with_wakeup(lat, lng, quality):
    API_URL = "https://shadowmap-api.onrender.com/upload"
    # Round to 5 decimal places (~1.1 meter precision)
    payload = {
        "lat": round(float(lat), 5),
        "lng": round(float(lng), 5),
        "quality": int(quality_score)
    }
    # Render Free Tier takes ~50s to spin up. 
    # We use a 60s timeout for the "Wake-up" attempt.
    try:
        print("Sending data (Waiting for server to wake up...)")
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 201:
            print("Server is awake! Data uploaded.")
            return True
    except requests.exceptions.ReadTimeout:
        print("Server wake-up timed out. Retrying on next bump...")
    except Exception as e:
        print(f"Connection error: {e}")
    return False

class PotholeNet:
    """
    PotholeNet: Road Quality Classifier
    Optimized for Royal Enfield Classic 350 ("Shadow")
    
    This class handles the ingestion of smartphone accelerometer data,
    filters out mechanical noise from the engine, and classifies
    road surface anomalies.
    """
    
    def __init__(self, sampling_rate=100):
        self.fs = sampling_rate  # Target sampling frequency (Hz)
        self.model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=12, 
            random_state=42
        )

    def _apply_butterworth_highpass(self, data, cutoff=12, order=4):
        """
        Removes low-frequency engine 'thump' vibrations.
        Specifically tuned for the 350cc long-stroke engine signature.
        """
        nyq = 0.5 * self.fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, data)

    def extract_features(self, window):
        """Feature Engineering: RMS, Std Dev, and Peak Magnitude."""
        # Check if the window is a DataFrame; if so, grab the 'z' column.
        # Otherwise, assume it's already a slice of the z-axis data.
        if isinstance(window, pd.DataFrame):
            z_raw = window['z'].values
        else:
            # If it's a numpy array, we assume column 3 (index 2) is Z
            # (time=0, x=1, y=2, z=3)
            z_raw = window[:, 3] if window.ndim > 1 else window
            
        z_filt = self._apply_butterworth_highpass(z_raw)
        
        return [
            np.std(z_filt),
            np.max(np.abs(z_filt)),
            np.sqrt(np.mean(z_filt**2)),
            np.ptp(z_filt)
        ]

    def train_model(self, data_windows, labels):
        """
        Trains the Random Forest model on labeled segments.
        Labels: 0 = Smooth Road, 1 = Pothole/Rough Road
        """
        X = [self.extract_features(win) for win in data_windows]
        y = labels
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        self.model.fit(X_train, y_train)
        
        print("--- Model Training Performance ---")
        predictions = self.model.predict(X_test)
        print(classification_report(y_test, predictions))
        
        # Save the model for real-time edge deployment
        joblib.dump(self.model, 'potholenet_v1.pkl')
        print("Model saved as potholenet_v1.pkl")

    def run_inference(self, live_window):
        """
        Used for real-time prediction during a ride.
        """
        features = np.array(self.extract_features(live_window)).reshape(1, -1)
        prediction = self.model.predict(features)
        return "POTHOLE" if prediction[0] == 1 else "SMOOTH"

if __name__ == "__main__":
    print("PotholeNet Core Engine v1.0")
    print("Waiting for data mission files from 'Shadow'...")
