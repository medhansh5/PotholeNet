# 📂 PotholeNet Dataset Directory

This directory contains the inertial sensor data used for training and validating the PotholeNet classifier.

### 🧪 Synthetic Test Files (Pre-calibration)
* **`smooth_road.csv`**: A 100Hz simulation of the **Royal Enfield Classic 350** engine at idle. This file mimics the periodic 12Hz "thump" vibration to verify that the Butterworth High-Pass filter correctly nullifies mechanical noise without triggering false positives.
* **`pothole_events.csv`**: A test file containing high-amplitude vertical impact spikes (simulating 15cm road anomalies). Used to validate the model's sensitivity and Feature Engineering (RMS and Peak-to-Peak) accuracy.

### 🛣️ Real-World Data (Pending Collection)
*Once collected, real-world data from "Shadow" should be stored here using the following naming convention:*
- `RE350_Smooth_[Date].csv`
- `RE350_Pothole_[Date].csv`

---
*Note: All acceleration units are in m/s². Sampling rate fixed at 100Hz via Phyphox Linear Accelerometer.*
