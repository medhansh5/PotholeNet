import pandas as pd
import numpy as np
from potholenet import PotholeNet
import os

def bootstrap_model():
    # 1. Initialize PotholeNet
    detector = PotholeNet(sampling_rate=100)
    
    # 2. Load the synthetic test data
    try:
        smooth_df = pd.read_csv('data/smooth_road.csv')
        pothole_df = pd.read_csv('data/pothole_events.csv')
    except FileNotFoundError:
        print("Error: CSV files not found in /data. Please add them first!")
        return

    # 3. Create Windows (Segments of data for the AI to 'look' at)
    # We break the 1000 samples into 10 windows of 100 samples each
    smooth_windows = np.array_split(smooth_df, 10)
    pothole_windows = np.array_split(pothole_df, 10)
    
    X_windows = smooth_windows + pothole_windows
    y_labels = [0]*10 + [1]*10  # 0 for smooth, 1 for pothole
    
    # 4. Train and Save
    print("Starting training session for 'The Baron'...")
    detector.train_model(X_windows, y_labels)
    
    # Move the generated model to the models folder
    if os.path.exists('potholenet_v1.pkl'):
        os.rename('potholenet_v1.pkl', 'models/potholenet_v1.pkl')
        print("Success: Model saved to models/potholenet_v1.pkl")

if __name__ == "__main__":
    bootstrap_model()