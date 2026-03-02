"""
Feature 6: Anomaly Detection using Isolation Forest.
Detects unusual SAR backscatter patterns that may indicate flooding
by analyzing monthly SAR statistics against historical patterns.
"""

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import IsolationForest
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


class FloodAnomalyDetector:
    """Detect anomalous SAR conditions using Isolation Forest."""

    def __init__(self, contamination=0.1):
        if not _SKLEARN:
            raise ImportError("scikit-learn is required.")
        self.contamination = contamination
        self.model = None
        self.results = None

    def detect_from_monthly_stats(self, monthly_df):
        """
        Detect anomalies from monthly SAR statistics.

        Args:
            monthly_df: DataFrame with columns:
                - year, month
                - mean_backscatter, std_backscatter
                - min_backscatter, flood_fraction (optional)

        Returns:
            dict with anomaly results.
        """
        feature_cols = [c for c in ['mean_backscatter', 'std_backscatter',
                                     'min_backscatter', 'flood_fraction']
                        if c in monthly_df.columns]

        if len(feature_cols) < 2:
            return None

        X = monthly_df[feature_cols].copy().fillna(0)

        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=200,
            max_samples='auto',
            random_state=42,
        )
        labels = self.model.fit_predict(X)
        scores = self.model.decision_function(X)

        result_df = monthly_df.copy()
        result_df['anomaly'] = (labels == -1).astype(int)
        result_df['anomaly_score'] = scores

        self.results = result_df

        anomalous = result_df[result_df['anomaly'] == 1]

        return {
            'result_df': result_df,
            'n_anomalies': len(anomalous),
            'n_total': len(result_df),
            'anomaly_months': anomalous[['year', 'month']].to_dict('records') if not anomalous.empty else [],
            'features_used': feature_cols,
        }

    def detect_from_sar_timeseries(self, aoi_json, start_year=2018, end_year=2024,
                                    polarization='VH'):
        """
        Full pipeline: fetch monthly SAR stats from GEE and detect anomalies.

        Returns dict with anomaly results.
        """
        from gee_functions.sar_timeseries import get_sar_monthly_stats

        monthly_df = get_sar_monthly_stats(aoi_json, start_year, end_year, polarization)

        if monthly_df is None or len(monthly_df) < 12:
            return None

        return self.detect_from_monthly_stats(monthly_df)

    def get_anomaly_chart_data(self):
        """Return DataFrame formatted for Streamlit chart rendering."""
        if self.results is None:
            return None

        df = self.results.copy()
        df['date_label'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)
        return df.set_index('date_label')
