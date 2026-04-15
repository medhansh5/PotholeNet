# 🛠️ Utility & Automation Scripts

This folder contains the execution pipeline for data processing and model training for the Shadow project.

### 📜 Script Inventory
* **`train_model.py`**: The primary training pipeline. It ingests CSV data from `/data`, applies the Butterworth filter, extracts features, and exports a serialized `.pkl` model to `/models`.
* **`data_validator.py`** *(Optional)*: Checks incoming Phyphox CSVs for correct sampling rates (100Hz) and column headers before training.

### 🚀 How to Retrain
To update the model with new ride data from your ride, run:
```bash
python scripts/train_model.py
