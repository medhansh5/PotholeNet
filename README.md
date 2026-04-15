# PotholeNet: Shadow Edition 🏍️📊
### Edge-AI Road Quality Classification for the Royal Enfield Classic 350

PotholeNet is a research-oriented machine learning pipeline designed to map urban infrastructure health using smartphone-integrated inertial sensors. Unlike generic classifiers, this model implements specific digital signal processing (DSP) filters to isolate road anomalies from the 350cc long-stroke engine vibrations of **"Shadow"** (Royal Enfield Classic 350).

---

## 🔬 Scientific Thesis
Two-wheeler riders in India face disproportionate safety risks due to unmapped road degradation. PotholeNet treats the motorcycle as a **Mobile Sensor Node**, utilizing high-frequency telemetry to crowdsource road surface data for safer navigation and municipal maintenance.

### 1. Signal De-noising (DSP)
The Royal Enfield "thump" creates significant low-frequency mechanical noise (~10-15Hz). We implement a **4th-order Butterworth High-Pass filter** (Cutoff: 12Hz) to "mute" the engine and isolate sharp vertical impacts ($Z$-axis displacement).

### 2. Feature Engineering
We extract time-domain statistical features from 100Hz sliding windows:
* **Z-axis RMS Energy**: Quantifies total impact intensity.
* **Peak-to-Peak Amplitude**: Captures the maximum "jolt" magnitude.
* **Vertical Variance ($\sigma$ / Std Dev)**: Identifies sustained road roughness.

### 3. Machine Learning Architecture
A **Random Forest Classifier** was selected for its low-latency performance on edge devices. The model is trained to distinguish between gear shifts, engine revs, and actual potholes.

---

## 📂 Repository Structure
```text
PotholeNet/
├── data/           # CSV Telemetry (Smooth Baseline vs. Pothole Impacts)
├── models/         # Serialized ML (.pkl) Model Registry
├── scripts/        # Data Validation & Automated Training Pipelines
├── potholenet.py   # Core DSP & ML Engine
├── visualize.py    # Signal Analysis & Plotting Suite
└── requirements.txt
```

## 🛠️ Installation & Usage
```bash
# Clone the repository
git clone https://github.com/medhansh5/PotholeNet.git

# Install dependencies
pip install -r requirements.txt

# Run the program
python potholenet.py

# Run visualization to see the filtered signal
python visualize.py
