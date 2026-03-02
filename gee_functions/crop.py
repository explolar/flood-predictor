import ee
import json
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_crop_loss_data(aoi_json, p_start, p_end, f_start, f_end, crop_price_per_ha, ndvi_threshold=0.10):
    """Quantify crop damage within flooded agricultural pixels."""
    try:
        aoi_geom  = ee.Geometry(json.loads(aoi_json))
        col_pre   = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                     .filterBounds(aoi_geom).filterDate(str(p_start), str(p_end))
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        col_post  = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                     .filterBounds(aoi_geom).filterDate(str(f_start), str(f_end))
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
        if col_pre.size().getInfo() == 0 or col_post.size().getInfo() == 0:
            return None
        ndvi_pre  = col_pre.median().normalizedDifference(['B8','B4']).clip(aoi_geom)
        ndvi_post = col_post.median().normalizedDifference(['B8','B4']).clip(aoi_geom)
        ndvi_diff = ndvi_pre.subtract(ndvi_post)

        crop_mask = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom).eq(40)
        damaged   = ndvi_diff.gt(ndvi_threshold).And(crop_mask)

        px_area = ee.Image.pixelArea()
        _crop_info = crop_mask.multiply(px_area).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=10, maxPixels=1e10
        ).getInfo() or {}
        total_crop_ha = (list(_crop_info.values())[0] if _crop_info else 0) or 0
        total_crop_ha = total_crop_ha / 10000

        _dmg_info = damaged.multiply(px_area).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=10, maxPixels=1e10
        ).getInfo() or {}
        damaged_ha = (list(_dmg_info.values())[0] if _dmg_info else 0) or 0
        damaged_ha = damaged_ha / 10000

        loss = damaged_ha * crop_price_per_ha
        pct  = round(100 * damaged_ha / total_crop_ha, 1) if total_crop_ha > 0 else 0

        ndvi_crop_tile = ndvi_diff.updateMask(crop_mask).getMapId(
            {'min': 0, 'max': 0.5, 'palette': ['1a9850','ffffbf','d73027']}
        )['tile_fetcher'].url_format

        return {
            'tile_url':      ndvi_crop_tile,
            'total_crop_ha': round(total_crop_ha, 1),
            'damaged_ha':    round(damaged_ha, 1),
            'damage_pct':    pct,
            'loss_estimate': int(round(loss)),
        }
    except Exception:
        return None
