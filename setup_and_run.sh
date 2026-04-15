#!/bin/bash
# PotholeNet: Shadow Edition - Unix Setup
echo "------------------------------------------------"
echo "🏍️  Initializing PotholeNet: Shadow Edition"
echo "------------------------------------------------"

# 1. Environment Setup
python3 -m venv venv
source venv/bin/activate

# 2. Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Execution
echo "🔍 Validating data..."
python3 scripts/data_validator.py

echo "🧠 Training Shadow's Engine..."
python3 scripts/train_model.py

echo "📈 Generating Visuals..."
python3 visualise.py data/pothole_events.csv

echo "------------------------------------------------"
echo "✅ Setup Complete. Check 'models/' and 'impact_analysis.png'"