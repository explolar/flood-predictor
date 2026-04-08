"""Optical+SAR fusion for advanced flood detection.

Combines Sentinel-1 SAR flood mask with Sentinel-2 water indices (MNDWI, NDWI)
for improved accuracy where cloud conditions allow.

This is an advanced optional mode — not required for baseline results.
"""

import json

import ee

from utils.cache import cache_data


@cache_data(ttl=3600)
def get_fused_flood_mask(
    aoi_json,
    f_start,
    f_end,
    p_start,
    p_end,
    threshold=3.0,
    polarization="VH",
    speckle=True,
    cloud_thresh=40,
    fusion_weight=0.5,
):
    """Create a fused SAR+optical flood mask.

    Strategy:
    1. Generate SAR flood mask (from sar.py)
    2. Generate optical water mask from S2 MNDWI > 0
    3. Score each pixel: fusion_weight * SAR + (1-fusion_weight) * Optical
    4. Threshold the combined score at 0.5

    Returns dict with fused tile URL, SAR-only URL, optical URL, and stats.
    Returns None if optical data is unavailable (too cloudy).
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # SAR flood mask
    from gee_functions.sar import _build_s1_collection, _make_flood_mask

    s1 = _build_s1_collection(aoi_geom, polarization)
    pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
    post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
    if speckle:
        pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
        post = post.focal_mean(radius=1, kernelType="square", units="pixels")

    sar_flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom)
    # SAR as 0/1 image
    sar_binary = sar_flood.unmask(0).clip(aoi_geom)

    # Optical water mask from Sentinel-2
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi_geom)
        .filterDate(str(f_start), str(f_end))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_thresh))
    )
    s2_count = s2.size().getInfo()
    if s2_count == 0:
        return None  # Too cloudy for optical fusion

    s2_composite = s2.median().clip(aoi_geom)
    # MNDWI = (Green - SWIR1) / (Green + SWIR1)
    mndwi = s2_composite.normalizedDifference(["B3", "B11"]).rename("mndwi")
    optical_water = mndwi.gt(0).unmask(0)

    # Fusion: weighted combination
    w_sar = ee.Image(float(fusion_weight))
    w_opt = ee.Image(1.0 - fusion_weight)
    fused_score = sar_binary.multiply(w_sar).add(optical_water.multiply(w_opt))
    fused_mask = fused_score.gte(0.5).selfMask()

    # Area computation
    fused_area = (
        fused_mask.multiply(ee.Image.pixelArea())
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=30, maxPixels=1e9)
        .getInfo()
        or {}
    )
    area_val = list(fused_area.values())[0] if fused_area else 0
    fused_ha = round((area_val or 0) / 10000, 2)

    sar_area = (
        sar_binary.multiply(ee.Image.pixelArea())
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=30, maxPixels=1e9)
        .getInfo()
        or {}
    )
    sar_val = list(sar_area.values())[0] if sar_area else 0
    sar_ha = round((sar_val or 0) / 10000, 2)

    return {
        "fused_url": fused_mask.getMapId({"palette": ["00FFFF"]})["tile_fetcher"].url_format,
        "sar_only_url": sar_flood.getMapId({"palette": ["FF6B6B"]})["tile_fetcher"].url_format,
        "optical_url": optical_water.selfMask().getMapId({"palette": ["0077FF"]})["tile_fetcher"].url_format,
        "mndwi_url": mndwi.getMapId({"min": -0.5, "max": 0.5, "palette": ["d73027", "ffffbf", "2166ac"]})[
            "tile_fetcher"
        ].url_format,
        "fused_area_ha": fused_ha,
        "sar_only_area_ha": sar_ha,
        "s2_scenes_used": s2_count,
        "fusion_weight": fusion_weight,
    }
