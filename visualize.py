import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from potholenet import PotholeNet

def run_visualization(file_path):
    print(f"📈 Analyzing telemetry from: {file_path}")
    
    # 1. Load Data
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return

    # 2. Initialize PotholeNet for DSP
    detector = PotholeNet(sampling_rate=100)
    
    # 3. Apply the Shadow-Specific Filter (Butterworth)
    z_raw = df['z'].values
    # Note: We use the internal filter logic from your PotholeNet class
    z_filt = detector._apply_butterworth_highpass(z_raw)

    # 4. Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    
    # Raw Signal (with Shadow's engine vibration)
    ax1.plot(df['time'], z_raw, color='gray', alpha=0.5, label='Raw Z-Axis (Engine + Road)')
    ax1.set_title("Shadow: Raw Sensor Telemetry")
    ax1.set_ylabel("Acceleration (m/s²)")
    ax1.legend()

    # Filtered Signal (Road anomalies isolated)
    ax2.plot(df['time'], z_filt, color='#f39c12', linewidth=1.5, label='Filtered (Road Only)')
    ax2.set_title("Shadow: Isolated Road Impacts (Butterworth High-Pass >12Hz)")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Acceleration (m/s²)")
    ax2.legend()

    plt.tight_layout()
    
    # Save for the GitHub README
    plt.savefig('impact_analysis.png')
    print("✅ Visualization saved as 'impact_analysis.png'")
    
    # Show the plot window
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_visualization(sys.argv[1])
    else:
        print("Usage: python visualise.py <path_to_csv>")
