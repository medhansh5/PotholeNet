# PotholeNet 🏍️📊
### Real-time Road Quality Classification for the Royal Enfield Classic 350

PotholeNet is a research-oriented machine learning project designed to map urban infrastructure health using smartphone-integrated inertial sensors. Unlike generic classifiers, this model implements specific signal-processing filters to isolate road anomalies from the 350cc long-stroke engine vibrations of the **Royal Enfield Classic 350 ("The Baron")**.

---

## 🔬 Scientific Approach
Two-wheelers are disproportionately affected by road quality. PotholeNet treats the motorcycle as a mobile sensor node to crowdsource infrastructure data.

### 1. Signal De-noising
The Royal Enfield "thump" creates significant low-frequency noise. We implement a **4th-order Butterworth High-Pass filter** (cutoff: 12Hz) to "mute" the engine and isolate sharp vertical impacts.

### 2. Feature Engineering
We extract time-domain statistical features from sliding windows of data:
* **Z-axis RMS Energy**: Measures total impact intensity.
* **Peak-to-Peak Amplitude**: Captures the maximum "jolt" of a pothole.
* **Vertical Variance (Std Dev)**: Identifies sustained rough patches.

### 3. Machine Learning
A **Random Forest Classifier** is used for its low-latency performance, making it ideal for future deployment on edge devices or smartphone apps.

---

## 📲 Data Collection Protocol
To maintain high data fidelity, follow these steps:

1. **Hardware**: Rigid handlebar mount on a **RE Classic 350**. 
2. **Software**: Use **Phyphox** (Linear Accelerometer) at a **100 Hz** sampling rate.
3. **Labels**: Record separate CSVs for `smooth_road.csv` and `pothole_events.csv`.

---

## 🛠️ Installation & Usage
```bash
# Clone the repository
git clone [https://github.com/medhansh5/PotholeNet.git](https://github.com/medhansh5/PotholeNet.git)

# Install dependencies
pip install -r requirements.txt

# Run the program
python potholenet.py

# Run visualization to see the filtered signal
python visualize.py
