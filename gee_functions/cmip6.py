"""
NASA NEX-GDDP-CMIP6 climate projections from Google Earth Engine.
Provides downscaled (~25 km) daily projections of precipitation and temperature
under SSP scenarios (2015-2100) from multiple CMIP6 global climate models.

GEE Asset: NASA/GDDP-CMIP6
"""

import json

import ee
import pandas as pd
import streamlit as st

_CMIP6_ASSET = "NASA/GDDP-CMIP6"

AVAILABLE_MODELS = [
    "ACCESS-CM2",
    "GFDL-ESM4",
    "MRI-ESM2-0",
    "UKESM1-0-LL",
    "IPSL-CM6A-LR",
    "MPI-ESM1-2-HR",
]

AVAILABLE_SCENARIOS = ["ssp245", "ssp585"]

# pr (kg/m2/s) -> mm/day: multiply by 86400
_PR_TO_MM_DAY = 86400


def _get_cmip6_collection(aoi_geom, scenario, model, start_year, end_year):
    """Filtered CMIP6 collection for a given scenario/model/period."""
    return (
        ee.ImageCollection(_CMIP6_ASSET)
        .filterBounds(aoi_geom)
        .filterDate(f"{start_year}-01-01", f"{end_year + 1}-01-01")
        .filter(ee.Filter.eq("model", model))
        .filter(ee.Filter.eq("scenario", scenario))
    )


@st.cache_data(show_spinner=False, ttl=7200)
def get_cmip6_projections(aoi_json, scenario="ssp245", model="ACCESS-CM2", start_year=2030, end_year=2050):
    """
    Mean annual precipitation and temperature projections for a future period.

    Returns dict with mean values, tile URLs for precipitation and temperature,
    and metadata.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    col = _get_cmip6_collection(aoi_geom, scenario, model, start_year, end_year)

    count = col.size().getInfo()
    if not count:
        return None

    # Mean daily precipitation -> mm/year (mean daily rate * 365)
    mean_precip = col.select("pr").mean().multiply(_PR_TO_MM_DAY * 365).clip(aoi_geom).rename("precip")

    # Temperature: K -> C
    mean_tasmax = col.select("tasmax").mean().subtract(273.15).clip(aoi_geom).rename("tasmax")
    mean_tasmin = col.select("tasmin").mean().subtract(273.15).clip(aoi_geom).rename("tasmin")

    stats = (
        ee.Image.cat([mean_precip, mean_tasmax, mean_tasmin])
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=25000, maxPixels=1e8)
        .getInfo()
        or {}
    )

    precip_tile = mean_precip.getMapId(
        {"min": 200, "max": 3000, "palette": ["ffffcc", "a1dab4", "41b6c4", "2c7fb8", "253494"]}
    )["tile_fetcher"].url_format

    temp_tile = mean_tasmax.getMapId(
        {"min": 15, "max": 45, "palette": ["3288bd", "99d594", "e6f598", "fee08b", "fc8d59", "d53e4f"]}
    )["tile_fetcher"].url_format

    return {
        "mean_precip_mm_yr": round(stats.get("precip", 0) or 0, 1),
        "mean_tasmax_c": round(stats.get("tasmax", 0) or 0, 1),
        "mean_tasmin_c": round(stats.get("tasmin", 0) or 0, 1),
        "precip_tile_url": precip_tile,
        "temp_tile_url": temp_tile,
        "scenario": scenario,
        "model": model,
        "period": f"{start_year}-{end_year}",
    }


@st.cache_data(show_spinner=False, ttl=7200)
def get_cmip6_scenario_comparison(aoi_json, model="ACCESS-CM2", periods=None):
    """
    Compare SSP245 vs SSP585 across multiple time periods.

    Returns dict with a comparison DataFrame and model name.
    """
    if periods is None:
        periods = [(2030, 2050), (2050, 2070), (2070, 2100)]

    aoi_geom = ee.Geometry(json.loads(aoi_json))
    rows = []

    for start_yr, end_yr in periods:
        for scenario in AVAILABLE_SCENARIOS:
            col = _get_cmip6_collection(aoi_geom, scenario, model, start_yr, end_yr)
            count = col.size().getInfo()
            if not count:
                continue

            mean_precip = col.select("pr").mean().multiply(_PR_TO_MM_DAY * 365).clip(aoi_geom)
            mean_tasmax = col.select("tasmax").mean().subtract(273.15).clip(aoi_geom)
            mean_tasmin = col.select("tasmin").mean().subtract(273.15).clip(aoi_geom)

            stats = (
                ee.Image.cat(
                    [
                        mean_precip.rename("precip"),
                        mean_tasmax.rename("tasmax"),
                        mean_tasmin.rename("tasmin"),
                    ]
                )
                .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=25000, maxPixels=1e8)
                .getInfo()
                or {}
            )

            rows.append(
                {
                    "period": f"{start_yr}-{end_yr}",
                    "scenario": scenario.upper(),
                    "precip_mm_yr": round(stats.get("precip", 0) or 0, 1),
                    "tasmax_c": round(stats.get("tasmax", 0) or 0, 1),
                    "tasmin_c": round(stats.get("tasmin", 0) or 0, 1),
                }
            )

    if not rows:
        return None

    return {"comparison_df": pd.DataFrame(rows), "model": model}


def get_cmip6_risk_feature_stack(aoi_json, scenario="ssp245", model="ACCESS-CM2", start_year=2030, end_year=2050):
    """
    Build an ee.Image feature stack for future risk prediction.

    Static layers (elevation, slope, LULC, JRC) are kept as-is.
    CHIRPS annual rainfall is replaced with CMIP6 projected precipitation.

    Returns an ee.Image with bands matching FloodRiskPredictor.BASE_FEATURES,
    or None if CMIP6 data is unavailable.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    col = _get_cmip6_collection(aoi_geom, scenario, model, start_year, end_year)
    count = col.size().getInfo()
    if not count:
        return None

    # Static terrain/land layers (same as current risk model)
    dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom).rename("slope")
    lulc = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select("Map").clip(aoi_geom).rename("lulc_class")
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    jrc_occ = jrc.select("occurrence").clip(aoi_geom).rename("jrc_occurrence")
    jrc_max = jrc.select("max_extent").clip(aoi_geom).rename("jrc_max_extent")

    # Future rainfall: CMIP6 projected mean annual precipitation (mm/yr)
    future_precip = col.select("pr").mean().multiply(_PR_TO_MM_DAY * 365).clip(aoi_geom).rename("annual_rainfall")

    return (
        dem.rename("elevation")
        .addBands(slope)
        .addBands(future_precip)
        .addBands(lulc)
        .addBands(jrc_occ)
        .addBands(jrc_max)
    )


@st.cache_data(show_spinner=False, ttl=7200)
def get_cmip6_precip_change(aoi_json, scenario="ssp245", model="ACCESS-CM2", future_start=2040, future_end=2060):
    """
    Percentage change in mean annual precipitation relative to historical baseline (2015-2025).

    Returns dict with baseline/future values, percentage change, and a
    diverging-palette tile URL for the spatial change map.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # Historical baseline from the same model (use 'historical' scenario for <2015,
    # or early SSP period for 2015-2025)
    baseline_col = _get_cmip6_collection(aoi_geom, scenario, model, 2015, 2025)
    future_col = _get_cmip6_collection(aoi_geom, scenario, model, future_start, future_end)

    b_count = baseline_col.size().getInfo()
    f_count = future_col.size().getInfo()
    if not b_count or not f_count:
        return None

    baseline_precip = baseline_col.select("pr").mean().multiply(_PR_TO_MM_DAY * 365).clip(aoi_geom)
    future_precip = future_col.select("pr").mean().multiply(_PR_TO_MM_DAY * 365).clip(aoi_geom)

    # Percentage change: ((future - baseline) / baseline) * 100
    pct_change = (
        future_precip.subtract(baseline_precip).divide(baseline_precip.max(1)).multiply(100).rename("pct_change")
    )

    stats_baseline = (
        baseline_precip.rename("val")
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=25000, maxPixels=1e8)
        .getInfo()
        or {}
    )
    stats_future = (
        future_precip.rename("val")
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=25000, maxPixels=1e8)
        .getInfo()
        or {}
    )
    stats_pct = (
        pct_change.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=25000, maxPixels=1e8).getInfo()
        or {}
    )

    tile_url = pct_change.getMapId(
        {"min": -40, "max": 40, "palette": ["8c510a", "d8b365", "f6e8c3", "f5f5f5", "c7eae5", "5ab4ac", "01665e"]}
    )["tile_fetcher"].url_format

    return {
        "baseline_precip_mm": round(stats_baseline.get("val", 0) or 0, 1),
        "future_precip_mm": round(stats_future.get("val", 0) or 0, 1),
        "pct_change": round(stats_pct.get("pct_change", 0) or 0, 1),
        "change_tile_url": tile_url,
        "scenario": scenario,
        "model": model,
        "baseline_period": "2015-2025",
        "future_period": f"{future_start}-{future_end}",
    }
