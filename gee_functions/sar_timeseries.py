"""
SAR time-series analysis for anomaly detection (Feature 6).
Computes monthly backscatter statistics from Sentinel-1 archive.
"""

import ee
import json
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=7200)
def get_sar_monthly_stats(aoi_json, start_year=2018, end_year=2024, polarization='VH'):
    """
    Compute monthly SAR backscatter statistics for anomaly detection.

    Returns DataFrame with year, month, mean_backscatter, std_backscatter,
    min_backscatter columns.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    records = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            m_start = f'{year}-{month:02d}-01'
            if month == 12:
                m_end = f'{year + 1}-01-01'
            else:
                m_end = f'{year}-{month + 1:02d}-01'

            col = (ee.ImageCollection('COPERNICUS/S1_GRD')
                   .filterBounds(aoi_geom)
                   .filterDate(m_start, m_end)
                   .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
                   .select(polarization))

            count = col.size().getInfo()
            if not count:
                continue

            monthly = col.median().clip(aoi_geom)
            stats = monthly.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', True)
                        .combine(ee.Reducer.min(), '', True),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e8,
            ).getInfo() or {}

            records.append({
                'year': year,
                'month': month,
                'mean_backscatter': round(stats.get(f'{polarization}_mean', 0) or 0, 2),
                'std_backscatter': round(stats.get(f'{polarization}_stdDev', 0) or 0, 2),
                'min_backscatter': round(stats.get(f'{polarization}_min', 0) or 0, 2),
            })

    if not records:
        return None

    return pd.DataFrame(records)
