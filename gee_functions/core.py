import ee
import json
import streamlit as st

project_id = 'xward-481405'


@st.cache_resource
def _init_ee_core():
    try:
        from ee import compute_engine
        creds = compute_engine.ComputeEngineCredentials()
        ee.Initialize(creds, project=project_id)
    except Exception:
        ee.Initialize(project=project_id)
    ee.Image('USGS/SRTMGL1_003').getInfo()


def initialize_ee():
    try:
        _init_ee_core()
        st.markdown('<div class="status-pill"><span class="status-dot"></span>GEE SATELLITE LINK · STABLE</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="status-pill-err"><span style="width:7px;height:7px;background:#ff4444;border-radius:50%;box-shadow:0 0 8px #ff4444;display:inline-block;"></span>LINK FAILED · {str(e)[:60]}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=3600)
def get_aoi_stats(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    dem   = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    combined = dem.rename('elev').addBands(slope.rename('slope'))
    stats = combined.reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), '', True),
        geometry=aoi_geom, scale=100, maxPixels=1e9
    ).getInfo()
    area_m2 = aoi_geom.area(maxError=1).getInfo()
    return {
        'elev_min':   round(stats.get('elev_min', 0)),
        'elev_max':   round(stats.get('elev_max', 0)),
        'elev_mean':  round(stats.get('elev_mean', 0)),
        'slope_mean': round(stats.get('slope_mean', 0), 1),
        'area_km2':   round(area_m2 / 1e6, 2)
    }
