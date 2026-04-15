import pandas as pd
import numpy as np
import os

def validate_ride_data(file_path, target_fs=100):
    """
    Validates telemetry data from Shadow (RE Classic 350).
    Checks for: Column integrity, Sampling Rate, and Data Gaps.
    """
    print(f"--- Validating: {os.path.basename(file_path)} ---")
    
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ ERROR: Could not read file. {e}")
        return False

    # 1. Check Required Columns
    required_cols = ['time', 'x', 'y', 'z']
    if not all(col in df.columns for col in required_cols):
        print(f"❌ ERROR: Missing columns. Expected {required_cols}")
        return False
    print("✅ Column Integrity: Pass")

    # 2. Check Sampling Frequency (Hz)
    # We calculate the average time difference between samples
    time_diffs = np.diff(df['time'].values)
    avg_diff = np.mean(time_diffs)
    actual_fs = 1 / avg_diff
    
    if not (target_fs * 0.9 <= actual_fs <= target_fs * 1.1):
        print(f"⚠️ WARNING: Sampling rate is {actual_fs:.2f}Hz. Target is {target_fs}Hz.")
        print("   Inconsistent sampling may distort the Butterworth filter.")
    else:
        print(f"✅ Sampling Rate: {actual_fs:.2f}Hz (Pass)")

    # 3. Check for Null Values or Gaps
    if df.isnull().values.any():
        print("❌ ERROR: File contains Null/NaN values.")
        return False
    print("✅ Data Completeness: Pass")

    # 4. Check Signal Range (Detecting if phone was loose)
    z_range = np.ptp(df['z'])
    if z_range > 50: # Arbitrary threshold for 'extreme' noise
        print("⚠️ WARNING: Extreme Z-axis variance detected. Was the phone mount loose?")
    
    print("--- Validation Successful ---\n")
    return True

if __name__ == "__main__":
    # Test against your dummy files
    data_dir = 'data/'
    for file in os.listdir(data_dir):
        if file.endswith('.csv'):
            validate_ride_data(os.path.join(data_dir, file))