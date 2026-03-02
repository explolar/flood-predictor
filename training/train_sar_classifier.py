"""
Offline training script for the Gradient Boosting SAR flood classifier.
Extracts SAR features from known flood events via GEE,
trains the classifier, and saves to models/sar_classifier_gb.joblib.

Usage:
    python training/train_sar_classifier.py

Requires: authenticated GEE session, ~10 minutes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import ee
import json
import pandas as pd
from ml_models.data_extraction import extract_sar_training_samples
from ml_models.sar_classifier import SARFloodClassifier

# Initialize GEE
project_id = 'xward-481405'
try:
    ee.Initialize(project=project_id)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=project_id)

print("GEE initialized successfully.")

# Define training events: known flood regions with pre/post dates
events = [
    {
        "name": "Patna Bihar 2024 monsoon",
        "bbox": [84.90, 25.50, 85.30, 25.80],
        "pre": ("2024-05-01", "2024-05-30"),
        "post": ("2024-08-01", "2024-08-30"),
    },
    {
        "name": "Assam 2024 monsoon",
        "bbox": [91.60, 26.10, 91.90, 26.30],
        "pre": ("2024-04-01", "2024-04-30"),
        "post": ("2024-07-01", "2024-07-31"),
    },
    {
        "name": "Kerala 2024 monsoon",
        "bbox": [76.20, 9.90, 76.40, 10.10],
        "pre": ("2024-03-01", "2024-03-31"),
        "post": ("2024-08-01", "2024-08-31"),
    },
]

all_samples = []
for event in events:
    print(f"  Extracting SAR features from {event['name']}...")
    bbox = event['bbox']
    aoi_json = json.dumps(ee.Geometry.BBox(*bbox).getInfo())
    try:
        df = extract_sar_training_samples(
            aoi_json,
            f_start=event['post'][0], f_end=event['post'][1],
            p_start=event['pre'][0], p_end=event['pre'][1],
            threshold=3.0, polarization='VH', speckle=True,
            n_points=5000, scale=30
        )
        print(f"    Got {len(df)} samples (flood: {(df['flood_label']==1).sum()}, non-flood: {(df['flood_label']==0).sum()})")
        all_samples.append(df)
    except Exception as e:
        print(f"    FAILED: {e}")

if not all_samples:
    print("ERROR: No training data extracted.")
    sys.exit(1)

combined = pd.concat(all_samples, ignore_index=True)
print(f"\nTotal training samples: {len(combined)}")
print(f"Class distribution:\n{combined['flood_label'].value_counts().sort_index()}")

# Train
print("\nTraining Gradient Boosting classifier...")
classifier = SARFloodClassifier()
classifier.train(combined)

print(f"Feature Importance: {classifier.feature_importances_}")

# Save
classifier.save()
print(f"\nModel saved to {classifier.MODEL_PATH}")
