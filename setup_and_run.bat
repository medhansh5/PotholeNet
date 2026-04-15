@echo off
title PotholeNet: Shadow Edition Setup
echo ------------------------------------------------
echo 🏍️  Initializing PotholeNet: Shadow Edition (Windows)
echo ------------------------------------------------

:: 1. Create and Activate Virtual Environment
echo 📦 Creating Virtual Environment...
python -m venv venv
call venv\Scripts\activate

:: 2. Install Dependencies
echo 📥 Installing Requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 3. Run Pipeline
:: We set PYTHONPATH to the current directory to avoid the ModuleNotFoundError
set PYTHONPATH=%cd%

echo 🔍 Validating Telemetry...
python scripts/data_validator.py

echo 🧠 Training Shadow's Engine...
python scripts/train_model.py

echo 📈 Generating Visuals...
python visualise.py data/pothole_events.csv

echo ------------------------------------------------
echo ✅ Success! Shadow is ready.
echo ------------------------------------------------
pause