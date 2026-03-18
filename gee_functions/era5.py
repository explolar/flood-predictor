"""
ERA5-Land reanalysis data from Google Earth Engine.
Provides historical climate variables: temperature, runoff, evapotranspiration,
multi-depth soil moisture, snowfall/melt, and precipitation at ~11 km resolution.

GEE Asset: ECMWF/ERA5_LAND/DAILY_AGGR (daily aggregates, 1950-present)
"""

import json

import ee
import pandas as pd
import streamlit as st

_ERA5_ASSET = 'ECMWF/ERA5_LAND/DAILY_AGGR'

# Bands relevant to flood modelling
_CLIMATE_BANDS = [
    'temperature_2m',
    'total_precipitation_sum',
    'total_evaporation_sum',
    'surface_runoff_sum',
    'volumetric_soil_water_layer_1',   # 0-7 cm
    'volumetric_soil_water_layer_2',   # 7-28 cm
    'volumetric_soil_water_layer_3',   # 28-100 cm
    'volumetric_soil_water_layer_4',   # 100-289 cm
    'snowfall_sum',
    'snowmelt_sum',
]


@st.cache_data(show_spinner=False, ttl=3600)
def get_era5_climate_summary(aoi_json, year=2023):
    """
    Annual climate summary from ERA5-Land for a given year.

    Returns dict with mean temperature (C), total precipitation/runoff (mm),
    mean soil moisture, and a runoff tile URL.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    col = (ee.ImageCollection(_ERA5_ASSET)
           .filterBounds(aoi_geom)
           .filterDate(f'{year}-01-01', f'{year + 1}-01-01')
           .select(_CLIMATE_BANDS))

    count = col.size().getInfo()
    if not count:
        return None

    # Annual mean temperature (K -> C)
    mean_temp = col.select('temperature_2m').mean().subtract(273.15).clip(aoi_geom)

    # Annual totals (m -> mm)
    total_precip = col.select('total_precipitation_sum').sum().multiply(1000).clip(aoi_geom)
    total_runoff = col.select('surface_runoff_sum').sum().multiply(1000).clip(aoi_geom)
    total_et = col.select('total_evaporation_sum').sum().multiply(-1000).clip(aoi_geom)  # ET is negative in ERA5

    # Mean soil moisture across 4 layers (m3/m3)
    sm_layers = ['volumetric_soil_water_layer_1', 'volumetric_soil_water_layer_2',
                 'volumetric_soil_water_layer_3', 'volumetric_soil_water_layer_4']
    sm_mean = col.select(sm_layers).mean().reduce(ee.Reducer.mean()).clip(aoi_geom)

    # Reduce to scalar stats
    stats = ee.Image.cat([
        mean_temp.rename('temp'),
        total_precip.rename('precip'),
        total_runoff.rename('runoff'),
        total_et.rename('et'),
        sm_mean.rename('sm'),
    ]).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=aoi_geom,
        scale=11000, maxPixels=1e8
    ).getInfo() or {}

    # Runoff tile for map visualisation
    tile_url = total_runoff.rename('runoff').getMapId({
        'min': 0, 'max': 800,
        'palette': ['ffffcc', 'a1dab4', '41b6c4', '2c7fb8', '253494']
    })['tile_fetcher'].url_format

    return {
        'temperature_c': round(stats.get('temp', 0) or 0, 1),
        'total_precip_mm': round(stats.get('precip', 0) or 0, 1),
        'total_runoff_mm': round(stats.get('runoff', 0) or 0, 1),
        'total_et_mm': round(stats.get('et', 0) or 0, 1),
        'mean_soil_moisture': round(stats.get('sm', 0) or 0, 4),
        'tile_url': tile_url,
        'year': year,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_era5_timeseries(aoi_json, start_date, end_date, variable='total_precipitation_sum'):
    """
    Daily time-series for a single ERA5-Land variable.

    Returns dict with a pandas DataFrame ('date' index, variable column) and count.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    col = (ee.ImageCollection(_ERA5_ASSET)
           .filterBounds(aoi_geom)
           .filterDate(str(start_date), str(end_date))
           .select(variable))

    count = col.size().getInfo()
    if not count:
        return None

    def extract(img):
        val = img.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi_geom,
            scale=11000, maxPixels=1e8
        )
        return ee.Feature(None, {
            'date': img.date().format('YYYY-MM-dd'),
            'value': val.get(variable),
        })

    fc = col.map(extract).getInfo()
    records = [
        {'date': f['properties']['date'], 'value': f['properties']['value']}
        for f in fc.get('features', [])
        if f['properties'].get('value') is not None
    ]
    if not records:
        return None

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').set_index('date')
    df.columns = [variable]

    return {'timeseries': df, 'variable': variable, 'n_observations': len(df)}


@st.cache_data(show_spinner=False, ttl=3600)
def get_era5_monsoon_profile(aoi_json, year=2023):
    """
    Monthly monsoon profile (Jun-Oct) for precipitation, runoff,
    soil moisture (shallow), and evapotranspiration.

    Returns dict with a DataFrame of monthly aggregates (values in mm, except SM in m3/m3).
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    rows = []

    for month in range(6, 11):
        start = f'{year}-{month:02d}-01'
        end_m = month + 1 if month < 12 else 1
        end_y = year if month < 12 else year + 1
        end = f'{end_y}-{end_m:02d}-01'

        col = (ee.ImageCollection(_ERA5_ASSET)
               .filterBounds(aoi_geom)
               .filterDate(start, end)
               .select(['total_precipitation_sum', 'surface_runoff_sum',
                        'volumetric_soil_water_layer_1', 'total_evaporation_sum']))

        img_count = col.size().getInfo()
        if not img_count:
            continue

        precip = col.select('total_precipitation_sum').sum().multiply(1000)
        runoff = col.select('surface_runoff_sum').sum().multiply(1000)
        sm = col.select('volumetric_soil_water_layer_1').mean()
        et = col.select('total_evaporation_sum').sum().multiply(-1000)

        stats = ee.Image.cat([
            precip.rename('precip'), runoff.rename('runoff'),
            sm.rename('sm'), et.rename('et')
        ]).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=aoi_geom,
            scale=11000, maxPixels=1e8
        ).getInfo() or {}

        rows.append({
            'month': month,
            'precip_mm': round(stats.get('precip', 0) or 0, 1),
            'runoff_mm': round(stats.get('runoff', 0) or 0, 1),
            'soil_moisture': round(stats.get('sm', 0) or 0, 4),
            'et_mm': round(stats.get('et', 0) or 0, 1),
        })

    if not rows:
        return None

    return {'monthly_data': pd.DataFrame(rows), 'year': year}


def get_era5_features_for_ml(aoi_json, year=2023):
    """
    Return an ee.Image with ERA5-derived bands for ML feature stacking.

    Bands (all annual aggregates):
        era5_annual_precip   - total precipitation (mm)
        era5_annual_runoff   - surface runoff (mm)
        era5_mean_sm_shallow - mean soil moisture 0-7 cm (m3/m3)
        era5_mean_sm_deep    - mean soil moisture 28-100 cm (m3/m3)
        era5_mean_temp       - mean 2 m temperature (C)

    Returns an ee.Image (NOT a dict) for direct .addBands() usage.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    col = (ee.ImageCollection(_ERA5_ASSET)
           .filterBounds(aoi_geom)
           .filterDate(f'{year}-01-01', f'{year + 1}-01-01'))

    precip = col.select('total_precipitation_sum').sum().multiply(1000).rename('era5_annual_precip')
    runoff = col.select('surface_runoff_sum').sum().multiply(1000).rename('era5_annual_runoff')
    sm_shallow = col.select('volumetric_soil_water_layer_1').mean().rename('era5_mean_sm_shallow')
    sm_deep = col.select('volumetric_soil_water_layer_3').mean().rename('era5_mean_sm_deep')
    temp = col.select('temperature_2m').mean().subtract(273.15).rename('era5_mean_temp')

    return (precip
            .addBands(runoff)
            .addBands(sm_shallow)
            .addBands(sm_deep)
            .addBands(temp)
            .clip(aoi_geom))
