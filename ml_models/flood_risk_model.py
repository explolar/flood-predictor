"""
Model 1: Random Forest flood risk predictor.
Trains on GEE-extracted terrain/climate features to predict 5-class flood risk.
Can load pre-trained .joblib or train on-the-fly for the current AOI.
"""

import os
import json
import numpy as np
import pandas as pd
import ee

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    import joblib
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


class FloodRiskPredictor:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'flood_risk_rf.joblib')

    feature_names = [
        'elevation', 'slope', 'annual_rainfall',
        'lulc_class', 'jrc_occurrence', 'jrc_max_extent'
    ]

    def __init__(self):
        self.model = None
        self.oob_score_ = None
        self.feature_importances_ = None

    def load(self):
        """Load pre-trained model from disk."""
        if not _SKLEARN:
            raise ImportError("scikit-learn is required. Run: pip install scikit-learn")
        if os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            self.feature_importances_ = dict(zip(
                self.model.feature_names_in_,
                self.model.feature_importances_
            ))
            self.oob_score_ = getattr(self.model, 'oob_score_', None)
            return True
        return False

    def train(self, df):
        """Train from a DataFrame of GEE-extracted samples."""
        if not _SKLEARN:
            raise ImportError("scikit-learn is required. Run: pip install scikit-learn")

        X = df[self.feature_names].copy()
        y = df['risk_class'].astype(int)

        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_leaf=10,
            class_weight='balanced',
            oob_score=True,
            n_jobs=-1,
            random_state=42
        )
        self.model.fit(X, y)

        self.oob_score_ = round(self.model.oob_score_, 3)
        self.feature_importances_ = dict(zip(
            self.feature_names,
            [round(v, 4) for v in self.model.feature_importances_]
        ))
        return self

    def save(self):
        """Save trained model to disk."""
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, self.MODEL_PATH)

    def predict(self, feature_df):
        """Predict risk classes from a feature DataFrame."""
        X = feature_df[self.feature_names].copy()
        return self.model.predict(X)

    def predict_for_aoi(self, aoi_json):
        """
        End-to-end: extract features from GEE, train (or load), predict,
        and return a tile URL for map rendering.
        """
        from ml_models.data_extraction import extract_risk_training_samples, dataframe_to_ee_fc

        # Try loading pre-trained model
        pretrained = self.load()

        # Extract sample points from the AOI
        df = extract_risk_training_samples(aoi_json, n_points=5000, scale=100)

        if df.empty or len(df) < 50:
            return None

        if not pretrained:
            # Train on-the-fly using the AOI's own data
            self.train(df)

        # Predict on all sampled points
        df['risk_pred'] = self.predict(df)

        # Reconstruct as GEE image
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        fc = dataframe_to_ee_fc(df, 'risk_pred')
        risk_image = (fc.reduceToImage(['risk_pred'], ee.Reducer.first())
                      .clip(aoi_geom)
                      .rename('risk'))

        tile_url = risk_image.getMapId({
            'min': 1, 'max': 5,
            'palette': ['1a9850', '91cf60', 'ffffbf', 'fc8d59', 'd73027']
        })['tile_fetcher'].url_format

        return {
            'tile_url': tile_url,
            'n_samples': len(df),
            'oob_score': self.oob_score_,
            'feature_importance': self.feature_importances_,
        }
