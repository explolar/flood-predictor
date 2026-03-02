"""
LightGBM SAR flood classifier.
Same interface as SARFloodClassifier but uses LightGBM for faster training on large datasets.
"""

import os
import json
import numpy as np
import pandas as pd

try:
    from lightgbm import LGBMClassifier
    import joblib
    _LGBM = True
except ImportError:
    _LGBM = False


class LGBMFloodClassifier:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'sar_classifier_lgbm.joblib')

    feature_names = [
        'pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
        'elevation', 'slope', 'jrc_occ', 'jrc_season'
    ]

    def __init__(self):
        self.model = None
        self.feature_importances_ = None

    def load(self):
        if not _LGBM:
            raise ImportError("lightgbm is required. Run: pip install lightgbm")
        if os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            self.feature_importances_ = dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))
            return True
        return False

    def train(self, df):
        if not _LGBM:
            raise ImportError("lightgbm is required. Run: pip install lightgbm")

        X = df[self.feature_names].copy().fillna(0)
        y = df['flood_label'].astype(int)

        self.model = LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=20,
            is_unbalance=True,
            random_state=42,
            verbose=-1,
        )
        self.model.fit(X, y)

        self.feature_importances_ = dict(zip(
            self.feature_names,
            [round(v, 4) for v in self.model.feature_importances_]
        ))
        return self

    def save(self):
        os.makedirs(os.path.dirname(self.MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, self.MODEL_PATH)

    def predict(self, feature_df):
        X = feature_df[self.feature_names].copy().fillna(0)
        return self.model.predict(X)

    def predict_proba(self, feature_df):
        X = feature_df[self.feature_names].copy().fillna(0)
        return self.model.predict_proba(X)[:, 1]

    def classify_for_aoi(self, aoi_json, f_start, f_end, p_start, p_end,
                          threshold, polarization, speckle,
                          return_probability=False):
        import ee
        from ml_models.data_extraction import extract_sar_training_samples, dataframe_to_ee_fc

        pretrained = self.load()

        df = extract_sar_training_samples(
            aoi_json, f_start, f_end, p_start, p_end,
            threshold, polarization, speckle,
            n_points=4000, scale=30
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

        return {
            'tile_url': tile_url,
            'ml_area_ha': ml_area_ha,
            'threshold_area_ha': threshold_area_ha,
            'n_samples': total_count,
            'feature_importance': self.feature_importances_,
            'model_name': 'LightGBM',
        }
