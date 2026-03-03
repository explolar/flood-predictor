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

    Uses server-side aggregation via ee.ImageCollection.map() to avoid
    per-month .getInfo() round-trips (previously ~144 calls).

    Returns DataFrame with year, month, mean_backscatter, std_backscatter,
    min_backscatter columns.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # Build a list of monthly intervals as ee.Features
    months = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            m_start = f'{year}-{month:02d}-01'
            if month == 12:
                m_end = f'{year + 1}-01-01'
            else:
                m_end = f'{year}-{month + 1:02d}-01'
            months.append(ee.Feature(None, {
                'year': year, 'month': month,
                'm_start': m_start, 'm_end': m_end,
            }))

    month_fc = ee.FeatureCollection(months)

    s1_base = (ee.ImageCollection('COPERNICUS/S1_GRD')
               .filterBounds(aoi_geom)
               .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
               .select(polarization))

    def compute_monthly(feat):
        m_start = feat.get('m_start')
        m_end = feat.get('m_end')
        col = s1_base.filterDate(m_start, m_end)
        count = col.size()
        monthly = col.median().clip(aoi_geom)
        stats = monthly.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), '', True)
                    .combine(ee.Reducer.min(), '', True),
            geometry=aoi_geom,
            scale=100,
            maxPixels=1e8,
        )
        return feat.set({
            'count': count,
            'mean_val': stats.get(f'{polarization}_mean'),
            'std_val': stats.get(f'{polarization}_stdDev'),
            'min_val': stats.get(f'{polarization}_min'),
        })

    results_fc = month_fc.map(compute_monthly)

    # Single .getInfo() call replaces ~144 individual calls
    results_info = results_fc.getInfo()

    records = []
    for feat in results_info.get('features', []):
        props = feat.get('properties', {})
        if not props.get('count'):
            continue
        mean_v = props.get('mean_val')
        std_v = props.get('std_val')
        min_v = props.get('min_val')
        if mean_v is None:
            continue
        records.append({
            'year': props['year'],
            'month': props['month'],
            'mean_backscatter': round(mean_v or 0, 2),
            'std_backscatter': round(std_v or 0, 2),
            'min_backscatter': round(min_v or 0, 2),
        })

    if not records:
        return None

    return pd.DataFrame(records)
