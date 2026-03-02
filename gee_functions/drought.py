"""
Feature 12: Drought Monitoring Module.
Standardized Precipitation Index (SPI) from CHIRPS + NDVI anomaly from MODIS.
"""

import ee
import json
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_spi_index(aoi_json, target_year=2024, baseline_years=20):
    """
    Compute Standardized Precipitation Index (SPI) for target year.

    SPI = (P - mean) / std, where P is annual rainfall, mean/std from baseline.

    Returns dict with SPI value, category, and tile URL.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    start_baseline = target_year - baseline_years
    chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterBounds(aoi_geom)

    # Baseline annual totals
    baseline_annuals = []
    for yr in range(start_baseline, target_year):
        annual = chirps.filterDate(f'{yr}-01-01', f'{yr + 1}-01-01').sum().rename('rain')
        baseline_annuals.append(annual)

    baseline_stack = ee.ImageCollection(baseline_annuals)
    baseline_mean = baseline_stack.mean().clip(aoi_geom)  # band: 'rain'
    baseline_std = baseline_stack.reduce(ee.Reducer.stdDev()).clip(aoi_geom).rename('rain')

    # Target year rainfall
    target_col = chirps.filterDate(f'{target_year}-01-01', f'{target_year + 1}-01-01')
    target_count = target_col.size().getInfo()
    if not target_count:
        return None
    target_rain = target_col.sum().clip(aoi_geom).rename('rain')

    # SPI = (P - mean) / std
    spi = target_rain.subtract(baseline_mean).divide(baseline_std.max(1)).rename('spi')

    # Mean SPI for AOI
    spi_stats = spi.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=5000, maxPixels=1e8
    ).getInfo() or {}
    mean_spi = round(spi_stats.get('spi', 0) or 0, 2)

    # Categorize
    if mean_spi >= 2.0:
        category = 'Extremely Wet'
    elif mean_spi >= 1.5:
        category = 'Severely Wet'
    elif mean_spi >= 1.0:
        category = 'Moderately Wet'
    elif mean_spi > -1.0:
        category = 'Near Normal'
    elif mean_spi > -1.5:
        category = 'Moderately Dry'
    elif mean_spi > -2.0:
        category = 'Severely Dry'
    else:
        category = 'Extremely Dry'

    tile_url = spi.getMapId({
        'min': -3, 'max': 3,
        'palette': ['67001f', 'd6604d', 'f4a582', 'fddbc7', 'f7f7f7',
                    'd1e5f0', '92c5de', '4393c3', '2166ac']
    })['tile_fetcher'].url_format

    return {
        'spi_value': mean_spi,
        'category': category,
        'tile_url': tile_url,
        'target_year': target_year,
        'baseline_years': baseline_years,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_ndvi_anomaly(aoi_json, target_year=2024, baseline_years=20):
    """
    Compute NDVI anomaly from MODIS compared to 20-year climatology.

    Returns dict with anomaly value, tile URL, and interpretation.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    modis = ee.ImageCollection('MODIS/061/MOD13A2').filterBounds(aoi_geom).select('NDVI')

    start_baseline = target_year - baseline_years

    # Baseline mean NDVI
    baseline = modis.filterDate(f'{start_baseline}-01-01', f'{target_year}-01-01')
    baseline_mean = baseline.mean().clip(aoi_geom).rename('ndvi')

    # Target year NDVI
    target = modis.filterDate(f'{target_year}-01-01', f'{target_year + 1}-01-01')
    target_count = target.size().getInfo()
    if not target_count:
        return None

    target_mean = target.mean().clip(aoi_geom).rename('ndvi')

    # Anomaly (both bands named 'ndvi' so subtract works correctly)
    anomaly = target_mean.subtract(baseline_mean).rename('ndvi_anomaly')

    # Scale factor: MODIS NDVI is scaled by 10000
    anomaly_scaled = anomaly.divide(10000)

    anom_stats = anomaly_scaled.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=1000, maxPixels=1e8
    ).getInfo() or {}
    mean_anomaly = round(anom_stats.get('ndvi_anomaly', 0) or 0, 4)

    if mean_anomaly < -0.1:
        interpretation = 'Significant vegetation stress (drought indicator)'
    elif mean_anomaly < -0.03:
        interpretation = 'Mild vegetation stress'
    elif mean_anomaly < 0.03:
        interpretation = 'Near normal vegetation'
    else:
        interpretation = 'Above-normal vegetation (wet conditions)'

    tile_url = anomaly_scaled.getMapId({
        'min': -0.2, 'max': 0.2,
        'palette': ['8c510a', 'd8b365', 'f6e8c3', 'f5f5f5', 'c7eae5', '5ab4ac', '01665e']
    })['tile_fetcher'].url_format

    return {
        'anomaly_value': mean_anomaly,
        'interpretation': interpretation,
        'tile_url': tile_url,
        'target_year': target_year,
    }
