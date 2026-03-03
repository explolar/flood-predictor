"""
Spectral Indices computation from Sentinel-2 SR.
Computes NDVI, NDWI, MNDWI, NDBI, SAVI, EVI, BSI with classification.
"""

import ee
import json
import logging
import streamlit as st

logger = logging.getLogger(__name__)

# ── Registry: single source of truth for all indices ─────────────────────────
INDEX_REGISTRY = {
    "NDVI": {
        "label": "Normalized Difference Vegetation Index",
        "formula": "(B8 − B4) / (B8 + B4)",
        "source": "Sentinel-2 SR (10 m)",
        "min": -0.2, "max": 0.8,
        "palette": ["d73027", "f46d43", "fdae61", "fee08b", "ffffbf",
                     "d9ef8b", "a6d96a", "66bd63", "1a9850"],
        "classes": [
            (-1.0, 0.00, "#4575b4", "Water / Non-Vegetated"),
            (0.00, 0.20, "#d73027", "Barren / Urban"),
            (0.20, 0.40, "#fdae61", "Sparse Vegetation"),
            (0.40, 0.60, "#a6d96a", "Moderate Vegetation"),
            (0.60, 1.00, "#1a9850", "Dense Vegetation"),
        ],
        "info": (
            "NDVI (Tucker, 1979) uses the contrast between NIR reflectance "
            "(high for chlorophyll-rich leaves) and Red reflectance (absorbed "
            "by chlorophyll). Values near 1 indicate dense, healthy vegetation; "
            "values near 0 indicate bare soil; negative values indicate water "
            "or cloud. Classification thresholds follow FAO standard practice."
        ),
    },
    "NDWI": {
        "label": "Normalized Difference Water Index",
        "formula": "(B3 − B8) / (B3 + B8)",
        "source": "Sentinel-2 SR (10 m)",
        "min": -0.5, "max": 0.5,
        "palette": ["d7191c", "fdae61", "ffffbf", "abd9e9", "2c7bb6"],
        "classes": [
            (-1.0, -0.20, "#d7191c", "Non-Water (Dry)"),
            (-0.20, 0.00, "#fdae61", "Non-Water (Moist)"),
            (0.00, 0.20, "#ffffbf", "Potential Wet Area"),
            (0.20, 0.40, "#abd9e9", "Shallow / Turbid Water"),
            (0.40, 1.00, "#2c7bb6", "Open Water"),
        ],
        "info": (
            "NDWI (McFeeters, 1996) uses Green and NIR bands. Positive values "
            "indicate open water surfaces; the NIR band is strongly absorbed by "
            "water, reducing background noise from vegetation. Threshold of 0.0 "
            "is the canonical water/non-water boundary. Values > 0.3 indicate "
            "high-confidence open water."
        ),
    },
    "MNDWI": {
        "label": "Modified Normalized Difference Water Index",
        "formula": "(B3 − B11) / (B3 + B11)",
        "source": "Sentinel-2 SR (20 m resampled)",
        "min": -0.5, "max": 0.7,
        "palette": ["a50026", "d73027", "fdae61", "ffffbf", "74add1", "313695"],
        "classes": [
            (-1.0, -0.30, "#a50026", "Built-Up / Dry"),
            (-0.30, 0.00, "#fdae61", "Non-Water"),
            (0.00, 0.30, "#ffffbf", "Transitional"),
            (0.30, 0.60, "#74add1", "Water (Moderate)"),
            (0.60, 1.00, "#313695", "Open Water (High Conf.)"),
        ],
        "info": (
            "MNDWI (Xu, 2006) replaces NIR with SWIR1 (B11), which suppresses "
            "built-up land noise that affects NDWI. It performs better in urban "
            "areas for delineating water bodies. MNDWI > 0 is the water boundary "
            "used in JRC surface water products."
        ),
    },
    "NDBI": {
        "label": "Normalized Difference Built-Up Index",
        "formula": "(B11 − B8) / (B11 + B8)",
        "source": "Sentinel-2 SR (20 m resampled)",
        "min": -0.5, "max": 0.5,
        "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"],
        "classes": [
            (-1.0, -0.20, "#1a9850", "Dense Vegetation"),
            (-0.20, 0.00, "#91cf60", "Sparse Vegetation / Soil"),
            (0.00, 0.20, "#ffffbf", "Transitional"),
            (0.20, 0.40, "#fc8d59", "Low-Density Built-Up"),
            (0.40, 1.00, "#d73027", "High-Density Built-Up"),
        ],
        "info": (
            "NDBI (Zha et al., 2003) leverages the fact that built-up areas "
            "reflect more SWIR than NIR, while vegetation shows the opposite "
            "pattern. Positive NDBI values indicate impervious surfaces relevant "
            "to urban flood risk assessment."
        ),
    },
    "SAVI": {
        "label": "Soil-Adjusted Vegetation Index",
        "formula": "1.5 × (B8 − B4) / (B8 + B4 + 0.5)",
        "source": "Sentinel-2 SR (10 m)",
        "min": -0.3, "max": 0.8,
        "palette": ["d73027", "f46d43", "fdae61", "d9ef8b", "1a9850"],
        "classes": [
            (-1.0, 0.00, "#d73027", "Bare Soil / Water"),
            (0.00, 0.20, "#f46d43", "Very Sparse Vegetation"),
            (0.20, 0.40, "#fdae61", "Sparse Vegetation"),
            (0.40, 0.60, "#d9ef8b", "Moderate Vegetation"),
            (0.60, 1.00, "#1a9850", "Dense Vegetation"),
        ],
        "info": (
            "SAVI (Huete, 1988) introduces a soil brightness correction factor "
            "L=0.5 to reduce soil background effects that inflate NDVI in arid "
            "or semi-arid areas with sparse cover. Recommended for flood-affected "
            "agricultural regions where soil exposure is high post-flood."
        ),
    },
    "EVI": {
        "label": "Enhanced Vegetation Index",
        "formula": "2.5 × (B8 − B4) / (B8 + 6×B4 − 7.5×B2 + 1)",
        "source": "Sentinel-2 SR (10 m)",
        "min": -0.2, "max": 0.8,
        "palette": ["d73027", "fdae61", "ffffbf", "a6d96a", "1a9850"],
        "classes": [
            (-1.0, 0.00, "#d73027", "Non-Vegetated"),
            (0.00, 0.20, "#fdae61", "Very Low Vegetation"),
            (0.20, 0.40, "#ffffbf", "Low-Moderate Vegetation"),
            (0.40, 0.60, "#a6d96a", "Moderate-High Vegetation"),
            (0.60, 1.00, "#1a9850", "Dense Vegetation"),
        ],
        "info": (
            "EVI (Huete et al., 2002) improves on NDVI by incorporating the Blue "
            "band (B2) for aerosol correction and applying canopy background and "
            "atmospheric resistance adjustments. Less susceptible to saturation "
            "in dense canopy conditions. Coefficients (6, 7.5) are standard "
            "empirical values from Huete et al."
        ),
    },
    "BSI": {
        "label": "Bare Soil Index",
        "formula": "((B11+B4) − (B8+B2)) / ((B11+B4) + (B8+B2))",
        "source": "Sentinel-2 SR (10/20 m mixed)",
        "min": -0.5, "max": 0.5,
        "palette": ["1a9850", "d9ef8b", "ffffbf", "fdae61", "d73027"],
        "classes": [
            (-1.0, -0.20, "#1a9850", "Vegetated"),
            (-0.20, 0.00, "#d9ef8b", "Partial Vegetation Cover"),
            (0.00, 0.20, "#ffffbf", "Transitional"),
            (0.20, 0.40, "#fdae61", "Sparse / Degraded Soil"),
            (0.40, 1.00, "#d73027", "Bare / Eroded Soil"),
        ],
        "info": (
            "BSI (Rikimaru et al., 2002) combines SWIR1, Red, NIR, and Blue "
            "bands to highlight bare, eroded, or degraded soil. High BSI values "
            "indicate soil vulnerability to erosion and runoff, which directly "
            "increases flood peak discharge."
        ),
    },
}


def _compute_index(s2, index_key):
    """Compute a single spectral index from a median S2 composite."""
    b2 = s2.select('B2')
    b3 = s2.select('B3')
    b4 = s2.select('B4')
    b8 = s2.select('B8')
    b11 = s2.select('B11')
    name = index_key.lower()

    if index_key == 'NDVI':
        return s2.normalizedDifference(['B8', 'B4']).rename(name)
    elif index_key == 'NDWI':
        return s2.normalizedDifference(['B3', 'B8']).rename(name)
    elif index_key == 'MNDWI':
        return s2.normalizedDifference(['B3', 'B11']).rename(name)
    elif index_key == 'NDBI':
        return s2.normalizedDifference(['B11', 'B8']).rename(name)
    elif index_key == 'SAVI':
        L = 0.5
        numer = b8.subtract(b4).multiply(1 + L)
        denom = b8.add(b4).add(L)
        return numer.divide(denom).rename(name)
    elif index_key == 'EVI':
        b2f = b2.divide(10000)
        b4f = b4.divide(10000)
        b8f = b8.divide(10000)
        numer = b8f.subtract(b4f).multiply(2.5)
        denom = b8f.add(b4f.multiply(6)).subtract(b2f.multiply(7.5)).add(1)
        return numer.divide(denom).rename(name)
    elif index_key == 'BSI':
        a = b11.add(b4)
        b = b8.add(b2)
        return a.subtract(b).divide(a.add(b)).rename(name)
    else:
        raise ValueError(f'Unknown index: {index_key}')


@st.cache_data(show_spinner=False, ttl=3600)
def get_index_tile(aoi_json, index_key, date_start, date_end, cloud_thresh=60):
    """
    Compute a spectral index and return tile URL, download URL, thumb URL, stats.

    Returns dict or None on failure.
    """
    try:
        aoi_geom = _make_geometry(aoi_json)
        meta = INDEX_REGISTRY[index_key]

        col, n_scenes, col_id = _build_s2_collection(
            aoi_geom, date_start, date_end, cloud_thresh
        )
        if not col:
            return None

        def mask_clouds(img):
            scl = img.select('SCL')
            mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
            return img.updateMask(mask)

        s2 = col.map(mask_clouds).median().clip(aoi_geom)
        index_img = _compute_index(s2, index_key)

        viz = {'min': meta['min'], 'max': meta['max'], 'palette': meta['palette']}

        tile_url = index_img.getMapId(viz)['tile_fetcher'].url_format

        download_url = index_img.getDownloadUrl({
            'scale': 10, 'crs': 'EPSG:4326',
            'format': 'GeoTIFF', 'region': aoi_geom,
        })

        thumb_url = index_img.getThumbUrl({
            'min': meta['min'], 'max': meta['max'],
            'palette': meta['palette'], 'dimensions': 512,
            'region': aoi_geom, 'format': 'png',
        })

        stats = index_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi_geom, scale=30, maxPixels=1e9,
        ).getInfo() or {}
        mean_val = round(stats.get(index_key.lower(), 0) or 0, 4)

        return {
            'tile_url': tile_url,
            'download_url': download_url,
            'thumb_url': thumb_url,
            'mean_value': mean_val,
            'n_scenes': n_scenes,
        }
    except Exception as e:
        logger.warning(f"get_index_tile({index_key}) failed: {e}")
        return None


def _make_geometry(aoi_json):
    """Safely reconstruct an ee.Geometry from serialized AOI JSON.

    Handles the geodesic/evenOdd fields that ee.Geometry.getInfo() adds
    but that ee.Geometry() constructor may misinterpret on round-trip.
    """
    geo = json.loads(aoi_json) if isinstance(aoi_json, str) else aoi_json
    coords = geo.get('coordinates', [])
    geo_type = geo.get('type', 'Polygon')
    geodesic = geo.get('geodesic', True)

    if geo_type == 'Polygon':
        return ee.Geometry.Polygon(coords, proj='EPSG:4326', geodesic=geodesic)
    elif geo_type == 'MultiPolygon':
        return ee.Geometry.MultiPolygon(coords, proj='EPSG:4326', geodesic=geodesic)
    elif geo_type == 'Rectangle':
        return ee.Geometry.Rectangle(coords, proj='EPSG:4326', geodesic=geodesic)
    else:
        return ee.Geometry(geo, opt_proj='EPSG:4326')


def _build_s2_collection(aoi_geom, date_start, date_end, cloud_thresh):
    """Try S2_SR_HARMONIZED first, fall back to S2_SR if no scenes found."""
    _BANDS = ['B2', 'B3', 'B4', 'B8', 'B11', 'SCL']

    for collection_id in ['COPERNICUS/S2_SR_HARMONIZED', 'COPERNICUS/S2_SR']:
        base = (ee.ImageCollection(collection_id)
                .filterBounds(aoi_geom)
                .filterDate(date_start, date_end)
                .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', cloud_thresh)))
        n_scenes = base.size().getInfo()
        if n_scenes:
            logger.info(f"{collection_id}: {n_scenes} scenes found")
            return base.select(_BANDS), n_scenes, collection_id

    return None, 0, None


@st.cache_data(show_spinner=False, ttl=3600)
def get_all_index_tiles(aoi_json, date_start, date_end, cloud_thresh=60):
    """
    Compute ALL 7 indices from a single S2 composite (one GEE collection fetch).
    Returns {index_key: result_dict}.
    Raises ValueError on no scenes (prevents caching empty results).
    """
    aoi_geom = _make_geometry(aoi_json)

    col, n_scenes, col_id = _build_s2_collection(
        aoi_geom, date_start, date_end, cloud_thresh
    )

    if not col:
        raise ValueError(
            f"No Sentinel-2 scenes found with cloud <= {cloud_thresh}% "
            f"for {date_start} to {date_end}. "
            f"Tried S2_SR_HARMONIZED and S2_SR. "
            f"Try increasing cloud cover to 80-100% or expanding the date range."
        )

    def mask_clouds(img):
        scl = img.select('SCL')
        mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        return img.updateMask(mask)

    s2 = col.map(mask_clouds).median().clip(aoi_geom)

    results = {}
    errors = []
    for index_key, meta in INDEX_REGISTRY.items():
        try:
            index_img = _compute_index(s2, index_key)
            viz = {'min': meta['min'], 'max': meta['max'], 'palette': meta['palette']}

            tile_url = index_img.getMapId(viz)['tile_fetcher'].url_format

            download_url = index_img.getDownloadUrl({
                'scale': 10, 'crs': 'EPSG:4326',
                'format': 'GeoTIFF', 'region': aoi_geom,
            })

            thumb_url = index_img.getThumbUrl({
                'min': meta['min'], 'max': meta['max'],
                'palette': meta['palette'], 'dimensions': 512,
                'region': aoi_geom, 'format': 'png',
            })

            stats = index_img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi_geom, scale=30, maxPixels=1e9,
            ).getInfo() or {}
            mean_val = round(stats.get(index_key.lower(), 0) or 0, 4)

            results[index_key] = {
                'tile_url': tile_url,
                'download_url': download_url,
                'thumb_url': thumb_url,
                'mean_value': mean_val,
                'n_scenes': n_scenes,
            }
        except Exception as e:
            logger.warning(f"Index {index_key} failed: {e}")
            errors.append(f"{index_key}: {e}")
            continue

    if not results:
        # Raise so @st.cache_data does NOT cache an empty result
        raise ValueError(
            f"Found {n_scenes} S2 scenes ({col_id}) but all 7 index "
            f"computations failed: {'; '.join(errors[:3])}"
        )

    return results


def diagnose_s2_access(aoi_json, date_start, date_end, cloud_thresh):
    """Step-by-step diagnostic for S2 collection access. Returns list of dicts."""
    steps = []
    try:
        aoi_geom = _make_geometry(aoi_json)
        centroid = aoi_geom.centroid(1).getInfo()['coordinates']
        steps.append({'step': 'Geometry', 'status': 'OK',
                      'detail': f'Centroid: [{centroid[0]:.4f}, {centroid[1]:.4f}]'})
    except Exception as e:
        steps.append({'step': 'Geometry', 'status': 'FAIL', 'detail': str(e)})
        return steps

    for col_id in ['COPERNICUS/S2_SR_HARMONIZED', 'COPERNICUS/S2_SR']:
        try:
            # Date only (no location filter)
            n_date = (ee.ImageCollection(col_id)
                      .filterDate(date_start, date_end)
                      .limit(1).size().getInfo())
            steps.append({'step': f'{col_id.split("/")[-1]} (date only)',
                          'status': 'OK' if n_date else 'EMPTY',
                          'detail': f'{n_date} image(s)'})

            # Date + bounds
            n_bounds = (ee.ImageCollection(col_id)
                        .filterBounds(aoi_geom)
                        .filterDate(date_start, date_end)
                        .size().getInfo())
            steps.append({'step': f'{col_id.split("/")[-1]} (date+AOI)',
                          'status': 'OK' if n_bounds else 'EMPTY',
                          'detail': f'{n_bounds} scene(s)'})

            # Date + bounds + cloud
            n_full = (ee.ImageCollection(col_id)
                      .filterBounds(aoi_geom)
                      .filterDate(date_start, date_end)
                      .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', cloud_thresh))
                      .size().getInfo())
            steps.append({'step': f'{col_id.split("/")[-1]} (date+AOI+cloud≤{cloud_thresh}%)',
                          'status': 'OK' if n_full else 'EMPTY',
                          'detail': f'{n_full} scene(s)'})

            if n_full:
                return steps
        except Exception as e:
            steps.append({'step': col_id, 'status': 'ERROR', 'detail': str(e)})

    return steps
