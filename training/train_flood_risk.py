"""
Offline training script for the Random Forest flood risk model.
Extracts training data from multiple flood-prone regions via GEE,
trains the model, and saves to models/flood_risk_rf.joblib.

Usage:
    python training/train_flood_risk.py

Requires: authenticated GEE session, ~5 minutes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import ee
import json
import pandas as pd
from ml_models.data_extraction import extract_risk_training_samples
from ml_models.flood_risk_model import FloodRiskPredictor

# Initialize GEE
project_id = 'xward-481405'
try:
    ee.Initialize(project=project_id)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=project_id)

print("GEE initialized successfully.")

# Define training regions (flood-prone areas across India)
regions = [
    {"name": "Patna, Bihar",    "bbox": [84.90, 25.50, 85.30, 25.80]},
    {"name": "Kolkata, WB",     "bbox": [88.20, 22.40, 88.60, 22.70]},
    {"name": "Chennai, TN",     "bbox": [80.10, 12.80, 80.40, 13.20]},
    {"name": "Guwahati, Assam", "bbox": [91.60, 26.10, 91.90, 26.30]},
    {"name": "Kochi, Kerala",   "bbox": [76.20, 9.90, 76.40, 10.10]},
]

all_samples = []
for region in regions:
    print(f"  Extracting samples from {region['name']}...")
    bbox = region['bbox']
    aoi_json = json.dumps(ee.Geometry.BBox(*bbox).getInfo())
    try:
        df = extract_risk_training_samples(aoi_json, n_points=3000, scale=100)
        print(f"    Got {len(df)} samples")
        all_samples.append(df)
    except Exception as e:
        print(f"    FAILED: {e}")

if not all_samples:
    print("ERROR: No training data extracted. Check GEE connectivity.")
    sys.exit(1)

combined = pd.concat(all_samples, ignore_index=True)
print(f"\nTotal training samples: {len(combined)}")
print(f"Class distribution:\n{combined['risk_class'].value_counts().sort_index()}")

# Train
print("\nTraining Random Forest...")
predictor = FloodRiskPredictor()
predictor.train(combined)

print(f"OOB Score: {predictor.oob_score_}")
print(f"Feature Importance: {predictor.feature_importances_}")

# Save
predictor.save()
print(f"\nModel saved to {predictor.MODEL_PATH}")
