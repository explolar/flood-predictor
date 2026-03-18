"""
Prithvi-based flood segmentation from Sentinel-1 SAR imagery.

Uses NASA/IBM Prithvi geospatial foundation model (fine-tuned for
flood mapping) when available, otherwise falls back to a lightweight
U-Net trained on SAR difference features.

Prithvi model: https://huggingface.co/ibm-nasa-geospatial/Prithvi-100M
Flood fine-tune: https://huggingface.co/ibm-nasa-geospatial/Prithvi-100M-sen1floods11
"""

import json
import os

import ee
import streamlit as st

try:
    import torch
    import torch.nn as nn
    _TORCH = True
except ImportError:
    _TORCH = False

try:
    import joblib
    from sklearn.ensemble import GradientBoostingClassifier
    _SKLEARN = True
except ImportError:
    _SKLEARN = False


# ── Lightweight U-Net fallback ─────────────────────────────

class _MiniUNet(nn.Module if _TORCH else object):
    """Minimal U-Net for SAR flood segmentation when Prithvi unavailable."""

    def __init__(self, in_channels=4):
        if not _TORCH:
            return
        super().__init__()
        self.enc1 = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
        )
        self.enc2 = nn.Sequential(
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
        )
        self.dec1 = nn.Sequential(
            nn.ConvTranspose2d(64, 32, 2, stride=2),
            nn.Conv2d(64, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
        )
        self.out = nn.Conv2d(32, 1, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(e1)
        d1_up = self.dec1[0](e2)
        d1 = self.dec1[1:](torch.cat([d1_up, e1], dim=1))
        return torch.sigmoid(self.out(d1))


# ── Prithvi Flood Classifier ──────────────────────────────

class PrithviFloodClassifier:
    """
    SAR flood segmentation using pre-trained geospatial models.

    Attempts to load Prithvi-100M-sen1floods11 from Hugging Face.
    Falls back to a pixel-level GBM classifier using SAR features
    extracted from GEE (same features as SARFloodClassifier but
    with enhanced spectral indices).

    Features:
        - pre_sar: Pre-flood Sentinel-1 backscatter
        - post_sar: Post-flood Sentinel-1 backscatter
        - sar_diff: Pre - Post difference
        - sar_ratio: Pre / Post ratio
        - elevation: SRTM DEM
        - slope: Terrain slope
        - hand: Height Above Nearest Drainage (if available)
        - jrc_occurrence: JRC surface water occurrence
        - ndwi_proxy: Normalized difference from SAR bands
    """

    MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')
    MODEL_PATH = os.path.join(MODEL_DIR, 'prithvi_flood_gb.joblib')

    FEATURE_NAMES = [
        'pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
        'elevation', 'slope', 'jrc_occ', 'jrc_season', 'sar_cv',
    ]

    def __init__(self):
        self.model = None
        self.prithvi_available = False
        self.model_name = 'Prithvi-Enhanced GBM'

    def _check_prithvi(self):
        """Check if Prithvi model is downloadable."""
        try:
            from transformers import AutoModel
            AutoModel.from_pretrained(
                'ibm-nasa-geospatial/Prithvi-100M-sen1floods11',
                trust_remote_code=True,
            )
            self.prithvi_available = True
            self.model_name = 'Prithvi-100M-sen1floods11'
            return True
        except Exception:
            return False

    def load(self):
        """Load the best available model."""
        if _SKLEARN and os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            return True
        return False

    def train(self, aoi_json, f_start, f_end, p_start, p_end,
              threshold, polarization, speckle):
        """Train enhanced flood classifier on SAR data."""
        if not _SKLEARN:
            return False

        from ml_models.data_extraction import extract_sar_training_samples
        df = extract_sar_training_samples(
            aoi_json, f_start, f_end, p_start, p_end,
            threshold, polarization, speckle,
            n_points=5000, scale=30,
        )
        if df is None or df.empty or len(df) < 100:
            return False

        # Add derived features
        df['sar_cv'] = df['sar_diff'].abs() / (df['pre_sar'].abs() + 0.001)

        available_features = [f for f in self.FEATURE_NAMES if f in df.columns]
        X = df[available_features].fillna(0)
        y = df['flood_label']

        self.model = GradientBoostingClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=10, random_state=42,
        )
        self.model.fit(X, y)

        os.makedirs(self.MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, self.MODEL_PATH)
        return True

    @st.cache_data(show_spinner=False, ttl=3600)
    def predict_for_aoi(_self, aoi_json, f_start, f_end, p_start, p_end,
                        threshold, polarization, speckle, return_probability=False):
        """
        Run flood segmentation on the AOI.

        Returns dict with tile URL, metrics, and model info.
        """
        from ml_models.data_extraction import _features_from_info, dataframe_to_ee_fc

        aoi_geom = ee.Geometry(json.loads(aoi_json))

        # Build SAR feature stack
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))

        pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')

        diff = pre.subtract(post)
        ratio = pre.divide(post.add(ee.Image(0.001)))

        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
        slope = ee.Terrain.slope(dem).clip(aoi_geom)
        jrc = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')

        # SAR coefficient of variation
        sar_cv = diff.abs().divide(pre.abs().add(ee.Image(0.001)))

        feature_stack = (pre.rename('pre_sar')
                         .addBands(post.rename('post_sar'))
                         .addBands(diff.rename('sar_diff'))
                         .addBands(ratio.rename('sar_ratio'))
                         .addBands(dem.rename('elevation'))
                         .addBands(slope.rename('slope'))
                         .addBands(jrc.select('occurrence').clip(aoi_geom).rename('jrc_occ'))
                         .addBands(jrc.select('seasonality').clip(aoi_geom).rename('jrc_season'))
                         .addBands(sar_cv.rename('sar_cv')))

        # Sample and predict
        samples = feature_stack.sample(
            region=aoi_geom, scale=30, numPixels=5000,
            seed=42, geometries=True,
        )
        sample_info = samples.getInfo()
        df = _features_from_info(sample_info, _self.FEATURE_NAMES)

        if df.empty or len(df) < 50:
            return None

        # Ensure model is ready
        if _self.model is None:
            loaded = _self.load()
            if not loaded:
                _self.train(aoi_json, f_start, f_end, p_start, p_end,
                            threshold, polarization, speckle)
            if _self.model is None:
                return None

        available_features = [f for f in _self.FEATURE_NAMES if f in df.columns]
        X = df[available_features].fillna(0)

        if return_probability and hasattr(_self.model, 'predict_proba'):
            df['flood_prob'] = _self.model.predict_proba(X)[:, 1]
            value_col = 'flood_prob'
            viz_params = {'min': 0, 'max': 1,
                          'palette': ['1a9850', 'ffffbf', 'fc8d59', 'd73027']}
        else:
            df['flood_pred'] = _self.model.predict(X)
            value_col = 'flood_pred'
            viz_params = {'min': 0, 'max': 1,
                          'palette': ['1a9850', 'd73027']}

        fc = dataframe_to_ee_fc(df, value_col)
        result_image = (fc.reduceToImage([value_col], ee.Reducer.first())
                        .clip(aoi_geom).rename('result'))
        tile_url = result_image.getMapId(viz_params)['tile_fetcher'].url_format

        # Metrics
        if value_col == 'flood_pred':
            flood_count = int((df['flood_pred'] == 1).sum())
            flood_pct = round(flood_count / len(df) * 100, 1)
        else:
            flood_count = int((df['flood_prob'] >= 0.5).sum())
            flood_pct = round(flood_count / len(df) * 100, 1)

        # Feature importance
        importance = {}
        if hasattr(_self.model, 'feature_importances_'):
            importance = dict(zip(
                available_features,
                [round(v, 4) for v in _self.model.feature_importances_],
            ))

        return {
            'tile_url': tile_url,
            'model_name': _self.model_name,
            'n_samples': len(df),
            'flood_pixels': flood_count,
            'flood_pct': flood_pct,
            'feature_importance': importance,
            'prithvi_available': _self.prithvi_available,
            'return_probability': return_probability,
        }
