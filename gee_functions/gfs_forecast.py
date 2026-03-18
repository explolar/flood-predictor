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

_GFS_ASSET = "NOAA/GFS0P25"

# Bands that exist on ALL GFS forecast images (not the F000 analysis)
_TEMP_BAND = "temperature_2m_above_ground"
_HUMIDITY_BAND = "relative_humidity_2m_above_ground"
_WIND_U_BAND = "u_component_of_wind_10m_above_ground"
_WIND_V_BAND = "v_component_of_wind_10m_above_ground"
_PRECIP_BAND = "precipitation_rate"


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

    # Latest GFS run: look back up to 48 hours to find data
    now = datetime.utcnow()
    start = (now - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%S")

    # Filter: skip F000 (analysis hour has fewer bands), keep forecast hours 1+
    col = (
        ee.ImageCollection(_GFS_ASSET)
        .filterBounds(aoi_geom)
        .filterDate(start, now.strftime("%Y-%m-%dT%H:%M:%S"))
        .filter(ee.Filter.gt("forecast_hours", 0))
        .filter(ee.Filter.lte("forecast_hours", forecast_hours))
    )

    count = col.size().getInfo()
    if not count:
        return None

    # Select only bands we need — do this AFTER filtering to avoid
    # band mismatch errors on images that lack certain bands
    def safe_select(img):
        """Select available bands, fill missing with zero."""
        bands = img.bandNames()
        precip = ee.Algorithms.If(
            bands.contains(_PRECIP_BAND),
            img.select(_PRECIP_BAND),
            ee.Image.constant(0).rename(_PRECIP_BAND),
        )
        temp = ee.Algorithms.If(
            bands.contains(_TEMP_BAND),
            img.select(_TEMP_BAND),
            ee.Image.constant(273.15).rename(_TEMP_BAND),
        )
        humidity = ee.Algorithms.If(
            bands.contains(_HUMIDITY_BAND),
            img.select(_HUMIDITY_BAND),
            ee.Image.constant(0).rename(_HUMIDITY_BAND),
        )
        wind_u = ee.Algorithms.If(
            bands.contains(_WIND_U_BAND),
            img.select(_WIND_U_BAND),
            ee.Image.constant(0).rename(_WIND_U_BAND),
        )
        wind_v = ee.Algorithms.If(
            bands.contains(_WIND_V_BAND),
            img.select(_WIND_V_BAND),
            ee.Image.constant(0).rename(_WIND_V_BAND),
        )
        return (
            ee.Image(precip)
            .addBands(ee.Image(temp))
            .addBands(ee.Image(humidity))
            .addBands(ee.Image(wind_u))
            .addBands(ee.Image(wind_v))
            .copyProperties(img, ["forecast_hours", "creation_time", "system:time_start"])
        )

    col = col.map(safe_select)

    # Extract time series
    def extract_step(img):
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom,
            scale=25000,
            maxPixels=1e8,
            bestEffort=True,
        )
        return ee.Feature(
            None,
            {
                "forecast_hour": img.get("forecast_hours"),
                "precip_rate": stats.get(_PRECIP_BAND),
                "temp_k": stats.get(_TEMP_BAND),
                "humidity_pct": stats.get(_HUMIDITY_BAND),
                "wind_u": stats.get(_WIND_U_BAND),
                "wind_v": stats.get(_WIND_V_BAND),
            },
        )

    fc = col.map(extract_step).getInfo()
    records = []
    for f in fc.get("features", []):
        p = f["properties"]
        if p.get("temp_k") is None:
            continue
        u = p.get("wind_u", 0) or 0
        v = p.get("wind_v", 0) or 0
        wind_speed = (u**2 + v**2) ** 0.5
        records.append(
            {
                "forecast_hour": p.get("forecast_hour", 0),
                "precip_mm": round((p.get("precip_rate", 0) or 0) * 3600, 2),
                "temp_c": round((p.get("temp_k", 273.15) or 273.15) - 273.15, 1),
                "humidity_pct": round(p.get("humidity_pct", 0) or 0, 1),
                "wind_speed_ms": round(wind_speed, 1),
            }
        )

    if not records:
        return None

    df = pd.DataFrame(records).sort_values("forecast_hour").drop_duplicates("forecast_hour")

    # Aggregate daily
    df["day"] = df["forecast_hour"] // 24
    daily = (
        df.groupby("day")
        .agg(
            {
                "precip_mm": "sum",
                "temp_c": "mean",
                "humidity_pct": "mean",
                "wind_speed_ms": "mean",
            }
        )
        .round(1)
        .reset_index()
    )
    daily.columns = ["Day", "Precip (mm)", "Temp (°C)", "Humidity (%)", "Wind (m/s)"]

    # Total forecast precipitation tile
    try:
        total_precip = col.select(_PRECIP_BAND).sum().multiply(3600).clip(aoi_geom)
        precip_tile = total_precip.getMapId(
            {
                "min": 0,
                "max": 200,
                "palette": ["f7fbff", "c6dbef", "6baed6", "2171b5", "08306b"],
            }
        )["tile_fetcher"].url_format
    except Exception:
        precip_tile = None

    # Latest temperature tile
    try:
        latest_temp = col.select(_TEMP_BAND).sort("system:time_start", False).first().subtract(273.15).clip(aoi_geom)
        temp_tile = latest_temp.getMapId(
            {
                "min": 10,
                "max": 45,
                "palette": ["3288bd", "99d594", "e6f598", "fee08b", "fc8d59", "d53e4f"],
            }
        )["tile_fetcher"].url_format
    except Exception:
        temp_tile = None

    # Summary
    total_precip_mm = round(daily["Precip (mm)"].sum(), 1)
    max_daily_precip = round(daily["Precip (mm)"].max(), 1)
    mean_temp = round(daily["Temp (°C)"].mean(), 1)
    max_wind = round(daily["Wind (m/s)"].max(), 1)

    return {
        "hourly_df": df,
        "daily_df": daily,
        "precip_tile_url": precip_tile,
        "temp_tile_url": temp_tile,
        "total_precip_mm": total_precip_mm,
        "max_daily_precip_mm": max_daily_precip,
        "mean_temp_c": mean_temp,
        "max_wind_ms": max_wind,
        "forecast_hours": forecast_hours,
        "forecast_days": forecast_hours // 24,
        "n_steps": len(df),
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

    daily = forecast["daily_df"]
    total_7day = forecast["total_precip_mm"]
    max_daily = forecast["max_daily_precip_mm"]

    # Determine alert level
    if rp_data:
        rp_5 = rp_data.get(5, 999999)
        rp_10 = rp_data.get(10, 999999)
        rp_25 = rp_data.get(25, 999999)
        rp_100 = rp_data.get(100, 999999)

        weekly_factor = 7 / 150
        if total_7day >= rp_100 * weekly_factor:
            level, color, icon = "EXTREME", "#7b0051", "🔴"
        elif total_7day >= rp_25 * weekly_factor:
            level, color, icon = "SEVERE", "#d73027", "🟠"
        elif total_7day >= rp_10 * weekly_factor:
            level, color, icon = "WARNING", "#fc8d59", "🟡"
        elif total_7day >= rp_5 * weekly_factor:
            level, color, icon = "WATCH", "#fee08b", "🟢"
        else:
            level, color, icon = "NORMAL", "#1a9850", "⚪"
    else:
        if max_daily > 150:
            level, color, icon = "EXTREME", "#7b0051", "🔴"
        elif max_daily > 100:
            level, color, icon = "SEVERE", "#d73027", "🟠"
        elif max_daily > 60:
            level, color, icon = "WARNING", "#fc8d59", "🟡"
        elif max_daily > 30:
            level, color, icon = "WATCH", "#fee08b", "🟢"
        else:
            level, color, icon = "NORMAL", "#1a9850", "⚪"

    peak_idx = daily["Precip (mm)"].idxmax()
    peak_day = int(daily.loc[peak_idx, "Day"])

    return {
        "level": level,
        "color": color,
        "icon": icon,
        "total_7day_mm": total_7day,
        "max_daily_mm": max_daily,
        "peak_day": peak_day,
        "mean_temp_c": forecast["mean_temp_c"],
        "daily_df": daily,
    }
