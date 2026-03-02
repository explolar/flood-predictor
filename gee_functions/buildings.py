"""
Feature 8: Building Damage Assessment.
Cross-references Google Open Buildings with flood depth for damage categorization.
"""

import ee
import json
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_building_damage(aoi_json, f_start, f_end, p_start, p_end,
                         threshold, polarization, speckle):
    """
    Assess building damage by crossing Open Buildings with flood depth.

    Damage categories:
    - 0-0.5m: Minor damage
    - 0.5-1.5m: Moderate damage
    - 1.5-3.0m: Severe damage
    - >3.0m: Destroyed

    Returns dict with counts per category and tile URL.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # Google Open Buildings v3
    buildings = (ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
                 .filterBounds(aoi_geom))

    building_count = buildings.size().getInfo()
    if building_count == 0:
        return None

    # Get flood depth from SAR
    from gee_functions.sar import get_all_sar_data
    sar_data = get_all_sar_data(
        aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
        threshold, polarization, speckle
    )

    # Simple flood depth proxy from backscatter change
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi_geom)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
          .select(polarization))

    pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
    post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
    diff = pre.subtract(post)

    # Map backscatter change to approximate depth (empirical scaling)
    depth = diff.divide(3.0).multiply(2.0).max(0).min(5).rename('depth')

    # Rasterize buildings
    buildings_img = buildings.reduceToImage(
        properties=['area_in_meters'],
        reducer=ee.Reducer.first()
    ).clip(aoi_geom).gt(0).selfMask()

    # Cross with depth
    building_depth = depth.updateMask(buildings_img)

    # Classify damage
    minor = building_depth.lte(0.5).selfMask()
    moderate = building_depth.gt(0.5).And(building_depth.lte(1.5)).selfMask()
    severe = building_depth.gt(1.5).And(building_depth.lte(3.0)).selfMask()
    destroyed = building_depth.gt(3.0).selfMask()

    # Count pixels per category
    damage_img = (ee.Image(0)
                  .where(building_depth.lte(0.5), 1)
                  .where(building_depth.gt(0.5).And(building_depth.lte(1.5)), 2)
                  .where(building_depth.gt(1.5).And(building_depth.lte(3.0)), 3)
                  .where(building_depth.gt(3.0), 4)
                  .updateMask(buildings_img)
                  .clip(aoi_geom))

    tile_url = damage_img.getMapId({
        'min': 1, 'max': 4,
        'palette': ['#fee08b', '#fc8d59', '#d73027', '#67001f']
    })['tile_fetcher'].url_format

    # Aggregate stats
    stats = damage_img.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=aoi_geom, scale=10, maxPixels=1e9
    ).getInfo() or {}

    hist = stats.get('constant', {}) or {}
    damage_counts = {
        'minor': int(hist.get('1', 0)),
        'moderate': int(hist.get('2', 0)),
        'severe': int(hist.get('3', 0)),
        'destroyed': int(hist.get('4', 0)),
    }

    return {
        'total_buildings': building_count,
        'damage_counts': damage_counts,
        'tile_url': tile_url,
        'total_affected': sum(damage_counts.values()),
    }
