"""Hydrology module — watershed delineation, stream network, flow analysis."""

import ee
import json
import logging
import streamlit as st

from ui_components.constants import (
    FLOW_ACC_VIZ, FLOW_DIR_VIZ, STREAM_ORDER_VIZ,
    COND_DEM_VIZ, DRAINAGE_DENSITY_VIZ,
)

logger = logging.getLogger(__name__)


# ── Existing: basin boundary lookup ──────────────────────────

@st.cache_data(show_spinner=False, ttl=7200)
def get_watershed_geojson(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        hydrobasins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8")
        ws = hydrobasins.filterBounds(aoi_geom)
        return ws.geometry().getInfo()
    except Exception:
        return None


# ── Batch hydrology computation ──────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600)
def get_all_hydrology_data(aoi_json, stream_threshold=100):
    """Compute flow accumulation, stream network, flow direction tiles and stats."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))

        flow_acc = ee.Image('WWF/HydroSHEDS/03ACC').select('b1').clip(aoi_geom)
        flow_dir = ee.Image('WWF/HydroSHEDS/03DIR').select('b1').clip(aoi_geom)
        cond_dem = ee.Image('WWF/HydroSHEDS/03CONDEM').select('b1').clip(aoi_geom)

        # Stream network from flow accumulation threshold
        streams = flow_acc.gt(stream_threshold).selfMask()

        # Stream order proxy via log10 binning (Strahler approximation)
        log_acc = flow_acc.max(1).log10()
        order = (ee.Image(0)
                 .where(log_acc.gte(2).And(log_acc.lt(3)), 1)
                 .where(log_acc.gte(3).And(log_acc.lt(4)), 2)
                 .where(log_acc.gte(4).And(log_acc.lt(5)), 3)
                 .where(log_acc.gte(5).And(log_acc.lt(6)), 4)
                 .where(log_acc.gte(6), 5)
                 .updateMask(streams)
                 .rename('stream_order'))

        # Tile URLs
        flow_acc_log = flow_acc.max(1).log10().clip(aoi_geom)
        flow_acc_url = flow_acc_log.getMapId(FLOW_ACC_VIZ)['tile_fetcher'].url_format
        flow_dir_url = flow_dir.getMapId(FLOW_DIR_VIZ)['tile_fetcher'].url_format
        stream_url = order.getMapId(STREAM_ORDER_VIZ)['tile_fetcher'].url_format
        cond_dem_url = cond_dem.getMapId(COND_DEM_VIZ)['tile_fetcher'].url_format

        # Stats
        stats = flow_acc.reduceRegion(
            reducer=ee.Reducer.max().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=aoi_geom, scale=100, bestEffort=True,
        ).getInfo()

        stream_count = streams.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=aoi_geom, scale=90, bestEffort=True,
        ).getInfo()

        dem_stats = cond_dem.reduceRegion(
            reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
            geometry=aoi_geom, scale=100, bestEffort=True,
        ).getInfo()

        pixel_count = stream_count.get('b1', 0) or 0
        stream_length_km = round(pixel_count * 0.09, 1)

        return {
            'flow_acc_url': flow_acc_url,
            'flow_dir_url': flow_dir_url,
            'stream_url': stream_url,
            'cond_dem_url': cond_dem_url,
            'stream_length_km': stream_length_km,
            'max_accumulation': stats.get('b1_max', 0),
            'mean_accumulation': round(stats.get('b1_mean', 0), 1),
            'dem_min': round(dem_stats.get('b1_min', 0), 1),
            'dem_max': round(dem_stats.get('b1_max', 0), 1),
            'dem_mean': round(dem_stats.get('b1_mean', 0), 1),
        }
    except Exception as e:
        logger.warning(f"get_all_hydrology_data failed: {e}")
        return None


# ── Multi-level basin hierarchy ──────────────────────────────

@st.cache_data(show_spinner=False, ttl=7200)
def get_multi_basin_geojson(aoi_json):
    """Return GeoJSON for HydroSHEDS basin levels 6, 8, 10."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        result = {}
        for level in [6, 8, 10]:
            asset = f"WWF/HydroSHEDS/v1/Basins/hybas_{level}"
            fc = ee.FeatureCollection(asset).filterBounds(aoi_geom).limit(50)
            count = fc.size().getInfo()
            geojson = fc.geometry().getInfo() if count > 0 else None
            result[f'hybas_{level}'] = {'geojson': geojson, 'count': count}
        return result
    except Exception as e:
        logger.warning(f"get_multi_basin_geojson failed: {e}")
        return None


# ── Drainage density ─────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600)
def get_drainage_density(aoi_json, stream_threshold=100):
    """Compute spatial drainage density (km/km2) and scalar metric."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        flow_acc = ee.Image('WWF/HydroSHEDS/03ACC').select('b1').clip(aoi_geom)
        streams = flow_acc.gt(stream_threshold).selfMask()

        # Local density: count stream pixels in 1.5 km radius, normalize
        local_density = (streams
                         .reduceNeighborhood(ee.Reducer.sum(), ee.Kernel.circle(1500, 'meters'))
                         .multiply(0.09)
                         .divide(3.14159 * 1.5 * 1.5)
                         .rename('drainage_density'))

        density_url = local_density.getMapId(DRAINAGE_DENSITY_VIZ)['tile_fetcher'].url_format

        # Scalar: total stream length / AOI area
        stream_count = streams.reduceRegion(
            reducer=ee.Reducer.count(), geometry=aoi_geom,
            scale=90, bestEffort=True,
        ).getInfo()
        area_km2 = ee.Number(aoi_geom.area(maxError=1)).divide(1e6).getInfo()

        pixel_count = stream_count.get('b1', 0) or 0
        total_length_km = pixel_count * 0.09
        scalar_density = round(total_length_km / max(area_km2, 0.01), 2)

        return {
            'density_url': density_url,
            'scalar_density': scalar_density,
            'total_length_km': round(total_length_km, 1),
            'area_km2': round(area_km2, 1),
        }
    except Exception as e:
        logger.warning(f"get_drainage_density failed: {e}")
        return None


# ── Basin statistics ─────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600)
def get_basin_statistics(aoi_json):
    """Per-basin stats at hybas_8 level: area, upstream area, mean elevation."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        fc = (ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8")
              .filterBounds(aoi_geom).limit(30))
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation')

        def add_elev(feature):
            mean_elev = dem.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=feature.geometry(),
                scale=100, bestEffort=True,
            ).get('elevation')
            return feature.set('mean_elev', ee.Number(mean_elev).round())

        enriched = fc.map(add_elev)
        features = enriched.getInfo().get('features', [])

        rows = []
        for f in features:
            props = f.get('properties', {})
            rows.append({
                'HYBAS_ID': props.get('HYBAS_ID', ''),
                'Sub-basin Area (km2)': round(props.get('SUB_AREA', 0), 1),
                'Upstream Area (km2)': round(props.get('UP_AREA', 0), 1),
                'Mean Elevation (m)': props.get('mean_elev', 'N/A'),
            })
        return rows
    except Exception as e:
        logger.warning(f"get_basin_statistics failed: {e}")
        return []
