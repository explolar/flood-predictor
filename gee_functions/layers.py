import ee
import json
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_ndvi_tile(aoi_json, p_start, p_end, f_start, f_end):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        col_pre  = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(aoi_geom).filterDate(str(p_start), str(p_end))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        col_post = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(aoi_geom).filterDate(str(f_start), str(f_end))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        if col_pre.size().getInfo() == 0 or col_post.size().getInfo() == 0:
            return None
        ndvi_pre  = col_pre.median().normalizedDifference(['B8','B4']).clip(aoi_geom)
        ndvi_post = col_post.median().normalizedDifference(['B8','B4']).clip(aoi_geom)
        ndvi_diff = ndvi_pre.subtract(ndvi_post)
        return ndvi_diff.getMapId({'min':-0.3,'max':0.5,'palette':['1a9850','ffffbf','d73027']})['tile_fetcher'].url_format
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_jrc_freq_tile(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        freq = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence').clip(aoi_geom)
        return freq.getMapId({'min':0,'max':100,'palette':['ffffff','0000ff']})['tile_fetcher'].url_format
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_s2_rgb_tile(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi_geom).filterDate('2024-01-01','2024-12-31')
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
        if col.size().getInfo() == 0:
            return None
        s2 = col.median().clip(aoi_geom)
        return s2.getMapId({'bands':['B4','B3','B2'],'min':0,'max':3000})['tile_fetcher'].url_format
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_s2_rgb_tiles(aoi_json, pre_start, pre_end, post_start, post_end):
    """Return pre- and post-flood Sentinel-2 true-color tile URLs."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        viz = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.3}
        col_pre  = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(aoi_geom).filterDate(str(pre_start), str(pre_end))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        col_post = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                    .filterBounds(aoi_geom).filterDate(str(post_start), str(post_end))
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        if col_pre.size().getInfo() == 0 or col_post.size().getInfo() == 0:
            return None
        s2_pre  = col_pre.median().clip(aoi_geom)
        s2_post = col_post.median().clip(aoi_geom)
        return {
            'pre_url':  s2_pre.getMapId(viz)['tile_fetcher'].url_format,
            'post_url': s2_post.getMapId(viz)['tile_fetcher'].url_format,
        }
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=7200)
def get_jrc_flood_history(aoi_json):
    """Return dict {year: flood_months} for 1984-2021 using JRC Monthly Water History."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        jrc = ee.ImageCollection("JRC/GSW1_4/MonthlyHistory").filterBounds(aoi_geom)
        years = ee.List.sequence(1984, 2021)

        def year_flood_months(y):
            y = ee.Number(y).int()
            start = ee.Date.fromYMD(y, 1, 1)
            end   = start.advance(1, 'year')
            monthly = jrc.filterDate(start, end)
            has_water = monthly.map(
                lambda img: ee.Feature(None, {
                    'w': img.eq(2).reduceRegion(
                        reducer=ee.Reducer.max(),
                        geometry=aoi_geom, scale=300, maxPixels=1e8
                    ).get('waterClass')
                })
            )
            flood_months = has_water.aggregate_sum('w')
            return ee.Feature(None, {'year': y, 'flood_months': flood_months})

        fc = ee.FeatureCollection(years.map(year_flood_months)).getInfo()
        result = {}
        for feat in fc['features']:
            p = feat['properties']
            result[int(p['year'])] = int(p.get('flood_months') or 0)
        return result
    except Exception:
        return None
