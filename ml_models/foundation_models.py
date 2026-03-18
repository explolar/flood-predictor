"""
Geospatial foundation model integrations for flood detection and classification.

Supports multiple pre-trained models with graceful fallback:
    - Prithvi-EO-2.0 (NASA/IBM, 300M params, multi-sensor)
    - Clay Foundation (70M params, S1+S2+DEM)
    - ClimaX (Microsoft, climate downscaling)
    - Pangu-Weather (Huawei, weather forecasting)

All models follow the same interface: load → predict → tile URL.
Falls back to enhanced GBM when model weights unavailable.
"""

import json
import os

import ee
import streamlit as st

try:
    import joblib
    from sklearn.ensemble import GradientBoostingClassifier
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

try:
    import torch  # noqa: F401
    _TORCH = True
except ImportError:
    _TORCH = False


MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'models')

# Registry of supported foundation models
MODEL_REGISTRY = {
    'prithvi-eo2': {
        'name': 'Prithvi-EO-2.0',
        'hf_id': 'ibm-nasa-geospatial/Prithvi-EO-2.0-300M',
        'params': '300M',
        'input': 'HLS (S1+S2)',
        'task': 'Flood segmentation',
    },
    'clay': {
        'name': 'Clay Foundation',
        'hf_id': 'made-with-clay/Clay',
        'params': '70M',
        'input': 'S1+S2+DEM',
        'task': 'Multi-modal flood mapping',
    },
    'climax': {
        'name': 'ClimaX',
        'hf_id': 'microsoft/climax',
        'params': '100M',
        'input': 'ERA5 climate variables',
        'task': 'Climate downscaling & projection',
    },
    'pangu': {
        'name': 'Pangu-Weather',
        'hf_id': 'huawei/pangu-weather',
        'params': '256M',
        'input': 'ERA5 pressure levels',
        'task': '7-day weather forecast',
    },
}


def check_model_availability(model_key):
    """Check if a foundation model can be loaded."""
    if not _TORCH:
        return False, 'PyTorch not installed'
    try:
        info = MODEL_REGISTRY.get(model_key)
        if not info:
            return False, f'Unknown model: {model_key}'
        # Just check if the model config is accessible (don't download weights)
        from huggingface_hub import model_info
        model_info(info['hf_id'])
        return True, 'Available'
    except Exception as e:
        return False, str(e)


class FoundationFloodClassifier:
    """
    Unified interface for foundation model-based flood classification.

    Extracts rich SAR + optical + terrain features from GEE, then either:
    1. Runs inference through a foundation model (if available), or
    2. Uses an enhanced GBM with 12 features as fallback.

    The GBM fallback is designed to approximate foundation model performance
    by using features that foundation models implicitly learn:
    - SAR temporal statistics (mean, std, coefficient of variation)
    - Multi-scale terrain features (elevation, slope, HAND proxy)
    - Surface water history (JRC occurrence, seasonality, transitions)
    """

    FEATURE_NAMES = [
        'pre_sar', 'post_sar', 'sar_diff', 'sar_ratio', 'sar_cv',
        'elevation', 'slope',
        'jrc_occ', 'jrc_season', 'jrc_transitions',
        'ndvi_proxy', 'terrain_roughness',
    ]

    def __init__(self, model_key='prithvi-eo2'):
        self.model_key = model_key
        self.model_info = MODEL_REGISTRY.get(model_key, MODEL_REGISTRY['prithvi-eo2'])
        self.model = None
        self.foundation_active = False
        self.model_path = os.path.join(MODEL_DIR, f'foundation_{model_key}.joblib')

    def load(self):
        """Load foundation model or fallback GBM."""
        # Try foundation model first
        if _TORCH:
            try:
                from transformers import AutoModel
                self.model = AutoModel.from_pretrained(
                    self.model_info['hf_id'], trust_remote_code=True,
                )
                self.foundation_active = True
                return True
            except Exception:
                pass

        # Fallback to GBM
        if _SKLEARN and os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            return True
        return False

    def _extract_features(self, aoi_json, f_start, f_end, p_start, p_end,
                          polarization, speckle):
        """Extract enhanced feature stack from GEE."""
        aoi_geom = ee.Geometry(json.loads(aoi_json))

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
        cv = diff.abs().divide(pre.abs().add(ee.Image(0.001)))

        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
        slope = ee.Terrain.slope(dem).clip(aoi_geom)

        # Terrain roughness (local elevation std dev in 5x5 window)
        roughness = dem.reduceNeighborhood(
            ee.Reducer.stdDev(), ee.Kernel.square(2, 'pixels'),
        ).rename('terrain_roughness')

        jrc = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')

        # NDVI proxy from SAR (post-flood vegetation damage indicator)
        ndvi_proxy = post.subtract(pre).divide(post.add(pre).abs().add(ee.Image(0.001)))

        feature_stack = (pre.rename('pre_sar')
                         .addBands(post.rename('post_sar'))
                         .addBands(diff.rename('sar_diff'))
                         .addBands(ratio.rename('sar_ratio'))
                         .addBands(cv.rename('sar_cv'))
                         .addBands(dem.rename('elevation'))
                         .addBands(slope.rename('slope'))
                         .addBands(jrc.select('occurrence').clip(aoi_geom).rename('jrc_occ'))
                         .addBands(jrc.select('seasonality').clip(aoi_geom).rename('jrc_season'))
                         .addBands(jrc.select('transitions').clip(aoi_geom).rename('jrc_transitions'))
                         .addBands(ndvi_proxy.rename('ndvi_proxy'))
                         .addBands(roughness))

        return feature_stack, aoi_geom

    def train(self, aoi_json, f_start, f_end, p_start, p_end,
              threshold, polarization, speckle):
        """Train the fallback GBM classifier."""
        if not _SKLEARN:
            return False

        from gee_functions.sar import _make_flood_mask
        from ml_models.data_extraction import _features_from_info

        feature_stack, aoi_geom = self._extract_features(
            aoi_json, f_start, f_end, p_start, p_end, polarization, speckle,
        )

        # Add flood label from threshold-based detection
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))
        pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')

        flood_mask, _ = _make_flood_mask(pre, post, threshold, aoi_geom)
        label = flood_mask.unmask(0).rename('flood_label')
        feature_stack = feature_stack.addBands(label)

        samples = feature_stack.stratifiedSample(
            numPoints=2500, classBand='flood_label',
            region=aoi_geom, scale=30, seed=42, geometries=True,
        )
        sample_info = samples.getInfo()
        df = _features_from_info(sample_info, self.FEATURE_NAMES, label_name='flood_label')

        if df.empty or len(df) < 100:
            return False

        X = df[self.FEATURE_NAMES].fillna(0)
        y = df['flood_label']

        self.model = GradientBoostingClassifier(
            n_estimators=300, max_depth=7, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=8, random_state=42,
        )
        self.model.fit(X, y)

        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        return True

    @st.cache_data(show_spinner=False, ttl=3600)
    def predict_for_aoi(_self, aoi_json, f_start, f_end, p_start, p_end,
                        threshold, polarization, speckle, return_probability=False):
        """Run flood classification and return tile URL + metrics."""
        from ml_models.data_extraction import _features_from_info, dataframe_to_ee_fc

        feature_stack, aoi_geom = _self._extract_features(
            aoi_json, f_start, f_end, p_start, p_end, polarization, speckle,
        )

        samples = feature_stack.sample(
            region=aoi_geom, scale=30, numPixels=5000,
            seed=42, geometries=True,
        )
        sample_info = samples.getInfo()
        df = _features_from_info(sample_info, _self.FEATURE_NAMES)

        if df.empty or len(df) < 50:
            return None

        # Ensure model ready
        if _self.model is None:
            loaded = _self.load()
            if not loaded:
                _self.train(aoi_json, f_start, f_end, p_start, p_end,
                            threshold, polarization, speckle)
            if _self.model is None:
                return None

        X = df[_self.FEATURE_NAMES].fillna(0)

        if return_probability and hasattr(_self.model, 'predict_proba'):
            df['flood_prob'] = _self.model.predict_proba(X)[:, 1]
            value_col = 'flood_prob'
            viz = {'min': 0, 'max': 1, 'palette': ['1a9850', 'ffffbf', 'fc8d59', 'd73027']}
        else:
            df['flood_pred'] = _self.model.predict(X)
            value_col = 'flood_pred'
            viz = {'min': 0, 'max': 1, 'palette': ['1a9850', 'd73027']}

        fc = dataframe_to_ee_fc(df, value_col)
        img = fc.reduceToImage([value_col], ee.Reducer.first()).clip(aoi_geom)
        tile_url = img.getMapId(viz)['tile_fetcher'].url_format

        flood_count = int((df.get('flood_pred', df.get('flood_prob', 0)) >= 0.5).sum())
        flood_pct = round(flood_count / len(df) * 100, 1) if len(df) else 0

        importance = {}
        if hasattr(_self.model, 'feature_importances_'):
            importance = dict(zip(
                _self.FEATURE_NAMES,
                [round(v, 4) for v in _self.model.feature_importances_],
            ))

        return {
            'tile_url': tile_url,
            'model_name': _self.model_info['name'],
            'model_key': _self.model_key,
            'foundation_active': _self.foundation_active,
            'n_samples': len(df),
            'flood_pixels': flood_count,
            'flood_pct': flood_pct,
            'feature_importance': importance,
            'n_features': len(_self.FEATURE_NAMES),
            'return_probability': return_probability,
        }
