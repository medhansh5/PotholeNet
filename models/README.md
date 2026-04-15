# 🧠 Shadow Model Registry

This directory serves as the model zoo for **Shadow** (Royal Enfield Classic 350). It stores the serialized weights of the Random Forest classifier after training.

## 📂 Current Model Versions

| Version | File | Accuracy | Training Set | Status |
| :--- | :--- | :--- | :--- | :--- |
| **v1.0-alpha** | `shadow_v1.pkl` | 50% | Synthetic Benchmarks | **Active** |
| **v2.0-beta** | `shadow_v2.pkl` | -- | Real-world NCR Telemetry | *Pending* |

## 🔬 Model Technical Specifications

* **Architecture:** Random Forest Classifier (Scikit-Learn).
* **Feature Input:** 4-Dimensional Vector (Filtered Z-STD, Z-Peak, Z-RMS, Z-PTP).
* **Temporal Window:** 1000ms sliding window @ 100Hz.
* **Target Device:** Edge-inference via Python/Smartphone.

## 🛠️ Usage
These models are generated automatically by running the training script from the root directory:
```bash
python scripts/train_model.py
