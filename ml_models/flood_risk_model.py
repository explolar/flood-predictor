"""
Model 1: Random Forest flood risk predictor.
Trains on GEE-extracted terrain/climate features to predict 5-class flood risk.
Can load pre-trained .joblib or train on-the-fly for the current AOI.
"""

import json
import os

import ee
import numpy as np
import pandas as pd

try:
    import joblib
    from sklearn.ensemble import RandomForestClassifier

    _SKLEARN = True
except ImportError:
    _SKLEARN = False


class FloodRiskPredictor:
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "flood_risk_rf.joblib")
    MODEL_PATH_ERA5 = os.path.join(os.path.dirname(__file__), "..", "models", "flood_risk_rf_era5.joblib")

    BASE_FEATURES = [
        "elevation",
        "slope",
        "annual_rainfall",
        "lulc_class",
        "jrc_occurrence",
        "jrc_max_extent",
    ]
    ERA5_FEATURES = [
        "era5_annual_precip",
        "era5_annual_runoff",
        "era5_mean_sm_shallow",
        "era5_mean_sm_deep",
        "era5_mean_temp",
    ]

    def __init__(self, include_era5=False):
        self.include_era5 = include_era5
        self.feature_names = self.BASE_FEATURES + (self.ERA5_FEATURES if include_era5 else [])
        self.model = None
        self.oob_score_ = None
        self.feature_importances_ = None

    def _model_path(self):
        return self.MODEL_PATH_ERA5 if self.include_era5 else self.MODEL_PATH

    def load(self):
        """Load pre-trained model from disk."""
        if not _SKLEARN:
            raise ImportError("scikit-learn is required. Run: pip install scikit-learn")
        path = self._model_path()
        if os.path.exists(path):
            self.model = joblib.load(path)
            # Align feature_names with whatever the loaded model was trained on
            self.feature_names = list(self.model.feature_names_in_)
            self.feature_importances_ = dict(zip(self.model.feature_names_in_, self.model.feature_importances_))
            self.oob_score_ = getattr(self.model, "oob_score_", None)
            return True
        return False

    def train(self, df):
        """Train from a DataFrame of GEE-extracted samples."""
        if not _SKLEARN:
            raise ImportError("scikit-learn is required. Run: pip install scikit-learn")

        X = df[self.feature_names].copy()
        y = df["risk_class"].astype(int)

        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_leaf=10,
            class_weight="balanced",
            oob_score=True,
            n_jobs=-1,
            random_state=42,
        )
        self.model.fit(X, y)

        self.oob_score_ = round(self.model.oob_score_, 3)
        self.feature_importances_ = dict(
            zip(self.feature_names, [round(v, 4) for v in self.model.feature_importances_])
        )
        return self

    def save(self):
        """Save trained model to disk."""
        path = self._model_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump(self.model, path)

    def predict(self, feature_df):
        """Predict risk classes from a feature DataFrame."""
        X = feature_df[self.feature_names].copy()
        return self.model.predict(X)

    def predict_future_risk(self, aoi_json, scenario="ssp245", model="ACCESS-CM2", start_year=2030, end_year=2050):
        """
        Predict flood risk using CMIP6-projected rainfall instead of current CHIRPS.

        Keeps terrain features (elevation, slope, LULC, JRC) static and swaps in
        future projected precipitation. Returns tile URL + metadata, or None.
        """
        from gee_functions.cmip6 import get_cmip6_risk_feature_stack
        from ml_models.data_extraction import _features_from_info, dataframe_to_ee_fc

        # Ensure we have a trained model (base features only for future projection)
        if self.model is None:
            loaded = self.load()
            if not loaded:
                # Train on current data first
                self.predict_for_aoi(aoi_json)
            if self.model is None:
                return None

        aoi_geom = ee.Geometry(json.loads(aoi_json))
        future_stack = get_cmip6_risk_feature_stack(
            aoi_json,
            scenario=scenario,
            model=model,
            start_year=start_year,
            end_year=end_year,
        )
        if future_stack is None:
            return None

        # Sample the future feature stack
        feature_names = self.BASE_FEATURES
        samples = future_stack.sample(
            region=aoi_geom,
            scale=100,
            numPixels=5000,
            seed=42,
            geometries=True,
        )
        sample_info = samples.getInfo()
        df = _features_from_info(sample_info, feature_names)

        if df.empty or len(df) < 50:
            return None

        # Predict using only base features (CMIP6 stack has base features)
        X = df[self.BASE_FEATURES].copy()
        df["risk_pred"] = self.model.predict(X)

        # Risk class distribution
        dist = df["risk_pred"].value_counts().sort_index().to_dict()

        # Reconstruct as GEE image
        fc = dataframe_to_ee_fc(df, "risk_pred")
        risk_image = fc.reduceToImage(["risk_pred"], ee.Reducer.first()).clip(aoi_geom).rename("risk")

        tile_url = risk_image.getMapId(
            {"min": 1, "max": 5, "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"]}
        )["tile_fetcher"].url_format

        return {
            "tile_url": tile_url,
            "n_samples": len(df),
            "risk_distribution": dist,
            "scenario": scenario,
            "model": model,
            "period": f"{start_year}-{end_year}",
        }

    def predict_future_risk_ensemble(self, aoi_json, scenario="ssp245", models=None, start_year=2030, end_year=2050):
        """
        Multi-model ensemble: run future risk prediction across multiple GCMs,
        then take the mode (majority vote) per sample point.

        Also computes a risk delta image (future - current) for spatial change mapping.

        Returns dict with ensemble tile, delta tile, per-model distributions, or None.
        """
        from gee_functions.cmip6 import AVAILABLE_MODELS, get_cmip6_risk_feature_stack
        from ml_models.data_extraction import _features_from_info, dataframe_to_ee_fc

        if models is None:
            models = AVAILABLE_MODELS[:4]  # Default: first 4 GCMs

        # Ensure trained model
        if self.model is None:
            loaded = self.load()
            if not loaded:
                self.predict_for_aoi(aoi_json)
            if self.model is None:
                return None

        aoi_geom = ee.Geometry(json.loads(aoi_json))

        # Collect predictions from each GCM on a shared sample grid
        # Use the first available model's stack to define sample locations
        ref_stack = None
        for m in models:
            ref_stack = get_cmip6_risk_feature_stack(
                aoi_json,
                scenario=scenario,
                model=m,
                start_year=start_year,
                end_year=end_year,
            )
            if ref_stack is not None:
                break
        if ref_stack is None:
            return None

        # Sample locations (shared across all models)
        ref_samples = ref_stack.sample(
            region=aoi_geom,
            scale=100,
            numPixels=5000,
            seed=42,
            geometries=True,
        )
        ref_info = ref_samples.getInfo()
        ref_df = _features_from_info(ref_info, self.BASE_FEATURES)
        if ref_df.empty or len(ref_df) < 50:
            return None

        # Current risk prediction on the same points
        X_current = ref_df[self.BASE_FEATURES].copy()
        ref_df["current_risk"] = self.model.predict(X_current)

        # Predict for each GCM model
        model_preds = {}
        per_model_dist = {}
        for gcm in models:
            stack = get_cmip6_risk_feature_stack(
                aoi_json,
                scenario=scenario,
                model=gcm,
                start_year=start_year,
                end_year=end_year,
            )
            if stack is None:
                continue

            samples = stack.sample(
                region=aoi_geom,
                scale=100,
                numPixels=5000,
                seed=42,
                geometries=True,
            )
            s_info = samples.getInfo()
            df_gcm = _features_from_info(s_info, self.BASE_FEATURES)
            if df_gcm.empty or len(df_gcm) < 50:
                continue

            preds = self.model.predict(df_gcm[self.BASE_FEATURES].copy())
            model_preds[gcm] = preds
            per_model_dist[gcm] = dict(pd.Series(preds).value_counts().sort_index())

        if not model_preds:
            return None

        # Ensemble: mode across GCMs (majority vote per sample)
        pred_matrix = np.column_stack(list(model_preds.values()))
        # Row-wise mode using numpy (avoids scipy dependency)
        ensemble_preds = np.apply_along_axis(
            lambda row: np.bincount(row.astype(int), minlength=6).argmax(),
            axis=1,
            arr=pred_matrix,
        )
        ref_df["risk_pred"] = ensemble_preds.astype(int)

        # Risk delta: future - current (positive = risk increased)
        ref_df["risk_delta"] = ref_df["risk_pred"] - ref_df["current_risk"]

        # Distributions
        ensemble_dist = ref_df["risk_pred"].value_counts().sort_index().to_dict()
        current_dist = ref_df["current_risk"].value_counts().sort_index().to_dict()

        # Build GEE images
        # Ensemble risk map
        fc_ens = dataframe_to_ee_fc(ref_df, "risk_pred")
        ens_image = fc_ens.reduceToImage(["risk_pred"], ee.Reducer.first()).clip(aoi_geom).rename("risk")
        ens_tile = ens_image.getMapId(
            {"min": 1, "max": 5, "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"]}
        )["tile_fetcher"].url_format

        # Delta map (range -4 to +4, diverging palette)
        fc_delta = dataframe_to_ee_fc(ref_df, "risk_delta")
        delta_image = fc_delta.reduceToImage(["risk_delta"], ee.Reducer.first()).clip(aoi_geom).rename("delta")
        delta_tile = delta_image.getMapId(
            {"min": -3, "max": 3, "palette": ["1a9850", "91cf60", "d9ef8b", "f7f7f7", "fee08b", "fc8d59", "d73027"]}
        )["tile_fetcher"].url_format

        # Current risk map tile (for side-by-side)
        fc_cur = dataframe_to_ee_fc(ref_df, "current_risk")
        cur_image = fc_cur.reduceToImage(["current_risk"], ee.Reducer.first()).clip(aoi_geom).rename("risk")
        cur_tile = cur_image.getMapId(
            {"min": 1, "max": 5, "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"]}
        )["tile_fetcher"].url_format

        # Mean delta
        mean_delta = round(ref_df["risk_delta"].mean(), 2)

        return {
            "ensemble_tile_url": ens_tile,
            "delta_tile_url": delta_tile,
            "current_tile_url": cur_tile,
            "n_samples": len(ref_df),
            "n_models": len(model_preds),
            "models_used": list(model_preds.keys()),
            "ensemble_distribution": ensemble_dist,
            "current_distribution": current_dist,
            "per_model_distribution": per_model_dist,
            "mean_risk_delta": mean_delta,
            "scenario": scenario,
            "period": f"{start_year}-{end_year}",
        }

    def predict_for_aoi(self, aoi_json):
        """
        End-to-end: extract features from GEE, train (or load), predict,
        and return a tile URL for map rendering.
        """
        from ml_models.data_extraction import dataframe_to_ee_fc, extract_risk_training_samples

        # Try loading pre-trained model
        pretrained = self.load()

        # Extract sample points from the AOI
        df = extract_risk_training_samples(aoi_json, n_points=5000, scale=100, include_era5=self.include_era5)

        if df.empty or len(df) < 50:
            return None

        if not pretrained:
            # Train on-the-fly using the AOI's own data
            self.train(df)

        # Predict on all sampled points
        df["risk_pred"] = self.predict(df)

        # Risk class distribution
        dist = df["risk_pred"].value_counts().sort_index().to_dict()

        # Reconstruct as GEE image
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        fc = dataframe_to_ee_fc(df, "risk_pred")
        risk_image = fc.reduceToImage(["risk_pred"], ee.Reducer.first()).clip(aoi_geom).rename("risk")

        tile_url = risk_image.getMapId(
            {"min": 1, "max": 5, "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"]}
        )["tile_fetcher"].url_format

        return {
            "tile_url": tile_url,
            "n_samples": len(df),
            "oob_score": self.oob_score_,
            "feature_importance": self.feature_importances_,
            "risk_distribution": dist,
        }
