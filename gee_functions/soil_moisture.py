"""
Feature 10: Soil Moisture Integration using NASA SMAP.
Provides soil moisture maps and time-series for enhanced flood modeling.
"""

import ee
import json
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_soil_moisture_data(aoi_json, start_date, end_date):
    """
    Get soil moisture time-series from NASA SMAP SPL3SMP_E (9km resolution).

    Returns dict with time-series DataFrame and tile URL for latest image.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    smap = (ee.ImageCollection('NASA/SMAP/SPL3SMP_E/005')
            .filterBounds(aoi_geom)
            .filterDate(start_date, end_date)
            .select('soil_moisture_am'))

    count = smap.size().getInfo()
    if count == 0:
        return None

    # Time-series
    def extract_sm(img):
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom, scale=9000, maxPixels=1e8
        )
        return ee.Feature(None, {
            'date': img.date().format('YYYY-MM-dd'),
            'soil_moisture': stats.get('soil_moisture_am')
        })

    fc = smap.map(extract_sm)
    data = fc.getInfo()

    records = []
    if data and data.get('features'):
        for feat in data['features']:
            props = feat['properties']
            if props.get('soil_moisture') is not None:
                records.append({
                    'date': props['date'],
                    'soil_moisture': round(float(props['soil_moisture']), 4)
                })

    ts_df = None
    if records:
        ts_df = pd.DataFrame(records)
        ts_df['date'] = pd.to_datetime(ts_df['date'])
        ts_df = ts_df.set_index('date').sort_index()

    # Latest image tile
    latest = smap.sort('system:time_start', False).first().clip(aoi_geom)
    tile_url = latest.getMapId({
        'min': 0.0, 'max': 0.5,
        'palette': ['f7fcb1', 'addd8e', '41ab5d', '006837', '004529']
    })['tile_fetcher'].url_format

    # Mean soil moisture
    mean_stats = latest.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi_geom, scale=9000, maxPixels=1e8
    ).getInfo()
    mean_sm = round(mean_stats.get('soil_moisture_am', 0) or 0, 3)

    return {
        'timeseries': ts_df,
        'tile_url': tile_url,
        'mean_soil_moisture': mean_sm,
        'n_observations': count,
    }


def get_smap_tile(aoi_json, target_date=None):
    """Get a single SMAP soil moisture tile for a specific date."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    if target_date:
        smap = (ee.ImageCollection('NASA/SMAP/SPL3SMP_E/005')
                .filterBounds(aoi_geom)
                .filterDate(target_date, ee.Date(target_date).advance(7, 'day'))
                .select('soil_moisture_am'))
    else:
        smap = (ee.ImageCollection('NASA/SMAP/SPL3SMP_E/005')
                .filterBounds(aoi_geom)
                .sort('system:time_start', False)
                .limit(1)
                .select('soil_moisture_am'))

    img = smap.first().clip(aoi_geom)
    return img.getMapId({
        'min': 0.0, 'max': 0.5,
        'palette': ['f7fcb1', 'addd8e', '41ab5d', '006837', '004529']
    })['tile_fetcher'].url_format
