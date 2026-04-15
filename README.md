# PotholeNet 🏍️📊
### Real-time Road Quality Classification for the Royal Enfield Classic 350

PotholeNet is a research-oriented machine learning project designed to map urban infrastructure health using smartphone-integrated inertial sensors. Unlike generic classifiers, this model implements specific signal-processing filters to isolate road anomalies from the 350cc long-stroke engine vibrations of the **Royal Enfield Classic 350 ("Shadow")**.

---

## 🔬 Scientific Approach
Two-wheelers are disproportionately affected by road quality. PotholeNet treats the motorcycle as a mobile sensor node.

1. **Signal De-noising**: A 4th-order Butterworth High-Pass filter removes engine 'thump' (>12Hz).
2. **Feature Engineering**: Time-domain statistical extraction (RMS, Standard Deviation, Peak-to-Peak).
3. **Classification**: Random Forest Classifier for low-latency, on-edge deployment.

---

## 📲 Data Collection Instructions
To contribute to the dataset or run the model, follow these steps:

### 1. Hardware Setup
- **Vehicle**: Royal Enfield Classic 350.
- **Mount**: Rigid handlebar phone mount (avoid silicone strap mounts).
- **Alignment**: Phone should be perpendicular to the road surface.

### 2. Software Configuration
- Download **Phyphox** (Physical Phone Experiments).
- Select **'Linear Accelerometer'** (This automatically removes Earth's gravity component).
- Set sampling rate to **100 Hz** in settings.

---

## 🛠️ Installation & Usage
```bash
git clone [https://github.com/medhansh5/PotholeNet.git](https://github.com/medhansh5/PotholeNet.git)
pip install -r requirements.txt
python potholenet.py
