"""
Feature 5: Ensemble Stacking classifier.
Combines GB + XGB + threshold predictions via a LogisticRegression meta-learner.
"""

import os
import json
import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    import joblib
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


class EnsembleFloodClassifier:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'ensemble_stacker.joblib')

    feature_names = [
        'pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
        'elevation', 'slope', 'jrc_occ', 'jrc_season'
    ]

    def __init__(self):
        self.gb_model = None
        self.xgb_model = None
        self.meta_model = None
        self.feature_importances_ = None

    def _get_base_predictions(self, X):
        """Get probability predictions from base learners."""
        preds = np.column_stack([
            self.gb_model.predict_proba(X)[:, 1],
        ])
        if self.xgb_model is not None:
            preds = np.column_stack([preds, self.xgb_model.predict_proba(X)[:, 1]])
        return preds

    def train(self, df):
        if not _SKLEARN:
            raise ImportError("scikit-learn is required.")

        X = df[self.feature_names].copy().fillna(0)
        y = df['flood_label'].astype(int)

        # Base learner 1: Gradient Boosting
        self.gb_model = GradientBoostingClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.1,
            subsample=0.8, min_samples_leaf=20, random_state=42
        )
        self.gb_model.fit(X, y)

        # Base learner 2: XGBoost (optional)
        try:
            from xgboost import XGBClassifier
            self.xgb_model = XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.08,
                subsample=0.8, colsample_bytree=0.8,
                random_state=42, eval_metric='logloss', verbosity=0,
            )
            self.xgb_model.fit(X, y)
        except ImportError:
            self.xgb_model = None

        # Meta-learner: Logistic Regression on base predictions + threshold feature
        base_preds = self._get_base_predictions(X)
        # Add threshold-based prediction as extra feature
        threshold_pred = df['flood_label'].values.reshape(-1, 1)
        meta_X = np.hstack([base_preds, threshold_pred])

        self.meta_model = LogisticRegression(random_state=42, max_iter=1000)
        self.meta_model.fit(meta_X, y)

        # Combined feature importance (average of base learners)
        importances = self.gb_model.feature_importances_.copy()
        if self.xgb_model is not None:
            importances = (importances + self.xgb_model.feature_importances_) / 2
        self.feature_importances_ = dict(zip(
            self.feature_names,
            [round(v, 4) for v in importances]
        ))
        return self

    def predict(self, feature_df):
        X = feature_df[self.feature_names].copy().fillna(0)
        base_preds = self._get_base_predictions(X)
        # Use GB prediction as threshold proxy for inference
        threshold_pred = (self.gb_model.predict(X)).reshape(-1, 1)
        meta_X = np.hstack([base_preds, threshold_pred])
        return self.meta_model.predict(meta_X)

    def predict_proba(self, feature_df):
        X = feature_df[self.feature_names].copy().fillna(0)
        base_preds = self._get_base_predictions(X)
        threshold_pred = (self.gb_model.predict(X)).reshape(-1, 1)
        meta_X = np.hstack([base_preds, threshold_pred])
        return self.meta_model.predict_proba(meta_X)[:, 1]

    def save(self):
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        joblib.dump({
            'gb': self.gb_model, 'xgb': self.xgb_model,
            'meta': self.meta_model, 'importances': self.feature_importances_
        }, self.MODEL_PATH)

    def load(self):
        if os.path.exists(self.MODEL_PATH):
            data = joblib.load(self.MODEL_PATH)
            self.gb_model = data['gb']
            self.xgb_model = data.get('xgb')
            self.meta_model = data['meta']
            self.feature_importances_ = data.get('importances')
            return True
        return False

    def classify_for_aoi(self, aoi_json, f_start, f_end, p_start, p_end,
                          threshold, polarization, speckle,
                          return_probability=False):
        import ee
        from ml_models.data_extraction import extract_sar_training_samples, dataframe_to_ee_fc

        pretrained = self.load()

        df = extract_sar_training_samples(
            aoi_json, f_start, f_end, p_start, p_end,
            threshold, polarization, speckle,
            n_points=8000, scale=30
        )

        if df.empty or len(df) < 100:
            return None

        threshold_flood_count = (df['flood_label'] == 1).sum()
        total_count = len(df)

        if not pretrained:
            self.train(df)

        if return_probability:
            df['ml_pred'] = self.predict_proba(df)
        else:
            df['ml_pred'] = self.predict(df)

        ml_flood_count = (df['ml_pred'] >= 0.5).sum() if return_probability else (df['ml_pred'] == 1).sum()

        aoi_geom = ee.Geometry(json.loads(aoi_json))

        if return_probability:
            df['ml_pred_int'] = (df['ml_pred'] * 100).astype(int)
            fc = dataframe_to_ee_fc(df, 'ml_pred_int')
            flood_image = (fc.reduceToImage(['ml_pred_int'], ee.Reducer.first())
                          .clip(aoi_geom).divide(100))
            tile_url = flood_image.getMapId({
                'min': 0, 'max': 1,
                'palette': ['000005', '0d1b2a', '1b4f72', '2e86c1', '00FFFF', 'ffffff']
            })['tile_fetcher'].url_format
        else:
            fc = dataframe_to_ee_fc(df, 'ml_pred')
            flood_image = (fc.reduceToImage(['ml_pred'], ee.Reducer.first())
                          .clip(aoi_geom).selfMask())
            tile_url = flood_image.getMapId({
                'palette': ['FF6B6B']
            })['tile_fetcher'].url_format

        aoi_ha = aoi_geom.area(maxError=1).getInfo() / 10000
        ml_area_ha = round(aoi_ha * ml_flood_count / total_count, 1)
        threshold_area_ha = round(aoi_ha * threshold_flood_count / total_count, 1)

        n_models = 2 if self.xgb_model else 1

        return {
            'tile_url': tile_url,
            'ml_area_ha': ml_area_ha,
            'threshold_area_ha': threshold_area_ha,
            'n_samples': total_count,
            'feature_importance': self.feature_importances_,
            'model_name': f'Ensemble ({n_models} base + LR meta)',
        }
