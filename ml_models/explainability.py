"""
Feature 4: SHAP Explainability for ML flood models.
Generates SHAP summary plots and spatial SHAP maps.
"""

import numpy as np
import pandas as pd
import io
import base64

try:
    import shap
    _SHAP = True
except ImportError:
    _SHAP = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _MPL = True
except ImportError:
    _MPL = False


class SHAPExplainer:
    """SHAP-based model explainability for tree-based flood classifiers."""

    def __init__(self):
        if not _SHAP:
            raise ImportError("shap is required. Run: pip install shap")
        if not _MPL:
            raise ImportError("matplotlib is required. Run: pip install matplotlib")
        self.explainer = None
        self.shap_values = None

    def explain(self, model, feature_df, feature_names, max_samples=500):
        """
        Compute SHAP values for a trained model.

        Args:
            model: A fitted scikit-learn / XGBoost / LightGBM model.
            feature_df: DataFrame with feature columns.
            feature_names: List of feature column names.
            max_samples: Max samples for SHAP computation (for speed).
        """
        X = feature_df[feature_names].copy().fillna(0)
        if len(X) > max_samples:
            X = X.sample(n=max_samples, random_state=42)

        self.explainer = shap.TreeExplainer(model)
        self.shap_values = self.explainer.shap_values(X)

        # For binary classifiers, shap_values may be a list [class_0, class_1]
        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]  # class 1 = flood

        return {
            'shap_values': self.shap_values,
            'feature_names': feature_names,
            'X': X,
            'n_samples': len(X),
        }

    def summary_plot_base64(self, max_display=10):
        """Generate a SHAP summary plot and return as base64 PNG."""
        if self.shap_values is None:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        shap.summary_plot(
            self.shap_values,
            features=self.explainer.data if hasattr(self.explainer, 'data') else None,
            show=False,
            max_display=max_display,
            plot_type='bar',
            color='#00FFFF',
        )
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                    facecolor='#0a0f1a', edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

    def get_feature_shap_df(self, feature_names):
        """Return mean absolute SHAP values per feature as a DataFrame."""
        if self.shap_values is None:
            return None

        mean_abs = np.abs(self.shap_values).mean(axis=0)
        df = pd.DataFrame({
            'Feature': feature_names,
            'Mean |SHAP|': [round(v, 4) for v in mean_abs]
        }).sort_values('Mean |SHAP|', ascending=False)
        return df

    def get_spatial_shap(self, feature_df, feature_names, target_feature):
        """
        Get per-sample SHAP values for a specific feature (for spatial mapping).

        Returns a DataFrame with latitude, longitude, and shap_value columns.
        """
        if self.shap_values is None:
            return None

        feat_idx = feature_names.index(target_feature)
        X = feature_df[feature_names].copy().fillna(0)
        if len(X) > len(self.shap_values):
            X = X.iloc[:len(self.shap_values)]

        result = pd.DataFrame({
            'latitude': feature_df['latitude'].iloc[:len(self.shap_values)].values,
            'longitude': feature_df['longitude'].iloc[:len(self.shap_values)].values,
            'shap_value': self.shap_values[:, feat_idx],
        })
        return result
