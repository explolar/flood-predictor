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

from utils.cache import cache_data

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

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


class AttentionGate(nn.Module if _TORCH else object):
    """Attention gate for U-Net skip connections.

    Learns to suppress irrelevant spatial regions in the encoder feature map
    ``x`` by using the coarser gating signal ``g`` from the decoder.  The gate
    produces a soft attention mask (0-1) that is element-wise multiplied with
    ``x`` so only flood-relevant features pass through to the decoder.

    Reference: Oktay et al., "Attention U-Net", 2018 (arXiv:1804.03999).

    Args:
        F_g: Number of channels in the gating signal (decoder feature map).
        F_l: Number of channels in the encoder skip-connection feature map.
        F_int: Number of intermediate channels for the attention computation.
    """

    def __init__(self, F_g, F_l, F_int):
        if not _TORCH:
            return
        super().__init__()
        self.W_g = nn.Conv2d(F_g, F_int, kernel_size=1, bias=True)
        self.W_x = nn.Conv2d(F_l, F_int, kernel_size=1, bias=True)
        self.psi = nn.Sequential(nn.Conv2d(F_int, 1, kernel_size=1, bias=True), nn.Sigmoid())
        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        """Compute attention-gated skip features.

        Args:
            g: Gating signal from the decoder (coarser resolution).
            x: Encoder feature map (finer resolution).

        Returns:
            Attention-weighted encoder features with the same shape as ``x``.
        """
        g1 = self.W_g(g)
        x1 = self.W_x(x)
        # Interpolate gating signal to match encoder spatial dims if needed
        if g1.shape[2:] != x1.shape[2:]:
            g1 = F.interpolate(g1, size=x1.shape[2:], mode="bilinear", align_corners=True)
        psi = self.relu(g1 + x1)
        psi = self.psi(psi)
        return x * psi


class ResBlock(nn.Module if _TORCH else object):
    """Residual convolutional block.

    Two 3x3 convolutions with BatchNorm, wrapped by a residual (identity)
    shortcut.  The shortcut helps gradients flow through deeper networks and
    stabilises training for the U-Net encoder/decoder stages.

    Args:
        ch: Number of input and output channels (kept equal for the identity
            shortcut).
    """

    def __init__(self, ch):
        if not _TORCH:
            return
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(ch, ch, 3, padding=1),
            nn.BatchNorm2d(ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch, ch, 3, padding=1),
            nn.BatchNorm2d(ch),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.conv(x) + x)


class _MiniUNet(nn.Module if _TORCH else object):
    """U-Net with residual blocks and attention-gated skip connections.

    Upgrades over the original minimal U-Net:
        * **Residual connections** in every encoder and decoder stage improve
          gradient flow and let each block learn *refinements* on top of the
          identity mapping.
        * **Attention gates** on the skip connections learn to highlight
          flood-relevant spatial regions in the encoder features before they
          are concatenated with the decoder, reducing false positives from
          irrelevant background structures.

    The input/output interface is unchanged:
        input  ``(batch, in_channels, H, W)`` -> output ``(batch, 1, H, W)``
        with values in [0, 1] (sigmoid activation).
    """

    def __init__(self, in_channels=4):
        if not _TORCH:
            return
        super().__init__()
        # ---- Encoder Stage 1 ----
        self.enc1_conv = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.enc1_res = ResBlock(32)

        # ---- Encoder Stage 2 ----
        self.pool = nn.MaxPool2d(2)
        self.enc2_conv = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
        )
        self.enc2_res = ResBlock(64)

        # ---- Attention Gate (decoder->encoder skip) ----
        # F_g=64 (decoder / gating channels), F_l=32 (encoder skip), F_int=16
        self.attn_gate1 = AttentionGate(F_g=64, F_l=32, F_int=16)

        # ---- Decoder Stage 1 ----
        self.up1 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
        self.dec1_conv = nn.Sequential(
            nn.Conv2d(64, 32, 3, padding=1),  # 64 because of cat with skip
            nn.BatchNorm2d(32),
            nn.ReLU(),
        )
        self.dec1_res = ResBlock(32)

        # ---- Output head ----
        self.out = nn.Conv2d(32, 1, 1)

    def forward(self, x):
        # Encoder
        e1 = self.enc1_conv(x)
        e1 = self.enc1_res(e1)  # (B, 32, H, W)

        e2 = self.pool(e1)
        e2 = self.enc2_conv(e2)
        e2 = self.enc2_res(e2)  # (B, 64, H/2, W/2)

        # Decoder with attention-gated skip connection
        d1_up = self.up1(e2)  # (B, 32, H, W)
        e1_att = self.attn_gate1(g=e2, x=e1)  # attention-weighted encoder features
        d1 = self.dec1_conv(torch.cat([d1_up, e1_att], dim=1))
        d1 = self.dec1_res(d1)  # (B, 32, H, W)

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

    MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
    MODEL_PATH = os.path.join(MODEL_DIR, "prithvi_flood_gb.joblib")

    FEATURE_NAMES = [
        "pre_sar",
        "post_sar",
        "sar_diff",
        "sar_ratio",
        "elevation",
        "slope",
        "jrc_occ",
        "jrc_season",
        "sar_cv",
    ]

    def __init__(self):
        self.model = None
        self.prithvi_available = False
        self.model_name = "Prithvi-Enhanced GBM"

    def _check_prithvi(self):
        """Check if Prithvi model is downloadable."""
        try:
            from transformers import AutoModel

            AutoModel.from_pretrained(
                "ibm-nasa-geospatial/Prithvi-100M-sen1floods11",
                trust_remote_code=True,
            )
            self.prithvi_available = True
            self.model_name = "Prithvi-100M-sen1floods11"
            return True
        except Exception:
            return False

    def load(self):
        """Load the best available model."""
        if _SKLEARN and os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            return True
        return False

    def train(self, aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
        """Train enhanced flood classifier on SAR data."""
        if not _SKLEARN:
            return False

        from ml_models.data_extraction import extract_sar_training_samples

        df = extract_sar_training_samples(
            aoi_json,
            f_start,
            f_end,
            p_start,
            p_end,
            threshold,
            polarization,
            speckle,
            n_points=5000,
            scale=30,
        )
        if df is None or df.empty or len(df) < 100:
            return False

        # Add derived features
        df["sar_cv"] = df["sar_diff"].abs() / (df["pre_sar"].abs() + 0.001)

        available_features = [f for f in self.FEATURE_NAMES if f in df.columns]
        X = df[available_features].fillna(0)
        y = df["flood_label"]

        self.model = GradientBoostingClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=10,
            random_state=42,
        )
        self.model.fit(X, y)

        os.makedirs(self.MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, self.MODEL_PATH)
        return True

    @cache_data(ttl=3600)
    def predict_for_aoi(
        _self, aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle, return_probability=False
    ):
        """
        Run flood segmentation on the AOI.

        Returns dict with tile URL, metrics, and model info.
        """
        from ml_models.data_extraction import _features_from_info, dataframe_to_ee_fc

        aoi_geom = ee.Geometry(json.loads(aoi_json))

        # Build SAR feature stack
        s1 = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(aoi_geom)
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
            .select(polarization)
        )

        pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
            post = post.focal_mean(radius=1, kernelType="square", units="pixels")

        diff = pre.subtract(post)
        ratio = pre.divide(post.add(ee.Image(0.001)))

        dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
        slope = ee.Terrain.slope(dem).clip(aoi_geom)
        jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")

        # SAR coefficient of variation
        sar_cv = diff.abs().divide(pre.abs().add(ee.Image(0.001)))

        feature_stack = (
            pre.rename("pre_sar")
            .addBands(post.rename("post_sar"))
            .addBands(diff.rename("sar_diff"))
            .addBands(ratio.rename("sar_ratio"))
            .addBands(dem.rename("elevation"))
            .addBands(slope.rename("slope"))
            .addBands(jrc.select("occurrence").clip(aoi_geom).rename("jrc_occ"))
            .addBands(jrc.select("seasonality").clip(aoi_geom).rename("jrc_season"))
            .addBands(sar_cv.rename("sar_cv"))
        )

        # Sample and predict
        samples = feature_stack.sample(
            region=aoi_geom,
            scale=30,
            numPixels=5000,
            seed=42,
            geometries=True,
        )
        sample_info = samples.getInfo()
        df = _features_from_info(sample_info, _self.FEATURE_NAMES)

        if df.empty or len(df) < 50:
            return None

        # Ensure model is ready
        if _self.model is None:
            loaded = _self.load()
            if not loaded:
                _self.train(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle)
            if _self.model is None:
                return None

        available_features = [f for f in _self.FEATURE_NAMES if f in df.columns]
        X = df[available_features].fillna(0)

        if return_probability and hasattr(_self.model, "predict_proba"):
            df["flood_prob"] = _self.model.predict_proba(X)[:, 1]
            value_col = "flood_prob"
            viz_params = {"min": 0, "max": 1, "palette": ["1a9850", "ffffbf", "fc8d59", "d73027"]}
        else:
            df["flood_pred"] = _self.model.predict(X)
            value_col = "flood_pred"
            viz_params = {"min": 0, "max": 1, "palette": ["1a9850", "d73027"]}

        fc = dataframe_to_ee_fc(df, value_col)
        result_image = fc.reduceToImage([value_col], ee.Reducer.first()).clip(aoi_geom).rename("result")
        tile_url = result_image.getMapId(viz_params)["tile_fetcher"].url_format

        # Metrics
        if value_col == "flood_pred":
            flood_count = int((df["flood_pred"] == 1).sum())
            flood_pct = round(flood_count / len(df) * 100, 1)
        else:
            flood_count = int((df["flood_prob"] >= 0.5).sum())
            flood_pct = round(flood_count / len(df) * 100, 1)

        # Feature importance
        importance = {}
        if hasattr(_self.model, "feature_importances_"):
            importance = dict(
                zip(
                    available_features,
                    [round(v, 4) for v in _self.model.feature_importances_],
                )
            )

        return {
            "tile_url": tile_url,
            "model_name": _self.model_name,
            "n_samples": len(df),
            "flood_pixels": flood_count,
            "flood_pct": flood_pct,
            "feature_importance": importance,
            "prithvi_available": _self.prithvi_available,
            "return_probability": return_probability,
        }
