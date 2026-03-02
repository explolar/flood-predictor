"""Optuna hyperparameter tuning script for SAR classifiers."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ee
from ml_models.automl_tuner import OptunaTuner
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
    print(f"Extracted {len(df)} samples.")

    feature_names = ['pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
                     'elevation', 'slope', 'jrc_occ', 'jrc_season']

    tuner = OptunaTuner(n_trials=50, cv_folds=3, metric='f1')

    print("\nTuning Gradient Boosting...")
    gb_result = tuner.tune_gradient_boosting(df, feature_names)
    print(f"Best GB score: {gb_result['best_score']}")
    print(f"Best GB params: {gb_result['best_params']}")

    try:
        print("\nTuning XGBoost...")
        xgb_result = tuner.tune_xgboost(df, feature_names)
        print(f"Best XGB score: {xgb_result['best_score']}")
        print(f"Best XGB params: {xgb_result['best_params']}")
    except ImportError:
        print("XGBoost not installed, skipping.")


if __name__ == '__main__':
    main()
