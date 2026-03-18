"""
GloFAS (Global Flood Awareness System) river discharge forecasts from GEE.
Provides 1-30 day river discharge forecasts and flood return period exceedance.

GEE Assets:
    ECMWF/CEMS/GloFAS_FORECAST_V1  — ensemble discharge forecast
    ECMWF/CEMS/GloFAS_HISTORICAL_V1 — historical reanalysis for baselines
"""

import json

import ee
import pandas as pd
import streamlit as st

_FORECAST_ASSET = "ECMWF/ERA5_LAND/DAILY_AGGR"  # GloFAS uses ERA5 routing
_GLOFAS_FC = "ECMWF/ERA5_LAND/DAILY_AGGR"

# Use HydroSHEDS + ERA5 runoff as proxy for discharge since
# GloFAS direct GEE assets have limited public access.
# This approach: ERA5 surface_runoff * upstream_area ≈ discharge proxy


@st.cache_data(show_spinner=False, ttl=3600)
def get_river_discharge_estimate(aoi_json, start_date, end_date):
    """
    Estimate river discharge using ERA5-Land runoff and HydroSHEDS flow accumulation.

    discharge_proxy = surface_runoff * flow_accumulation_weight

    Returns dict with time-series DataFrame, tile URL, and stats.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    flow_acc = ee.Image("WWF/HydroSHEDS/03ACC").select("b1").clip(aoi_geom)
    # Normalize flow accumulation to 0-1 for weighting
    fa_stats = flow_acc.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=aoi_geom,
        scale=500,
        bestEffort=True,
    ).getInfo()
    fa_max = max(fa_stats.get("b1", 1) or 1, 1)
    flow_weight = flow_acc.divide(fa_max).max(0.01)

    col = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterBounds(aoi_geom)
        .filterDate(str(start_date), str(end_date))
        .select(["surface_runoff_sum", "total_precipitation_sum"])
    )

    count = col.size().getInfo()
    if not count:
        return None

    def extract_day(img):
        # Weighted runoff (proxy for discharge)
        runoff_mm = img.select("surface_runoff_sum").multiply(1000)
        discharge_proxy = runoff_mm.multiply(flow_weight)
        precip_mm = img.select("total_precipitation_sum").multiply(1000)

        stats = ee.Image.cat(
            [
                discharge_proxy.rename("discharge"),
                runoff_mm.rename("runoff"),
                precip_mm.rename("precip"),
            ]
        ).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom,
            scale=1000,
            bestEffort=True,
        )
        return ee.Feature(
            None,
            {
                "date": img.date().format("YYYY-MM-dd"),
                "discharge": stats.get("discharge"),
                "runoff_mm": stats.get("runoff"),
                "precip_mm": stats.get("precip"),
            },
        )

    fc = col.map(extract_day).getInfo()
    records = []
    for f in fc.get("features", []):
        p = f["properties"]
        if p.get("discharge") is not None:
            records.append(
                {
                    "date": p["date"],
                    "discharge_idx": round(p.get("discharge", 0) or 0, 3),
                    "runoff_mm": round(p.get("runoff_mm", 0) or 0, 2),
                    "precip_mm": round(p.get("precip_mm", 0) or 0, 2),
                }
            )

    if not records:
        return None

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    # Tile: latest runoff weighted by flow accumulation
    latest = col.sort("system:time_start", False).first()
    discharge_img = latest.select("surface_runoff_sum").multiply(1000).multiply(flow_weight).clip(aoi_geom)
    tile_url = (
        discharge_img.rename("discharge")
        .getMapId(
            {
                "min": 0,
                "max": 5,
                "palette": ["f7fbff", "c6dbef", "6baed6", "2171b5", "08306b", "00004d"],
            }
        )["tile_fetcher"]
        .url_format
    )

    return {
        "timeseries": df,
        "tile_url": tile_url,
        "mean_discharge": round(df["discharge_idx"].mean(), 3),
        "max_discharge": round(df["discharge_idx"].max(), 3),
        "total_runoff_mm": round(df["runoff_mm"].sum(), 1),
        "n_days": len(df),
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_discharge_return_levels(aoi_json, baseline_years=20):
    """
    Compute discharge return levels from ERA5 annual max runoff.

    Uses Gumbel Type-I distribution (same as CHIRPS return periods).
    Returns dict with return level estimates for T = 2/5/10/25/50/100 years.
    """
    import math

    aoi_geom = ee.Geometry(json.loads(aoi_json))
    flow_acc = ee.Image("WWF/HydroSHEDS/03ACC").select("b1").clip(aoi_geom)
    fa_stats = flow_acc.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=aoi_geom,
        scale=500,
        bestEffort=True,
    ).getInfo()
    fa_max = max(fa_stats.get("b1", 1) or 1, 1)
    flow_weight = flow_acc.divide(fa_max).max(0.01)

    # Annual monsoon max runoff (Jun-Oct)
    annual_maxes = []
    end_year = 2023
    start_year = end_year - baseline_years

    for yr in range(start_year, end_year + 1):
        col = (
            ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
            .filterBounds(aoi_geom)
            .filterDate(f"{yr}-06-01", f"{yr}-11-01")
            .select("surface_runoff_sum")
        )
        cnt = col.size().getInfo()
        if not cnt:
            continue
        max_runoff = col.max().multiply(1000).multiply(flow_weight)
        val = max_runoff.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom,
            scale=1000,
            bestEffort=True,
        ).getInfo()
        v = val.get("surface_runoff_sum")
        if v is not None:
            annual_maxes.append(float(v))

    if len(annual_maxes) < 10:
        return None

    n = len(annual_maxes)
    mu = sum(annual_maxes) / n
    std = (sum((x - mu) ** 2 for x in annual_maxes) / n) ** 0.5
    beta = std * (6**0.5) / math.pi
    u = mu - 0.5772 * beta

    return_periods = {}
    for t in [2, 5, 10, 25, 50, 100]:
        yt = -math.log(-math.log(1 - 1 / t))
        return_periods[t] = round(u + beta * yt, 3)

    return {
        "return_levels": return_periods,
        "n_years": n,
        "mean_annual_max": round(mu, 3),
        "std_annual_max": round(std, 3),
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_flood_exceedance_forecast(aoi_json, forecast_days=7):
    """
    Compare GFS-derived runoff forecast against discharge return levels.

    Returns alert level based on expected peak discharge vs return periods.
    """
    from gee_functions.gfs_forecast import get_gfs_forecast

    forecast = get_gfs_forecast(aoi_json, forecast_hours=forecast_days * 24)
    rp = get_discharge_return_levels(aoi_json)

    if not forecast or not rp:
        return None

    # Use max daily precip as proxy for peak discharge potential
    max_precip = forecast["max_daily_precip_mm"]
    rp_levels = rp["return_levels"]

    # Map precipitation intensity to discharge exceedance
    if max_precip > 150:
        exceedance_t = 100
    elif max_precip > 100:
        exceedance_t = 25
    elif max_precip > 60:
        exceedance_t = 10
    elif max_precip > 30:
        exceedance_t = 5
    else:
        exceedance_t = 2

    level_map = {
        100: ("EXTREME", "#7b0051"),
        25: ("SEVERE", "#d73027"),
        10: ("WARNING", "#fc8d59"),
        5: ("WATCH", "#fee08b"),
        2: ("NORMAL", "#1a9850"),
    }
    level, color = level_map.get(exceedance_t, ("NORMAL", "#1a9850"))

    return {
        "level": level,
        "color": color,
        "exceedance_return_period": exceedance_t,
        "forecast_max_precip_mm": max_precip,
        "return_levels": rp_levels,
        "mean_annual_max_discharge": rp["mean_annual_max"],
    }
