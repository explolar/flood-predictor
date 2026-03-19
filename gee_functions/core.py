import json
import logging

import ee

from utils.cache import cache_data, cache_resource

logger = logging.getLogger(__name__)

project_id = "xward-481405"


@cache_resource()
def _init_ee_core():
    try:
        from ee import compute_engine

        creds = compute_engine.ComputeEngineCredentials()
        ee.Initialize(creds, project=project_id)
    except Exception:
        ee.Initialize(project=project_id)
    ee.Image("USGS/SRTMGL1_003").getInfo()


def initialize_ee():
    try:
        _init_ee_core()
        logger.info("GEE SATELLITE LINK · STABLE")
    except Exception as e:
        logger.error("GEE LINK FAILED · %s", str(e)[:60])


@cache_data(ttl=3600)
def get_aoi_stats(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    combined = dem.rename("elev").addBands(slope.rename("slope"))
    stats = combined.reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), "", True), geometry=aoi_geom, scale=100, maxPixels=1e9
    ).getInfo()
    area_m2 = aoi_geom.area(maxError=1).getInfo()
    return {
        "elev_min": round(stats.get("elev_min", 0)),
        "elev_max": round(stats.get("elev_max", 0)),
        "elev_mean": round(stats.get("elev_mean", 0)),
        "slope_mean": round(stats.get("slope_mean", 0), 1),
        "area_km2": round(area_m2 / 1e6, 2),
    }
