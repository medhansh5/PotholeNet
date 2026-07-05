"""
PotholeNet v3.0 - Model Training Script
Trains RandomForest classifier on synthetic/real road telemetry data.
"""

import pandas as pd
import numpy as np
import os
import sys

# Add project root to sys.path so potholenet can be imported from scripts/
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from potholenet import PotholeNet

def bootstrap_model():
    # 1. Initialize PotholeNet
    detector = PotholeNet(sampling_rate=100)
    
    # 2. Load test data using robust paths
    data_dir = os.path.join(base_dir, 'data')
    try:
        smooth_df = pd.read_csv(os.path.join(data_dir, 'smooth_road.csv'))
        pothole_df = pd.read_csv(os.path.join(data_dir, 'pothole_events.csv'))
    except FileNotFoundError:
        print(f"Error: CSV files not found in {data_dir}. Please add them first!")
        return

    # 3. Create Windows (Segments of data for the AI to 'look' at)
    # We break the data into windows of 100 samples each (1 second at 100Hz)
    window_size = 100
    smooth_windows = [smooth_df[i:i+window_size] for i in range(0, len(smooth_df) - window_size + 1, window_size)]
    pothole_windows = [pothole_df[i:i+window_size] for i in range(0, len(pothole_df) - window_size + 1, window_size)]
    
    X_windows = smooth_windows + pothole_windows
    y_labels = [0]*len(smooth_windows) + [1]*len(pothole_windows)
    
    # 4. Train and Save directly to models directory
    print("Starting PotholeNet v3.0 training session...")
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, 'potholenet_v3.pkl')
    
    detector.train_model(X_windows, y_labels, output_path=model_path)
    print(f"Success: Model saved to {model_path}")

if __name__ == "__main__":
    bootstrap_model()