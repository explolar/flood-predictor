"""SAR flood detection with selectable reference strategies and quality metadata."""

import datetime
import json

import ee

from ui_components.constants import DEPTH_VIZ, DIFF_VIZ, SAR_VIZ, SEV_VIZ
from utils.cache import cache_data

# ── Reference strategy helpers ──────────────────────────────────

VALID_STRATEGIES = ("event_pair", "seasonal_baseline", "rolling_baseline", "anomaly_mode")


def _build_s1_collection(aoi_geom, polarization):
    """Return base S1 collection filtered by AOI and polarization."""
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi_geom)
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
        .select(polarization)
    )


def _get_reference_image(s1, aoi_geom, strategy, f_start, f_end, p_start, p_end, speckle, rolling_days=90):
    """Build pre-flood reference and post-flood image based on strategy.

    Returns (pre, post, quality_meta) where quality_meta is a dict with
    scene counts, orbit info, and temporal gap.
    """
    post_col = s1.filterDate(str(f_start), str(f_end))
    n_post = post_col.size().getInfo()
    post = post_col.median().clip(aoi_geom)

    if strategy == "seasonal_baseline":
        # Same month-range across prior 3 years
        f_start_dt = datetime.date.fromisoformat(str(f_start))
        month_start = f_start_dt.month
        month_end = datetime.date.fromisoformat(str(f_end)).month or month_start
        pre_images = ee.ImageCollection([])
        for yr_offset in range(1, 4):
            yr = f_start_dt.year - yr_offset
            start_d = f"{yr}-{month_start:02d}-01"
            end_d = f"{yr}-{month_end:02d}-28"
            pre_images = pre_images.merge(s1.filterDate(start_d, end_d))
        n_pre = pre_images.size().getInfo()
        pre = pre_images.median().clip(aoi_geom)

    elif strategy == "rolling_baseline":
        # Trailing N days before flood start
        f_start_dt = datetime.date.fromisoformat(str(f_start))
        roll_start = (f_start_dt - datetime.timedelta(days=rolling_days)).isoformat()
        roll_end = (f_start_dt - datetime.timedelta(days=1)).isoformat()
        pre_col = s1.filterDate(roll_start, roll_end)
        n_pre = pre_col.size().getInfo()
        pre = pre_col.median().clip(aoi_geom)

    elif strategy == "anomaly_mode":
        # Historical normal: same season over 5 years
        f_start_dt = datetime.date.fromisoformat(str(f_start))
        month = f_start_dt.month
        pre_images = ee.ImageCollection([])
        for yr_offset in range(1, 6):
            yr = f_start_dt.year - yr_offset
            start_d = f"{yr}-{month:02d}-01"
            end_d = f"{yr}-{month:02d}-28"
            pre_images = pre_images.merge(s1.filterDate(start_d, end_d))
        n_pre = pre_images.size().getInfo()
        pre = pre_images.median().clip(aoi_geom)

    else:  # event_pair (default)
        pre_col = s1.filterDate(str(p_start), str(p_end))
        n_pre = pre_col.size().getInfo()
        pre = pre_col.median().clip(aoi_geom)

    if speckle:
        pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
        post = post.focal_mean(radius=1, kernelType="square", units="pixels")

    # Compute quality metadata
    p_start_dt = datetime.date.fromisoformat(str(p_start))
    temporal_gap = (datetime.date.fromisoformat(str(f_start)) - p_start_dt).days

    # Orbit consistency check
    try:
        pre_orbits = set()
        post_orbits = set()
        pre_col_check = s1.filterDate(str(p_start), str(p_end))
        post_col_check = post_col
        for col, orbit_set in [(pre_col_check, pre_orbits), (post_col_check, post_orbits)]:
            info = col.aggregate_array("orbitProperties_pass").getInfo()
            if info:
                orbit_set.update(info)
        orbit_consistent = pre_orbits == post_orbits and len(pre_orbits) > 0
    except Exception:
        orbit_consistent = False

    # Confidence score (0-1)
    scene_score = min(n_pre, 10) / 10 * 0.3 + min(n_post, 5) / 5 * 0.3
    orbit_score = 0.2 if orbit_consistent else 0.0
    gap_score = max(0, 0.2 - temporal_gap / 500)
    confidence = round(min(scene_score + orbit_score + gap_score, 1.0), 2)

    low_data_warning = None
    if n_pre < 3 or n_post < 2:
        low_data_warning = f"Low data: {n_pre} pre-scenes, {n_post} post-scenes. Results may be unreliable."

    quality = {
        "n_pre_scenes": n_pre,
        "n_post_scenes": n_post,
        "orbit_consistency": orbit_consistent,
        "temporal_gap_days": temporal_gap,
        "confidence_score": confidence,
        "low_data_warning": low_data_warning,
        "reference_strategy": strategy,
    }

    return pre, post, quality


# ── Core flood mask ──────────────────────────────────────────


def _make_flood_mask(pre, post, threshold, aoi_geom, dem=None, elev_p40=None):
    """Calibrated flood mask with 6-layer quality filters:
    1. Terrain slope < 8 deg
    2. Permanent water exclusion (JRC seasonality >= 10)
    3. JRC flood frequency gate (occurrence >= 5%)
    4. Elevation <= 40th percentile
    5. Minimum patch >= 56 pixels (~5 ha at 30 m)
    6. Morphological cleanup (focal_mode 40 m circle)
    """
    if dem is None:
        dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
    slope_mask = ee.Terrain.slope(dem).lt(8)
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    perm_water = jrc.select("seasonality").gte(10).clip(aoi_geom)
    jrc_gate = jrc.select("occurrence").gte(5).clip(aoi_geom)

    if elev_p40 is None:
        _info = (
            dem.reduceRegion(reducer=ee.Reducer.percentile([40]), geometry=aoi_geom, scale=100, maxPixels=1e9).getInfo()
            or {}
        )
        elev_p40 = _info.get("elevation_p40") or 9999
    elev_mask = dem.lte(ee.Number(float(elev_p40)))

    diff = pre.subtract(post)
    flooded = (
        diff.gt(threshold)
        .updateMask(slope_mask)
        .where(perm_water, 0)
        .selfMask()
        .updateMask(jrc_gate)
        .updateMask(elev_mask)
    )

    flooded = flooded.updateMask(flooded.connectedPixelCount(200, False).gte(56))
    flood = flooded.focal_mode(40, "circle", "meters").updateMask(flooded)
    return flood, dem


# ── Optional Sentinel-2 optical context ──────────────────────


def _get_optical_context(aoi_geom, f_start, f_end):
    """Try to get a Sentinel-2 true-color composite for context.
    Returns tile_url or None if cloud cover is too high.
    """
    try:
        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi_geom)
            .filterDate(str(f_start), str(f_end))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        )
        count = s2.size().getInfo()
        if count == 0:
            return None
        composite = s2.median().clip(aoi_geom)
        vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000}
        return composite.getMapId(vis)["tile_fetcher"].url_format
    except Exception:
        return None


# ── Main SAR analysis (v2) ───────────────────────────────────


@cache_data(ttl=3600)
def get_all_sar_data(
    aoi_json,
    f_start,
    f_end,
    p_start,
    p_end,
    threshold,
    polarization,
    speckle,
    reference_strategy="event_pair",
    rolling_days=90,
    include_optical=False,
):
    """Compute all SAR layers and stats with selectable reference strategy.

    Extra kwargs (reference_strategy, rolling_days, include_optical) are
    backward-compatible: callers that omit them get the original event_pair behavior.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    s1 = _build_s1_collection(aoi_geom, polarization)

    strategy = reference_strategy if reference_strategy in VALID_STRATEGIES else "event_pair"

    pre, post, quality = _get_reference_image(
        s1,
        aoi_geom,
        strategy,
        f_start,
        f_end,
        p_start,
        p_end,
        speckle,
        rolling_days,
    )

    if not quality["n_pre_scenes"] or not quality["n_post_scenes"]:
        raise ValueError(
            f"Insufficient Sentinel-1 data: {quality['n_pre_scenes']} pre-flood scenes, "
            f"{quality['n_post_scenes']} post-flood scenes. Try expanding the date windows."
        )

    diff = pre.subtract(post)
    flood, dem = _make_flood_mask(pre, post, threshold, aoi_geom)
    water_m = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("seasonality").gte(10).clip(aoi_geom).selfMask()

    # Severity zones
    ep = (
        dem.reduceRegion(reducer=ee.Reducer.percentile([10, 50]), geometry=aoi_geom, scale=100, maxPixels=1e9).getInfo()
        or {}
    )
    p10 = ep.get("elevation_p10", 50) or 50
    p50 = ep.get("elevation_p50", 100) or 100
    sev = flood.where(flood.And(dem.lte(p10)), 3)
    sev = sev.where(flood.And(dem.gt(p10).And(dem.lte(p50))), 2)
    sev = sev.where(flood.And(dem.gt(p50)), 1)
    severity = sev.updateMask(flood)

    # Area
    _area_info = (
        flood.multiply(ee.Image.pixelArea())
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=50, maxPixels=1e9)
        .getInfo()
        or {}
    )
    area_val = list(_area_info.values())[0] if _area_info else 0
    area_ha = round((area_val or 0) / 10000, 2)

    # Population using actual flood mask overlap
    try:
        pop_img = ee.ImageCollection("WorldPop/GP/100m/pop").filter(ee.Filter.eq("year", 2020)).mosaic().clip(aoi_geom)
        pop_val = (
            pop_img.updateMask(flood)
            .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, maxPixels=1e9)
            .get("population")
            .getInfo()
        )
        pop_exposed = int(round(pop_val)) if pop_val else 0
    except Exception:
        pop_exposed = 0

    result = {
        "flood_url": flood.getMapId({"palette": ["00FFFF"]})["tile_fetcher"].url_format,
        "water_url": water_m.getMapId({"palette": ["00008B"]})["tile_fetcher"].url_format,
        "pre_url": pre.getMapId(SAR_VIZ)["tile_fetcher"].url_format,
        "post_url": post.getMapId(SAR_VIZ)["tile_fetcher"].url_format,
        "diff_url": diff.getMapId(DIFF_VIZ)["tile_fetcher"].url_format,
        "severity_url": severity.getMapId(SEV_VIZ)["tile_fetcher"].url_format,
        "area_ha": area_ha,
        "pop_exposed": pop_exposed,
        "quality": quality,
    }

    # Optional optical context
    if include_optical:
        optical_url = _get_optical_context(aoi_geom, f_start, f_end)
        if optical_url:
            result["optical_context_url"] = optical_url

    return result


# ── Monthly SAR tile (unchanged) ─────────────────────────────


@cache_data(ttl=3600)
def get_month_sar_tile(aoi_json, year, month_num, polarization, threshold, speckle):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = _build_s1_collection(aoi_geom, polarization)
        pre = s1.filterDate(f"{year}-01-01", f"{year}-03-31").median().clip(aoi_geom)
        days_in = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month_num - 1]
        post = s1.filterDate(f"{year}-{month_num:02d}-01", f"{year}-{month_num:02d}-{days_in}").median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
            post = post.focal_mean(radius=1, kernelType="square", units="pixels")
        flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom)
        return flood.getMapId({"palette": ["FF6B6B"]})["tile_fetcher"].url_format
    except Exception:
        return None


# ── Flood depth ──────────────────────────────────────────────


@cache_data(ttl=3600)
def get_flood_depth_tile(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """Estimate water depth per pixel using DEM + flood mask.

    Uses a neighbourhood water-surface approach: for each flooded pixel the
    water level is the maximum DEM elevation among nearby non-flooded pixels
    (i.e. the flood boundary). This avoids the single-value p95 problem that
    returns 0 when the flood mask is thin or flat.
    """
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = _build_s1_collection(aoi_geom, polarization)
        pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
            post = post.focal_mean(radius=1, kernelType="square", units="pixels")
        flood, dem = _make_flood_mask(pre, post, threshold, aoi_geom)

        # Neighbourhood water-surface: take the max DEM of dry pixels within
        # a 500 m radius of each flooded pixel — this represents the local
        # water-surface elevation at the flood boundary.
        dry_dem = dem.updateMask(flood.Not())
        water_surface = dry_dem.focal_max(radius=500, kernelType="circle", units="meters")

        # Depth = local water surface − pixel DEM, clamped to [0, 10]
        depth = water_surface.subtract(dem).updateMask(flood).max(0).min(10).rename("depth")

        depth_stats = (
            depth.reduceRegion(
                reducer=ee.Reducer.mean().combine(ee.Reducer.max(), "", True),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e9,
            ).getInfo()
            or {}
        )

        _hist_info = (
            depth.reduceRegion(
                reducer=ee.Reducer.fixedHistogram(0, 4, 8),
                geometry=aoi_geom,
                scale=100,
                maxPixels=1e9,
            ).getInfo()
            or {}
        )
        hist_raw = _hist_info.get("depth", [])
        hist_labels = ["0-0.5", "0.5-1", "1-1.5", "1.5-2", "2-2.5", "2.5-3", "3-3.5", "3.5-4"]
        hist = {hist_labels[i]: int(row[1]) for i, row in enumerate(hist_raw) if i < len(hist_labels)}

        return {
            "tile_url": depth.getMapId(DEPTH_VIZ)["tile_fetcher"].url_format,
            "mean_depth": round(depth_stats.get("depth_mean", 0) or 0, 2),
            "max_depth": round(depth_stats.get("depth_max", 0) or 0, 2),
            "histogram": hist,
        }
    except Exception:
        return None


# ── Flood recession ──────────────────────────────────────────


@cache_data(ttl=3600)
def get_recession_data(aoi_json, f_end_str, p_start_str, p_end_str, polarization, threshold, speckle):
    """Compute flood extent (ha) at T=0, +12d, +24d, +36d after flood end."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        f_end_dt = datetime.date.fromisoformat(f_end_str)
        s1 = _build_s1_collection(aoi_geom, polarization)
        pre = s1.filterDate(p_start_str, p_end_str).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType="square", units="pixels")
        px_area = ee.Image.pixelArea()

        dem_r = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
        _ep_info = (
            dem_r.reduceRegion(
                reducer=ee.Reducer.percentile([40]), geometry=aoi_geom, scale=100, maxPixels=1e9
            ).getInfo()
            or {}
        )
        elev_p40 = _ep_info.get("elevation_p40") or 9999

        phases = [
            ("Peak (T\u2080)", 0, 12),
            ("+12 days", 12, 24),
            ("+24 days", 24, 36),
            ("+36 days", 36, 48),
        ]
        results = []
        for label, offset_start, offset_end in phases:
            t0 = (f_end_dt + datetime.timedelta(days=offset_start)).isoformat()
            t1 = (f_end_dt + datetime.timedelta(days=offset_end)).isoformat()
            post_col = s1.filterDate(t0, t1)
            if post_col.size().getInfo() == 0:
                results.append({"Phase": label, "Flood Area (ha)": None})
                continue
            post = post_col.median().clip(aoi_geom)
            if speckle:
                post = post.focal_mean(radius=1, kernelType="square", units="pixels")
            flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom, dem=dem_r, elev_p40=elev_p40)
            _r_info = (
                flood.multiply(px_area)
                .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=30, maxPixels=1e9)
                .getInfo()
                or {}
            )
            area_ha = (list(_r_info.values())[0] if _r_info else 0) or 0
            area_ha = area_ha / 10000
            results.append({"Phase": label, "Flood Area (ha)": round(area_ha, 1)})
        return results
    except Exception:
        return None


# ── Crop loss ────────────────────────────────────────────────


@cache_data(ttl=3600)
def get_crop_loss_data(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, crop_type, crop_price):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = _build_s1_collection(aoi_geom, polarization)
        pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)

        flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom)

        worldcover = ee.Image("ESA/WorldCover/v200/2021").select("Map")
        crop_mask = worldcover.eq(40).clip(aoi_geom)
        flooded_crops = flood.updateMask(crop_mask)

        _area_info = (
            flooded_crops.multiply(ee.Image.pixelArea())
            .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=10, maxPixels=1e10)
            .getInfo()
            or {}
        )
        area_m2 = list(_area_info.values())[0] if _area_info and list(_area_info.values()) else 0
        affected_ha = round((area_m2 or 0) / 10000, 2)

        return {
            "affected_ha": affected_ha,
            "estimated_loss_usd": round(affected_ha * crop_price, 2),
            "message": f"{affected_ha} hectares of {crop_type} flooded.",
        }
    except Exception as e:
        return {"affected_ha": 0, "estimated_loss_usd": 0, "message": str(e)}


# ── SAR timeseries ───────────────────────────────────────────


@cache_data(ttl=3600)
def get_sar_timeseries(aoi_json, p_start, f_end, polarization):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = _build_s1_collection(aoi_geom, polarization).filterDate(str(p_start), str(f_end))

        def calculate_mean(image):
            mean_dict = image.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=100, maxPixels=1e9)
            return ee.Feature(None, {"date": image.date().format("YYYY-MM-dd"), "value": mean_dict.get(polarization)})

        timeseries_features = s1.map(calculate_mean).getInfo()

        series = []
        if timeseries_features and "features" in timeseries_features:
            for feat in timeseries_features["features"]:
                props = feat.get("properties", {})
                if props.get("value") is not None:
                    series.append({"date": props["date"], "value": round(props["value"], 2)})

        series = sorted(series, key=lambda x: x["date"])
        return series
    except Exception:
        return []
