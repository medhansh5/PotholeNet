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
        "quality": int(quality)
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
        """Feature Engineering: 7-feature schema matching PotholeNet Engine v3.0."""
        if isinstance(window, pd.DataFrame):
            z_raw = window['z'].values
            x_raw = window['x'].values if 'x' in window else np.zeros_like(z_raw)
            y_raw = window['y'].values if 'y' in window else np.zeros_like(z_raw)
        else:
            if isinstance(window, np.ndarray) and window.ndim > 1 and window.shape[1] >= 4:
                x_raw = window[:, 1]
                y_raw = window[:, 2]
                z_raw = window[:, 3]
            elif isinstance(window, np.ndarray) and window.ndim > 1 and window.shape[1] == 3:
                x_raw = window[:, 0]
                y_raw = window[:, 1]
                z_raw = window[:, 2]
            else:
                z_raw = window if not isinstance(window, np.ndarray) or window.ndim == 1 else window[:, 0]
                x_raw = np.zeros_like(z_raw)
                y_raw = np.zeros_like(z_raw)
                
        z_filt = self._apply_butterworth_highpass(z_raw, cutoff=12, order=4)
        x_filt = self._apply_butterworth_highpass(x_raw, cutoff=8, order=4) if np.any(x_raw) else x_raw
        y_filt = self._apply_butterworth_highpass(y_raw, cutoff=8, order=4) if np.any(y_raw) else y_raw
        
        z_variance = np.var(z_filt)
        z_ptp = np.ptp(z_filt)
        z_rms = np.sqrt(np.mean(z_filt**2))
        z_max_abs = np.max(np.abs(z_filt))
        
        xy_mag = np.sqrt(x_filt**2 + y_filt**2)
        xy_rms = np.sqrt(np.mean(xy_mag**2))
        
        if len(z_filt) > 0:
            fft = np.fft.fft(z_filt)
            freqs = np.fft.fftfreq(len(z_filt), 1.0/self.fs)
            power_spectrum = np.abs(fft)**2
            high_freq_mask = (freqs >= 20) & (freqs <= 50)
            high_freq_power = np.sum(power_spectrum[high_freq_mask])
            power_sum = np.sum(power_spectrum[:len(freqs)//2])
            spectral_centroid = np.sum(freqs[:len(freqs)//2] * power_spectrum[:len(freqs)//2]) / power_sum if power_sum > 0 else 0.0
        else:
            high_freq_power = 0.0
            spectral_centroid = 0.0
            
        return [z_variance, z_ptp, z_rms, z_max_abs, xy_rms, high_freq_power, spectral_centroid]

    def train_model(self, data_windows, labels, output_path='potholenet_v3.pkl'):
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
        joblib.dump(self.model, output_path)
        print(f"Model saved as {output_path}")

    def run_inference(self, live_window):
        """
        Used for real-time prediction during a ride.
        """
        features = np.array(self.extract_features(live_window)).reshape(1, -1)
        prediction = self.model.predict(features)
        return "POTHOLE" if prediction[0] == 1 else "SMOOTH"

if __name__ == "__main__":
    print("PotholeNet Core Engine v3.0")
    print("Waiting for data mission files from 'Shadow'...")
