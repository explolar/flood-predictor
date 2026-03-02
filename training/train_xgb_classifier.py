"""Training script for XGBoost SAR flood classifier."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ee
from ml_models.xgb_classifier import XGBFloodClassifier
from ml_models.data_extraction import extract_sar_training_samples
import json


def main():
    ee.Initialize(project='xward-481405')

    aoi_json = json.dumps({
        "type": "Polygon",
        "coordinates": [[[84.90, 25.50], [85.30, 25.50], [85.30, 25.80], [84.90, 25.80], [84.90, 25.50]]]
    })

    print("Extracting SAR training samples from GEE...")
    df = extract_sar_training_samples(
        aoi_json, '2024-08-01', '2024-08-30', '2024-05-01', '2024-05-30',
        threshold=3.0, polarization='VH', speckle=True, n_points=10000, scale=30
    )
    print(f"Extracted {len(df)} samples. Flood ratio: {df['flood_label'].mean():.2%}")

    clf = XGBFloodClassifier()
    clf.train(df)
    clf.save()
    print(f"Model saved to {clf.MODEL_PATH}")
    print(f"Feature importances: {clf.feature_importances_}")


if __name__ == '__main__':
    main()
