"""
NOAA GFS 0.25-degree weather forecast from Google Earth Engine.
Provides 7-16 day precipitation, temperature, and wind forecasts.

GEE Asset: NOAA/GFS0P25
"""

import json
from datetime import datetime, timedelta

import ee
import pandas as pd
import streamlit as st

_GFS_ASSET = 'NOAA/GFS0P25'


@st.cache_data(show_spinner=False, ttl=1800)
def get_gfs_forecast(aoi_json, forecast_hours=168):
    """
    Retrieve GFS weather forecast for the AOI.

    Fetches the latest available GFS run and extracts hourly forecasts
    for precipitation, temperature, humidity, and wind.

    Args:
        aoi_json: Serialized AOI geometry.
        forecast_hours: Forecast horizon in hours (default 168 = 7 days, max 384 = 16 days).

    Returns dict with forecast DataFrame, summary stats, and tile URLs.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # Latest GFS run: filter last 24 hours of initialization times
    now = datetime.utcnow()
    start = (now - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')

    col = (ee.ImageCollection(_GFS_ASSET)
           .filterBounds(aoi_geom)
           .filterDate(start, now.strftime('%Y-%m-%dT%H:%M:%S'))
           .filter(ee.Filter.lte('forecast_hours', forecast_hours))
           .select([
               'total_precipitation_surface',
               'temperature_2m_above_ground',
               'relative_humidity_2m_above_ground',
               'u_component_of_wind_10m_above_ground',
               'v_component_of_wind_10m_above_ground',
           ]))

    count = col.size().getInfo()
    if not count:
        return None

    # Extract time series
    def extract_step(img):
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi_geom,
            scale=25000, maxPixels=1e8,
        )
        fh = img.get('forecast_hours')
        creation = img.get('creation_time')
        return ee.Feature(None, {
            'forecast_hour': fh,
            'creation_time': creation,
            'precip_mm': stats.get('total_precipitation_surface'),
            'temp_k': stats.get('temperature_2m_above_ground'),
            'humidity_pct': stats.get('relative_humidity_2m_above_ground'),
            'wind_u': stats.get('u_component_of_wind_10m_above_ground'),
            'wind_v': stats.get('v_component_of_wind_10m_above_ground'),
        })

    fc = col.map(extract_step).getInfo()
    records = []
    for f in fc.get('features', []):
        p = f['properties']
        if p.get('temp_k') is None:
            continue
        # Wind speed from u,v components
        u = p.get('wind_u', 0) or 0
        v = p.get('wind_v', 0) or 0
        wind_speed = (u ** 2 + v ** 2) ** 0.5
        records.append({
            'forecast_hour': p.get('forecast_hour', 0),
            'precip_mm': round(p.get('precip_mm', 0) or 0, 2),
            'temp_c': round((p.get('temp_k', 273.15) or 273.15) - 273.15, 1),
            'humidity_pct': round(p.get('humidity_pct', 0) or 0, 1),
            'wind_speed_ms': round(wind_speed, 1),
        })

    if not records:
        return None

    df = pd.DataFrame(records).sort_values('forecast_hour').drop_duplicates('forecast_hour')

    # Aggregate daily
    df['day'] = df['forecast_hour'] // 24
    daily = df.groupby('day').agg({
        'precip_mm': 'sum',
        'temp_c': 'mean',
        'humidity_pct': 'mean',
        'wind_speed_ms': 'mean',
    }).round(1).reset_index()
    daily.columns = ['Day', 'Precip (mm)', 'Temp (°C)', 'Humidity (%)', 'Wind (m/s)']

    # Total forecast precipitation tile
    total_precip = col.select('total_precipitation_surface').sum().clip(aoi_geom)
    precip_tile = total_precip.getMapId({
        'min': 0, 'max': 200,
        'palette': ['f7fbff', 'c6dbef', '6baed6', '2171b5', '08306b'],
    })['tile_fetcher'].url_format

    # Latest temperature tile
    latest_temp = (col.select('temperature_2m_above_ground').sort('forecast_hours', False)
                   .first().subtract(273.15).clip(aoi_geom))
    temp_tile = latest_temp.getMapId({
        'min': 10, 'max': 45,
        'palette': ['3288bd', '99d594', 'e6f598', 'fee08b', 'fc8d59', 'd53e4f'],
    })['tile_fetcher'].url_format

    # Summary
    total_precip_mm = round(daily['Precip (mm)'].sum(), 1)
    max_daily_precip = round(daily['Precip (mm)'].max(), 1)
    mean_temp = round(daily['Temp (°C)'].mean(), 1)
    max_wind = round(daily['Wind (m/s)'].max(), 1)

    return {
        'hourly_df': df,
        'daily_df': daily,
        'precip_tile_url': precip_tile,
        'temp_tile_url': temp_tile,
        'total_precip_mm': total_precip_mm,
        'max_daily_precip_mm': max_daily_precip,
        'mean_temp_c': mean_temp,
        'max_wind_ms': max_wind,
        'forecast_hours': forecast_hours,
        'forecast_days': forecast_hours // 24,
        'n_steps': len(df),
    }


@st.cache_data(show_spinner=False, ttl=1800)
def get_gfs_flood_alert(aoi_json, rp_data=None):
    """
    Evaluate flood alert level based on GFS forecast precipitation
    against return period thresholds.

    Args:
        aoi_json: Serialized AOI geometry.
        rp_data: Return period data dict from get_return_period() (optional).

    Returns dict with alert level, forecast summary, and risk assessment.
    """
    forecast = get_gfs_forecast(aoi_json, forecast_hours=168)
    if not forecast:
        return None

    daily = forecast['daily_df']
    total_7day = forecast['total_precip_mm']
    max_daily = forecast['max_daily_precip_mm']

    # Determine alert level
    if rp_data:
        rp_5 = rp_data.get(5, 999999)
        rp_10 = rp_data.get(10, 999999)
        rp_25 = rp_data.get(25, 999999)
        rp_100 = rp_data.get(100, 999999)

        # Compare 7-day total against monsoon return levels (scaled to weekly)
        weekly_factor = 7 / 150  # Rough: monsoon is ~150 days
        if total_7day >= rp_100 * weekly_factor:
            level, color, icon = 'EXTREME', '#7b0051', '🔴'
        elif total_7day >= rp_25 * weekly_factor:
            level, color, icon = 'SEVERE', '#d73027', '🟠'
        elif total_7day >= rp_10 * weekly_factor:
            level, color, icon = 'WARNING', '#fc8d59', '🟡'
        elif total_7day >= rp_5 * weekly_factor:
            level, color, icon = 'WATCH', '#fee08b', '🟢'
        else:
            level, color, icon = 'NORMAL', '#1a9850', '⚪'
    else:
        # Absolute thresholds
        if max_daily > 150:
            level, color, icon = 'EXTREME', '#7b0051', '🔴'
        elif max_daily > 100:
            level, color, icon = 'SEVERE', '#d73027', '🟠'
        elif max_daily > 60:
            level, color, icon = 'WARNING', '#fc8d59', '🟡'
        elif max_daily > 30:
            level, color, icon = 'WATCH', '#fee08b', '🟢'
        else:
            level, color, icon = 'NORMAL', '#1a9850', '⚪'

    # Peak day
    peak_idx = daily['Precip (mm)'].idxmax()
    peak_day = int(daily.loc[peak_idx, 'Day'])

    return {
        'level': level,
        'color': color,
        'icon': icon,
        'total_7day_mm': total_7day,
        'max_daily_mm': max_daily,
        'peak_day': peak_day,
        'mean_temp_c': forecast['mean_temp_c'],
        'daily_df': daily,
    }
