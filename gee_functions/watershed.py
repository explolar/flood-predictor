import ee
import json
import streamlit as st


@st.cache_data(show_spinner=False, ttl=7200)
def get_watershed_geojson(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        hydrobasins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8")
        ws = hydrobasins.filterBounds(aoi_geom)
        return ws.geometry().getInfo()
    except Exception:
        return None
