"""Tests for ML model classes (no GEE calls)."""

import pytest
import numpy as np
import pandas as pd


class TestFloodRiskPredictor:
    def test_train_and_predict(self, sample_risk_df):
        from ml_models.flood_risk_model import FloodRiskPredictor
        predictor = FloodRiskPredictor()
        predictor.train(sample_risk_df)

        assert predictor.model is not None
        assert predictor.oob_score_ is not None
        assert 0 <= predictor.oob_score_ <= 1
        assert predictor.feature_importances_ is not None
        assert len(predictor.feature_importances_) == 6

    def test_predict_returns_valid_classes(self, sample_risk_df):
        from ml_models.flood_risk_model import FloodRiskPredictor
        predictor = FloodRiskPredictor()
        predictor.train(sample_risk_df)
        preds = predictor.predict(sample_risk_df)

        assert len(preds) == len(sample_risk_df)
        assert set(preds).issubset({1, 2, 3, 4, 5})

    def test_save_and_load(self, sample_risk_df, tmp_path):
        from ml_models.flood_risk_model import FloodRiskPredictor
        predictor = FloodRiskPredictor()
        predictor.MODEL_PATH = str(tmp_path / "test_rf.joblib")
        predictor.train(sample_risk_df)
        predictor.save()

        predictor2 = FloodRiskPredictor()
        predictor2.MODEL_PATH = str(tmp_path / "test_rf.joblib")
        loaded = predictor2.load()

        assert loaded is True
        assert predictor2.model is not None
        preds = predictor2.predict(sample_risk_df)
        assert len(preds) == len(sample_risk_df)

    def test_feature_names(self):
        from ml_models.flood_risk_model import FloodRiskPredictor
        predictor = FloodRiskPredictor()
        expected = ['elevation', 'slope', 'annual_rainfall',
                    'lulc_class', 'jrc_occurrence', 'jrc_max_extent']
        assert predictor.feature_names == expected


class TestSARFloodClassifier:
    def test_train_and_predict(self, sample_sar_df):
        from ml_models.sar_classifier import SARFloodClassifier
        clf = SARFloodClassifier()
        clf.train(sample_sar_df)

        assert clf.model is not None
        assert clf.feature_importances_ is not None
        assert len(clf.feature_importances_) == 8

    def test_predict_binary(self, sample_sar_df):
        from ml_models.sar_classifier import SARFloodClassifier
        clf = SARFloodClassifier()
        clf.train(sample_sar_df)
        preds = clf.predict(sample_sar_df)

        assert len(preds) == len(sample_sar_df)
        assert set(preds).issubset({0, 1})

    def test_predict_proba(self, sample_sar_df):
        from ml_models.sar_classifier import SARFloodClassifier
        clf = SARFloodClassifier()
        clf.train(sample_sar_df)
        proba = clf.predict_proba(sample_sar_df)

        assert len(proba) == len(sample_sar_df)
        assert all(0 <= p <= 1 for p in proba)

    def test_save_and_load(self, sample_sar_df, tmp_path):
        from ml_models.sar_classifier import SARFloodClassifier
        clf = SARFloodClassifier()
        clf.MODEL_PATH = str(tmp_path / "test_gb.joblib")
        clf.train(sample_sar_df)
        clf.save()

        clf2 = SARFloodClassifier()
        clf2.MODEL_PATH = str(tmp_path / "test_gb.joblib")
        loaded = clf2.load()

        assert loaded is True
        preds = clf2.predict(sample_sar_df)
        assert len(preds) == len(sample_sar_df)

    def test_handles_nan_features(self, sample_sar_df):
        from ml_models.sar_classifier import SARFloodClassifier
        clf = SARFloodClassifier()
        clf.train(sample_sar_df)

        # Introduce NaNs
        df_nan = sample_sar_df.copy()
        df_nan.loc[0:5, 'jrc_occ'] = np.nan
        preds = clf.predict(df_nan)
        assert len(preds) == len(df_nan)


class TestDataExtraction:
    def test_features_from_info(self):
        from ml_models.data_extraction import _features_from_info

        sample_info = {
            'features': [
                {
                    'geometry': {'type': 'Point', 'coordinates': [85.1, 25.6]},
                    'properties': {'elevation': 50, 'slope': 2.5, 'risk_class': 3}
                },
                {
                    'geometry': {'type': 'Point', 'coordinates': [85.2, 25.7]},
                    'properties': {'elevation': 45, 'slope': 1.8, 'risk_class': 2}
                },
            ]
        }

        df = _features_from_info(sample_info, ['elevation', 'slope'], 'risk_class')
        assert len(df) == 2
        assert 'elevation' in df.columns
        assert 'slope' in df.columns
        assert 'risk_class' in df.columns
        assert 'latitude' in df.columns
        assert 'longitude' in df.columns

    def test_features_from_info_drops_na(self):
        from ml_models.data_extraction import _features_from_info

        sample_info = {
            'features': [
                {
                    'geometry': {'type': 'Point', 'coordinates': [85.1, 25.6]},
                    'properties': {'elevation': 50, 'slope': None}
                },
                {
                    'geometry': {'type': 'Point', 'coordinates': [85.2, 25.7]},
                    'properties': {'elevation': 45, 'slope': 1.8}
                },
            ]
        }

        df = _features_from_info(sample_info, ['elevation', 'slope'])
        assert len(df) == 1
