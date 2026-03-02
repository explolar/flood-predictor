"""
Feature 16: Multi-Year Flood Comparison.
Computes flood masks and areas for multiple monsoon seasons.
"""

import ee
import json
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=7200)
def get_multiyear_flood_comparison(aoi_json, years=None, polarization='VH',
                                    threshold=3.0, speckle=True):
    """
    Compute SAR-based flood area for multiple monsoon seasons.

    Compares Aug-Sep flood extent across selected years.

    Returns dict with yearly data and tile URLs per year.
    """
    if years is None:
        years = [2019, 2020, 2021, 2022, 2023, 2024]

    aoi_geom = ee.Geometry(json.loads(aoi_json))

    results = []
    tile_urls = {}

    for year in years:
        # Monsoon window: Aug 1 - Sep 30
        f_start = f'{year}-08-01'
        f_end = f'{year}-09-30'
        # Pre-flood: May 1 - May 31
        p_start = f'{year}-05-01'
        p_end = f'{year}-05-31'

        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))

        pre_col = s1.filterDate(p_start, p_end)
        post_col = s1.filterDate(f_start, f_end)

        pre_count = pre_col.size().getInfo()
        post_count = post_col.size().getInfo()

        if pre_count == 0 or post_count == 0:
            results.append({'year': year, 'flood_area_ha': None, 'pre_scenes': pre_count, 'post_scenes': post_count})
            continue

        pre = pre_col.median().clip(aoi_geom)
        post = post_col.median().clip(aoi_geom)

        if speckle:
            pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')

        diff = pre.subtract(post)
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
        slope = ee.Terrain.slope(dem)
        slope_mask = slope.lt(8)

        flood = diff.gt(threshold).And(slope_mask).selfMask()

        # Area calculation
        flood_area = flood.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi_geom, scale=30, maxPixels=1e9
        ).getInfo()

        area_ha = round(list(flood_area.values())[0] / 10000, 1) if flood_area and list(flood_area.values())[0] else 0

        # Tile URL
        tile_url = flood.getMapId({
            'palette': ['FF6B6B']
        })['tile_fetcher'].url_format

        tile_urls[year] = tile_url
        results.append({
            'year': year,
            'flood_area_ha': area_ha,
            'pre_scenes': pre_count,
            'post_scenes': post_count,
        })

    df = pd.DataFrame(results)

    # Trend analysis
    valid = df.dropna(subset=['flood_area_ha'])
    trend = None
    if len(valid) >= 3:
        areas = valid['flood_area_ha'].values
        if areas[-1] > areas[0] * 1.2:
            trend = 'INCREASING'
        elif areas[-1] < areas[0] * 0.8:
            trend = 'DECREASING'
        else:
            trend = 'STABLE'

    return {
        'data': df,
        'tile_urls': tile_urls,
        'trend': trend,
        'years_analyzed': len(valid),
    }
