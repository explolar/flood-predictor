import ee
import json
import datetime
import streamlit as st
from ui_components.constants import SAR_VIZ, DIFF_VIZ, SEV_VIZ, DEPTH_VIZ


def _make_flood_mask(pre, post, threshold, aoi_geom, dem=None, elev_p40=None):
    """Calibrated flood mask with 4-layer quality filters applied in sequence:
      1. Terrain slope < 8 deg  — eliminates radar shadow false positives
      2. Permanent water exclusion  — JRC seasonality >= 10 months
      3. JRC flood frequency gate  — historical occurrence >= 5% (filters cropland FP)
      4. Elevation <= 40th percentile  — restricts to AOI lowlands
      5. Minimum patch >= 56 pixels (~5 ha at 30 m)  — removes noise speckle
      6. Morphological cleanup  — focal_mode 40 m circle
    Returns (flood_mask, dem) so callers can reuse the DEM without re-loading it.
    Pass pre-computed dem / elev_p40 to avoid redundant GEE calls inside loops.
    """
    if dem is None:
        dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope_mask = ee.Terrain.slope(dem).lt(8)
    jrc        = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    perm_water = jrc.select('seasonality').gte(10).clip(aoi_geom)
    jrc_gate   = jrc.select('occurrence').gte(5).clip(aoi_geom)

    if elev_p40 is None:
        _info = dem.reduceRegion(
            reducer=ee.Reducer.percentile([40]),
            geometry=aoi_geom, scale=100, maxPixels=1e9
        ).getInfo() or {}
        elev_p40 = _info.get('elevation_p40') or 9999
    elev_mask = dem.lte(ee.Number(float(elev_p40)))

    diff    = pre.subtract(post)
    flooded = (diff.gt(threshold)
               .updateMask(slope_mask)
               .where(perm_water, 0)
               .selfMask()
               .updateMask(jrc_gate)
               .updateMask(elev_mask))

    flooded = flooded.updateMask(flooded.connectedPixelCount(200, False).gte(56))
    flood = flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded)
    return flood, dem


@st.cache_data(show_spinner=False, ttl=3600)
def get_all_sar_data(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """Compute all SAR layers and stats; return serializable dict for caching."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi_geom)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
          .select(polarization))

    pre_col  = s1.filterDate(str(p_start), str(p_end))
    post_col = s1.filterDate(str(f_start), str(f_end))
    n_pre  = pre_col.size().getInfo()
    n_post = post_col.size().getInfo()
    if not n_pre or not n_post:
        raise ValueError(
            f"Insufficient Sentinel-1 data: {n_pre} pre-flood scenes "
            f"({p_start}–{p_end}), {n_post} post-flood scenes "
            f"({f_start}–{f_end}). Try expanding the date windows."
        )

    pre  = pre_col.median().clip(aoi_geom)
    post = post_col.median().clip(aoi_geom)
    if speckle:
        pre  = pre.focal_mean(radius=1, kernelType='square', units='pixels')
        post = post.focal_mean(radius=1, kernelType='square', units='pixels')
    diff = pre.subtract(post)
    flood, dem = _make_flood_mask(pre, post, threshold, aoi_geom)
    water_m = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom).selfMask()

    ep = dem.reduceRegion(reducer=ee.Reducer.percentile([10,50]), geometry=aoi_geom, scale=100, maxPixels=1e9).getInfo() or {}
    p10 = ep.get('elevation_p10', 50) or 50
    p50 = ep.get('elevation_p50', 100) or 100
    sev = flood.where(flood.And(dem.lte(p10)), 3)
    sev = sev.where(flood.And(dem.gt(p10).And(dem.lte(p50))), 2)
    sev = sev.where(flood.And(dem.gt(p50)), 1)
    severity = sev.updateMask(flood)

    _area_info = flood.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=50, maxPixels=1e9
    ).getInfo() or {}
    area_val = list(_area_info.values())[0] if _area_info else 0
    area_ha = round((area_val or 0) / 10000, 2)

    try:
        pop_img = ee.ImageCollection("WorldPop/GP/100m/pop").filter(ee.Filter.eq('year', 2020)).mosaic().clip(aoi_geom)
        pop_val = pop_img.updateMask(flood).reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, maxPixels=1e9).get('population').getInfo()
        pop_exposed = int(round(pop_val)) if pop_val else 0
    except Exception:
        pop_exposed = 0

    return {
        'flood_url':    flood.getMapId({'palette': ['00FFFF']})['tile_fetcher'].url_format,
        'water_url':    water_m.getMapId({'palette': ['00008B']})['tile_fetcher'].url_format,
        'pre_url':      pre.getMapId(SAR_VIZ)['tile_fetcher'].url_format,
        'post_url':     post.getMapId(SAR_VIZ)['tile_fetcher'].url_format,
        'diff_url':     diff.getMapId(DIFF_VIZ)['tile_fetcher'].url_format,
        'severity_url': severity.getMapId(SEV_VIZ)['tile_fetcher'].url_format,
        'area_ha':      area_ha,
        'pop_exposed':  pop_exposed,
    }


@st.cache_data(show_spinner=False, ttl=3600)
def get_month_sar_tile(aoi_json, year, month_num, polarization, threshold, speckle):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))
        pre = s1.filterDate(f'{year}-01-01', f'{year}-03-31').median().clip(aoi_geom)
        days_in = [31,28,31,30,31,30,31,31,30,31,30,31][month_num-1]
        post = s1.filterDate(f'{year}-{month_num:02d}-01', f'{year}-{month_num:02d}-{days_in}').median().clip(aoi_geom)
        if speckle:
            pre  = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')
        flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom)
        return flood.getMapId({'palette': ['FF6B6B']})['tile_fetcher'].url_format
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_flood_depth_tile(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """Estimate water depth per pixel using DEM + flood mask."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))
        pre  = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
        post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
        if speckle:
            pre  = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')
        flood, dem = _make_flood_mask(pre, post, threshold, aoi_geom)
        flood_dem  = dem.updateMask(flood)

        ep = flood_dem.reduceRegion(
            reducer=ee.Reducer.percentile([95]),
            geometry=aoi_geom, scale=30, maxPixels=1e9
        ).getInfo() or {}
        water_surface = ep.get('elevation_p95', 0) or 0

        depth = ee.Image(float(water_surface)).subtract(dem).updateMask(flood).max(ee.Image(0))

        depth_stats = depth.reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.max(), '', True),
            geometry=aoi_geom, scale=30, maxPixels=1e9
        ).getInfo() or {}

        _hist_info = depth.reduceRegion(
            reducer=ee.Reducer.fixedHistogram(0, 4, 8),
            geometry=aoi_geom, scale=30, maxPixels=1e9
        ).getInfo() or {}
        hist_raw = _hist_info.get('constant', [])
        hist_labels = ['0-0.5', '0.5-1', '1-1.5', '1.5-2', '2-2.5', '2.5-3', '3-3.5', '3.5-4']
        hist = {hist_labels[i]: int(row[1]) for i, row in enumerate(hist_raw) if i < len(hist_labels)}

        return {
            'tile_url':   depth.getMapId(DEPTH_VIZ)['tile_fetcher'].url_format,
            'mean_depth': round(depth_stats.get('constant_mean', 0) or 0, 2),
            'max_depth':  round(depth_stats.get('constant_max',  0) or 0, 2),
            'histogram':  hist,
        }
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_recession_data(aoi_json, f_end_str, p_start_str, p_end_str, polarization, threshold, speckle):
    """Compute flood extent (ha) at T=0, +12d, +24d, +36d after flood end using SAR."""
    try:
        aoi_geom   = ee.Geometry(json.loads(aoi_json))
        f_end_dt   = datetime.date.fromisoformat(f_end_str)
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))
        pre = s1.filterDate(p_start_str, p_end_str).median().clip(aoi_geom)
        if speckle:
            pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
        px_area = ee.Image.pixelArea()

        dem_r    = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
        _ep_info = dem_r.reduceRegion(
            reducer=ee.Reducer.percentile([40]),
            geometry=aoi_geom, scale=100, maxPixels=1e9
        ).getInfo() or {}
        elev_p40 = _ep_info.get('elevation_p40') or 9999

        phases = [
            ('Peak (T\u2080)',  0,  12),
            ('+12 days',  12,  24),
            ('+24 days',  24,  36),
            ('+36 days',  36,  48),
        ]
        results = []
        for label, offset_start, offset_end in phases:
            t0 = (f_end_dt + datetime.timedelta(days=offset_start)).isoformat()
            t1 = (f_end_dt + datetime.timedelta(days=offset_end)).isoformat()
            post_col = s1.filterDate(t0, t1)
            if post_col.size().getInfo() == 0:
                results.append({'Phase': label, 'Flood Area (ha)': None})
                continue
            post = post_col.median().clip(aoi_geom)
            if speckle:
                post = post.focal_mean(radius=1, kernelType='square', units='pixels')
            flood, _ = _make_flood_mask(pre, post, threshold, aoi_geom,
                                        dem=dem_r, elev_p40=elev_p40)
            _r_info = flood.multiply(px_area).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=30, maxPixels=1e9
            ).getInfo() or {}
            area_ha = (list(_r_info.values())[0] if _r_info else 0) or 0
            area_ha = area_ha / 10000
            results.append({'Phase': label, 'Flood Area (ha)': round(area_ha, 1)})
        return results
    except Exception:
        return None
