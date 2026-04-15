import pandas as pd
import matplotlib.pyplot as plt
from potholenet import PotholeNet

def plot_impact_analysis(csv_file):
    """
    Loads ride data and plots Raw vs. Filtered Z-axis acceleration.
    This demonstrates the effectiveness of the Butterworth filter.
    """
    # 1. Load Data
    df = pd.read_csv(csv_file)
    
    # 2. Initialize the Detector
    detector = PotholeNet(sampling_rate=100)
    
    # 3. Process a segment of the data
    raw_z = df['z'].values
    filtered_z = detector._apply_butterworth_highpass(raw_z)
    
    # 4. Create the Visualization
    plt.figure(figsize=(12, 6))
    
    # Plot Raw Signal (Includes engine 'thump')
    plt.subplot(2, 1, 1)
    plt.plot(raw_z, color='red', alpha=0.5, label='Raw Signal (Engine + Road)')
    plt.title(f"Sensor Data Analysis: {csv_file}")
    plt.ylabel("Acceleration (m/s²)")
    plt.legend()
    
    # Plot Filtered Signal (Pothole Signature)
    plt.subplot(2, 1, 2)
    plt.plot(filtered_z, color='blue', label='Filtered Signal (Road Anomalies Only)')
    plt.xlabel("Samples (at 100Hz)")
    plt.ylabel("Acceleration (m/s²)")
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('impact_analysis.png') # Saves as a high-res image for your GitHub
    plt.show()

if __name__ == "__main__":
    # Replace with your actual filename after your ride
    # plot_impact_analysis('data/pothole_events.csv')
    print("Visualization Engine Ready. Run with a CSV file to generate plots.")
