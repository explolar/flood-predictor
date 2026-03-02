"""
Feature 13: Water Quality Assessment.
Uses Sentinel-2 for turbidity (NDTI) and chlorophyll-a proxy mapping.
"""

import ee
import json
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_turbidity_map(aoi_json, start_date, end_date):
    """
    Compute turbidity map using Sentinel-2 NDTI = (Red - Green) / (Red + Green).

    Also computes chlorophyll-a proxy using B5/B4 ratio.

    Returns dict with tile URLs for turbidity and chlorophyll, plus stats.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
          .filterBounds(aoi_geom)
          .filterDate(start_date, end_date)
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
          .select(['B2', 'B3', 'B4', 'B5', 'B8', 'SCL']))

    count = s2.size().getInfo()
    if count == 0:
        return None

    # Cloud masking
    def mask_clouds(img):
        scl = img.select('SCL')
        mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        return img.updateMask(mask)

    s2_clean = s2.map(mask_clouds).median().clip(aoi_geom)

    # NDTI (Normalized Difference Turbidity Index) = (Red - Green) / (Red + Green)
    red = s2_clean.select('B4')
    green = s2_clean.select('B3')
    ndti = red.subtract(green).divide(red.add(green)).rename('ndti')

    # Chlorophyll-a proxy = B5 / B4 (Red Edge / Red)
    b5 = s2_clean.select('B5')
    chl_a = b5.divide(red.add(ee.Image(0.001))).rename('chl_a')

    # Stats
    ndti_stats = ndti.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.minMax(), '', True),
        geometry=aoi_geom, scale=20, maxPixels=1e9
    ).getInfo() or {}

    chl_stats = chl_a.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi_geom, scale=20, maxPixels=1e9
    ).getInfo() or {}

    # Tile URLs
    ndti_tile = ndti.getMapId({
        'min': -0.3, 'max': 0.3,
        'palette': ['2166ac', '67a9cf', 'd1e5f0', 'fddbc7', 'ef8a62', 'b2182b']
    })['tile_fetcher'].url_format

    chl_tile = chl_a.getMapId({
        'min': 0.5, 'max': 2.0,
        'palette': ['f7fcf5', 'c7e9c0', '74c476', '238b45', '00441b']
    })['tile_fetcher'].url_format

    mean_ndti = round(ndti_stats.get('ndti_mean', 0) or 0, 4)
    if mean_ndti > 0.15:
        turbidity_level = 'High'
    elif mean_ndti > 0.05:
        turbidity_level = 'Moderate'
    elif mean_ndti > -0.05:
        turbidity_level = 'Low'
    else:
        turbidity_level = 'Very Low (clear water)'

    return {
        'ndti_tile': ndti_tile,
        'chl_tile': chl_tile,
        'mean_ndti': mean_ndti,
        'turbidity_level': turbidity_level,
        'mean_chl_ratio': round(chl_stats.get('chl_a_mean', 0) or 0, 3),
        'n_scenes': count,
    }
