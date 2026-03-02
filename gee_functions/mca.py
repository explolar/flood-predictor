import ee
import json
import streamlit as st


def calculate_flood_risk(aoi_geom, w_lulc=0.40, w_slope=0.30, w_rain=0.30):
    dem    = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope  = ee.Terrain.slope(dem).clip(aoi_geom)
    slope_r = slope.where(slope.lte(2), 5).where(slope.gt(20), 1)
    lulc   = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom)
    lulc_r = lulc.remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    rain   = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate('2023-01-01','2024-01-01').sum().clip(aoi_geom)
    rain_r = rain.where(rain.lt(1860), 1).where(rain.gte(1950), 5)
    return lulc_r.multiply(w_lulc/100).add(slope_r.multiply(w_slope/100)).add(rain_r.multiply(w_rain/100)).clip(aoi_geom).round()


@st.cache_data(show_spinner=False, ttl=3600)
def get_mca_tile(aoi_json, w_lulc, w_slope, w_rain):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    risk = calculate_flood_risk(aoi_geom, w_lulc, w_slope, w_rain)
    return risk.getMapId({'min':1,'max':5,'palette':['1a9850','91cf60','ffffbf','fc8d59','d73027']})['tile_fetcher'].url_format
