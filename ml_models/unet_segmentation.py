"""
Feature 1: U-Net SAR flood segmentation.
End-to-end pipeline: extracts SAR patches from GEE, runs ONNX inference,
and reconstructs as a GEE tile layer.
"""

import os
import json
import numpy as np
import pandas as pd

try:
    import ee
    _EE = True
except ImportError:
    _EE = False


class UNetFloodSegmenter:
    """U-Net based SAR flood segmentation using ONNX Runtime."""

    MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'unet_flood_mobilenet.onnx')

    def __init__(self):
        self.inference = None
        self.available = os.path.exists(self.MODEL_PATH)

    def _load_model(self):
        if self.inference is not None:
            return
        from ml_models.unet_model import UNetONNXInference
        self.inference = UNetONNXInference(self.MODEL_PATH)

    def _extract_patch_from_gee(self, aoi_json, f_start, f_end, p_start, p_end,
                                 polarization, speckle, patch_size=256, scale=10):
        """
        Extract a SAR image patch from GEE using sampleRectangle.

        Returns numpy array of shape (C, H, W) or None.
        """
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
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)

        stack = post.rename('post').addBands(diff.rename('diff')).addBands(dem.rename('elevation'))

        # Sample rectangle — limited to ~256x256 pixels at given scale
        try:
            sample = stack.sampleRectangle(region=aoi_geom, defaultValue=0)
            arrays = {}
            for band in ['post', 'diff', 'elevation']:
                arr = np.array(sample.get(band).getInfo())
                arrays[band] = arr
        except Exception:
            return None

        # Stack into (C, H, W) format
        channels = np.stack([arrays['post'], arrays['diff'], arrays['elevation']], axis=0)
        return channels.astype(np.float32)

    def segment_for_aoi(self, aoi_json, f_start, f_end, p_start, p_end,
                         polarization='VH', speckle=True, threshold=0.5):
        """
        End-to-end U-Net segmentation pipeline.

        Returns dict with tile_url, flood_area metrics, or None if model unavailable.
        """
        if not self.available:
            return {'error': 'U-Net model not found. Place unet_flood_mobilenet.onnx in models/'}

        self._load_model()

        # Extract patches
        patch = self._extract_patch_from_gee(
            aoi_json, f_start, f_end, p_start, p_end, polarization, speckle
        )
        if patch is None:
            return None

        # Run inference
        proba = self.inference.predict_large_image(patch)
        binary_mask = (proba >= threshold).astype(int)

        flood_pixels = binary_mask.sum()
        total_pixels = binary_mask.size
        flood_fraction = round(flood_pixels / max(total_pixels, 1), 4)

        # Reconstruct as GEE image using sample points
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        aoi_ha = aoi_geom.area(maxError=1).getInfo() / 10000
        flood_area_ha = round(aoi_ha * flood_fraction, 1)

        # Create a GEE visualization from the probability grid
        # Convert to point-based FeatureCollection for tile rendering
        from ml_models.data_extraction import dataframe_to_ee_fc

        H, W = proba.shape
        # Subsample for GEE reconstruction (max ~2000 points)
        step = max(1, int(np.sqrt(H * W / 2000)))
        rows = []
        bbox = json.loads(aoi_json)
        coords = bbox['coordinates'][0]
        min_lon, min_lat = coords[0]
        max_lon, max_lat = coords[2]

        for y in range(0, H, step):
            for x in range(0, W, step):
                lat = min_lat + (max_lat - min_lat) * (1 - y / H)
                lon = min_lon + (max_lon - min_lon) * (x / W)
                rows.append({
                    'latitude': lat, 'longitude': lon,
                    'flood_prob': int(proba[y, x] * 100)
                })

        df = pd.DataFrame(rows)
        fc = dataframe_to_ee_fc(df, 'flood_prob')
        flood_image = (fc.reduceToImage(['flood_prob'], ee.Reducer.first())
                      .clip(aoi_geom).divide(100))

        tile_url = flood_image.getMapId({
            'min': 0, 'max': 1,
            'palette': ['000005', '0d1b2a', '1b4f72', '2e86c1', '00FFFF', 'ffffff']
        })['tile_fetcher'].url_format

        return {
            'tile_url': tile_url,
            'flood_area_ha': flood_area_ha,
            'flood_fraction': flood_fraction,
            'patch_shape': list(patch.shape),
            'model_name': 'U-Net (MobileNetV2)',
        }
