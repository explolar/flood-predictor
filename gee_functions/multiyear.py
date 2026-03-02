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

    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi_geom)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
          .select(polarization))

    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope_mask = ee.Terrain.slope(dem).lt(8)

    for year in years:
        try:
            f_start = f'{year}-08-01'
            f_end = f'{year}-09-30'
            p_start = f'{year}-05-01'
            p_end = f'{year}-05-31'

            pre_col = s1.filterDate(p_start, p_end)
            post_col = s1.filterDate(f_start, f_end)

            # Single combined getInfo to check both counts
            counts = ee.Dictionary({
                'pre': pre_col.size(), 'post': post_col.size()
            }).getInfo() or {}

            pre_count = counts.get('pre', 0) or 0
            post_count = counts.get('post', 0) or 0

            if pre_count == 0 or post_count == 0:
                results.append({'year': year, 'flood_area_ha': None,
                                'pre_scenes': pre_count, 'post_scenes': post_count})
                continue

            pre = pre_col.median().clip(aoi_geom)
            post = post_col.median().clip(aoi_geom)

            if speckle:
                pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
                post = post.focal_mean(radius=1, kernelType='square', units='pixels')

            flood = pre.subtract(post).gt(threshold).And(slope_mask).selfMask()

            # Area + tile in one pass
            flood_area = flood.multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=aoi_geom, scale=100, maxPixels=1e9
            ).getInfo()

            vals = list(flood_area.values()) if flood_area else []
            area_val = vals[0] if vals and vals[0] else 0
            area_ha = round(area_val / 10000, 1)

            tile_url = flood.getMapId({
                'palette': ['FF6B6B']
            })['tile_fetcher'].url_format

            tile_urls[year] = tile_url
            results.append({
                'year': year, 'flood_area_ha': area_ha,
                'pre_scenes': pre_count, 'post_scenes': post_count,
            })
        except Exception:
            results.append({'year': year, 'flood_area_ha': None,
                            'pre_scenes': 0, 'post_scenes': 0})

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
