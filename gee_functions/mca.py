"""
Paper-grade AHP-MCDM Flood Susceptibility Mapping.

Implements a 10-factor Analytic Hierarchy Process (AHP) with:
  - Saaty pairwise comparison matrix & eigenvector weights
  - Consistency Ratio (CR) validation (CR < 0.10)
  - Complete 1-5 reclassification for every factor
  - Individual factor layer export for paper figures

Factors (literature standard):
  1. Distance to River   — HydroSHEDS flow accumulation
  2. Rainfall            — CHIRPS annual precipitation
  3. Slope               — SRTM DEM
  4. Elevation           — SRTM DEM
  5. Drainage Density    — HydroSHEDS stream network
  6. TWI                 — Topographic Wetness Index (SRTM + HydroSHEDS)
  7. LULC                — ESA WorldCover v200
  8. Soil                — OpenLandMap soil texture
  9. NDVI                — MODIS annual composite
 10. Curvature           — DEM second derivative (Laplacian)

References:
  - Saaty, T.L. (1980). The Analytic Hierarchy Process. McGraw-Hill.
  - Tehrany et al. (2014). J. Hydrology, 512, 332-343.
  - Khosravi et al. (2018). Sci. Total Environ., 644, 903-914.
"""

import json
import math

import ee
import numpy as np

from utils.cache import cache_data

# ═══════════════════════════════════════════════════════════════
# AHP Pairwise Comparison Matrix (Saaty 9-point scale)
# ═══════════════════════════════════════════════════════════════

FACTOR_NAMES = [
    "distance_to_river",
    "rainfall",
    "slope",
    "elevation",
    "drainage_density",
    "twi",
    "lulc",
    "soil",
    "ndvi",
    "curvature",
]

FACTOR_LABELS = {
    "distance_to_river": "Distance to River",
    "rainfall": "Rainfall",
    "slope": "Slope",
    "elevation": "Elevation",
    "drainage_density": "Drainage Density",
    "twi": "TWI",
    "lulc": "LULC",
    "soil": "Soil Texture",
    "ndvi": "NDVI",
    "curvature": "Curvature",
}

# Expert-derived pairwise matrix based on literature consensus.
# Row i vs Column j: how much more important is factor i over j?
# Upper triangle only — lower triangle is 1/value.
_AHP_MATRIX = np.array(
    [
        #  dist   rain  slope  elev  drain   twi   lulc  soil  ndvi  curv
        [1, 2, 3, 3, 4, 4, 5, 6, 7, 8],  # dist_river
        [1 / 2, 1, 2, 2, 3, 3, 4, 5, 6, 7],  # rainfall
        [1 / 3, 1 / 2, 1, 1, 2, 2, 3, 4, 5, 6],  # slope
        [1 / 3, 1 / 2, 1, 1, 2, 2, 3, 3, 5, 5],  # elevation
        [1 / 4, 1 / 3, 1 / 2, 1 / 2, 1, 1, 2, 3, 4, 5],  # drain_dens
        [1 / 4, 1 / 3, 1 / 2, 1 / 2, 1, 1, 2, 3, 3, 4],  # twi
        [1 / 5, 1 / 4, 1 / 3, 1 / 3, 1 / 2, 1 / 2, 1, 2, 3, 3],  # lulc
        [1 / 6, 1 / 5, 1 / 4, 1 / 3, 1 / 3, 1 / 3, 1 / 2, 1, 2, 3],  # soil
        [1 / 7, 1 / 6, 1 / 5, 1 / 5, 1 / 4, 1 / 3, 1 / 3, 1 / 2, 1, 2],  # ndvi
        [1 / 8, 1 / 7, 1 / 6, 1 / 5, 1 / 5, 1 / 4, 1 / 3, 1 / 3, 1 / 2, 1],  # curvature
    ],
    dtype=np.float64,
)

# Random Consistency Index (Saaty, 1980) for matrix size n
_RI_TABLE = {1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

# Visualization
MCA_VIZ = {"min": 1, "max": 5, "palette": ["1a9850", "91cf60", "ffffbf", "fc8d59", "d73027"]}

FACTOR_VIZ = {"min": 1, "max": 5, "palette": ["2166ac", "67a9cf", "f7f7f7", "ef8a62", "b2182b"]}


# ═══════════════════════════════════════════════════════════════
# AHP Weight Computation
# ═══════════════════════════════════════════════════════════════


def compute_ahp_weights(matrix=None):
    """Compute priority weights from a pairwise comparison matrix.

    Uses the principal eigenvector method (Saaty, 1980).

    Returns:
        dict with 'weights', 'cr', 'ci', 'lambda_max', 'consistent', 'matrix'
    """
    if matrix is None:
        matrix = _AHP_MATRIX

    n = matrix.shape[0]

    # Principal eigenvector via power method
    eigvals, eigvecs = np.linalg.eig(matrix)
    max_idx = np.argmax(eigvals.real)
    lambda_max = eigvals[max_idx].real
    principal = eigvecs[:, max_idx].real
    weights = principal / principal.sum()

    # Consistency Index and Ratio
    ci = (lambda_max - n) / (n - 1)
    ri = _RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri > 0 else 0.0

    weight_dict = {}
    for i, name in enumerate(FACTOR_NAMES):
        weight_dict[name] = round(float(weights[i]), 4)

    return {
        "weights": weight_dict,
        "cr": round(float(cr), 4),
        "ci": round(float(ci), 4),
        "lambda_max": round(float(lambda_max), 4),
        "consistent": cr < 0.10,
        "ri": ri,
        "n_factors": n,
    }


# ═══════════════════════════════════════════════════════════════
# Factor Computation (GEE)
# ═══════════════════════════════════════════════════════════════


def _percentile_reclassify(image, band, aoi_geom, invert=False):
    """Reclassify a single-band image into 1-5 classes using AOI percentiles.

    Args:
        invert: If True, high values = low risk (class 1). Default False = high values = high risk (class 5).
    """
    pctiles = image.reduceRegion(
        reducer=ee.Reducer.percentile([20, 40, 60, 80]),
        geometry=aoi_geom,
        scale=100,
        bestEffort=True,
    )
    p20 = ee.Number(pctiles.get(f"{band}_p20"))
    p40 = ee.Number(pctiles.get(f"{band}_p40"))
    p60 = ee.Number(pctiles.get(f"{band}_p60"))
    p80 = ee.Number(pctiles.get(f"{band}_p80"))

    if invert:
        # High value = low risk
        return (
            ee.Image(3)
            .where(image.lte(p20), 5)
            .where(image.gt(p20).And(image.lte(p40)), 4)
            .where(image.gt(p60).And(image.lte(p80)), 2)
            .where(image.gt(p80), 1)
            .clip(aoi_geom)
        )
    else:
        # High value = high risk
        return (
            ee.Image(3)
            .where(image.lte(p20), 1)
            .where(image.gt(p20).And(image.lte(p40)), 2)
            .where(image.gt(p60).And(image.lte(p80)), 4)
            .where(image.gt(p80), 5)
            .clip(aoi_geom)
        )


def compute_factor_layers(aoi_geom):
    """Compute all 10 conditioning factor layers reclassified to 1-5 scale.

    Returns dict mapping factor name -> reclassified ee.Image (1-5).
    """
    dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    flow_acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1").clip(aoi_geom)

    factors = {}

    # ── 1. Distance to River ────────────────────────────────
    # Closer to river = higher risk (class 5)
    stream_threshold = 100
    streams = flow_acc.gt(stream_threshold)
    # fastDistanceTransform: distance (in pixels) to nearest non-zero pixel
    dist_px = streams.fastDistanceTransform(neighborhood=2048).sqrt()
    pixel_scale = ee.Image.pixelArea().sqrt()
    dist_m = dist_px.multiply(pixel_scale).rename("dist")
    factors["distance_to_river"] = _percentile_reclassify(dist_m, "dist", aoi_geom, invert=True)

    # ── 2. Rainfall ─────────────────────────────────────────
    # Higher rainfall = higher risk (class 5)
    rain = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate("2023-01-01", "2024-01-01")
        .sum()
        .rename("rain")
        .clip(aoi_geom)
    )
    factors["rainfall"] = _percentile_reclassify(rain, "rain", aoi_geom, invert=False)

    # ── 3. Slope ────────────────────────────────────────────
    # Lower slope (flat) = higher risk — water pools on flat terrain
    slope_r = slope.rename("slope")
    factors["slope"] = _percentile_reclassify(slope_r, "slope", aoi_geom, invert=True)

    # ── 4. Elevation ────────────────────────────────────────
    # Lower elevation = higher risk — lowlands flood first
    elev = dem.rename("elevation")
    factors["elevation"] = _percentile_reclassify(elev, "elevation", aoi_geom, invert=True)

    # ── 5. Drainage Density ─────────────────────────────────
    # Higher density = more streams = higher risk
    streams_mask = flow_acc.gt(stream_threshold).selfMask()
    dd = (
        streams_mask.reduceNeighborhood(ee.Reducer.sum(), ee.Kernel.circle(1500, "meters"))
        .multiply(0.09)
        .divide(math.pi * 1.5 * 1.5)
        .rename("dd")
        .clip(aoi_geom)
    )
    factors["drainage_density"] = _percentile_reclassify(dd, "dd", aoi_geom, invert=False)

    # ── 6. TWI (Topographic Wetness Index) ──────────────────
    # TWI = ln(a / tan(β)), higher TWI = wetter = higher risk
    slope_rad = slope.multiply(math.pi / 180)
    tan_slope = slope_rad.tan().max(0.001)  # avoid division by zero
    # Use flow accumulation as contributing area proxy (pixel count * area)
    contrib_area = flow_acc.max(1).multiply(ee.Image.pixelArea())
    twi = contrib_area.divide(tan_slope).log().rename("twi").clip(aoi_geom)
    factors["twi"] = _percentile_reclassify(twi, "twi", aoi_geom, invert=False)

    # ── 7. LULC ─────────────────────────────────────────────
    # Remap ESA WorldCover classes to flood vulnerability 1-5
    lulc = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select("Map").clip(aoi_geom)
    # 10=Trees, 20=Shrub, 30=Grass, 40=Cropland, 50=Built-up,
    # 60=Bare, 70=Snow, 80=Water, 90=Wetland, 95=Mangrove, 100=Moss
    factors["lulc"] = lulc.remap(
        [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100],
        [1, 2, 3, 4, 5, 4, 1, 5, 5, 4, 3],
    ).clip(aoi_geom)

    # ── 8. Soil Texture ─────────────────────────────────────
    # Clay-rich = poor drainage = high risk; Sandy = low risk
    soil = ee.Image("OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02").select("b0").clip(aoi_geom)
    # USDA classes: 1=Clay,2=SiltyClay,3=SandyClay,4=ClayLoam,5=SiltyClayLoam,
    #               6=SandyClayLoam,7=Loam,8=SiltLoam,9=SandyLoam,10=Silt,
    #               11=LoamySand,12=Sand
    factors["soil"] = soil.remap(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [5, 5, 4, 4, 4, 3, 3, 3, 2, 4, 2, 1],
    ).clip(aoi_geom)

    # ── 9. NDVI ─────────────────────────────────────────────
    # Lower NDVI = less vegetation = more runoff = higher risk
    ndvi = (
        ee.ImageCollection("MODIS/061/MOD13A2")
        .filterDate("2023-01-01", "2024-01-01")
        .select("NDVI")
        .mean()
        .multiply(0.0001)  # MODIS scale factor
        .rename("ndvi")
        .clip(aoi_geom)
    )
    factors["ndvi"] = _percentile_reclassify(ndvi, "ndvi", aoi_geom, invert=True)

    # ── 10. Curvature ───────────────────────────────────────
    # Negative (concave) = collects water = higher risk
    # Positive (convex)  = sheds water    = lower risk
    laplacian_kernel = ee.Kernel.fixed(3, 3, [[0, 1, 0], [1, -4, 1], [0, 1, 0]])
    curvature = dem.convolve(laplacian_kernel).rename("curv").clip(aoi_geom)
    # Negative curvature → high risk, so invert=True (more negative = higher class)
    # Actually: more negative = concave = collects water.
    # percentile_reclassify with invert=True means: low values → class 5.
    # Since concave is negative (low), invert=True gives concave→5. Correct.
    factors["curvature"] = _percentile_reclassify(curvature, "curv", aoi_geom, invert=True)

    return factors


# ═══════════════════════════════════════════════════════════════
# Composite Flood Susceptibility Map
# ═══════════════════════════════════════════════════════════════


def compute_flood_susceptibility(aoi_geom, weights=None):
    """Compute the weighted AHP flood susceptibility composite.

    Args:
        aoi_geom: ee.Geometry
        weights: dict mapping factor name -> weight (0-1, sum to 1).
                 If None, AHP weights are computed from the default matrix.

    Returns:
        (composite_image, factor_layers, ahp_report)
    """
    if weights is None:
        ahp = compute_ahp_weights()
        weights = ahp["weights"]
    else:
        ahp = {"weights": weights, "cr": None, "ci": None, "lambda_max": None, "consistent": True}

    factors = compute_factor_layers(aoi_geom)

    # Weighted linear combination
    composite = ee.Image(0).toFloat()
    for name in FACTOR_NAMES:
        w = weights.get(name, 0)
        composite = composite.add(factors[name].toFloat().multiply(w))

    # Round to 1-5
    composite = composite.round().clamp(1, 5).clip(aoi_geom)

    return composite, factors, ahp


# ═══════════════════════════════════════════════════════════════
# Cached Public API
# ═══════════════════════════════════════════════════════════════


@cache_data(ttl=3600)
def get_mca_tile(aoi_json, method="ahp", custom_weights=None):
    """Compute AHP-MCDM flood susceptibility map.

    Args:
        aoi_json: JSON string of AOI geometry
        method: "ahp" (automatic weights) or "custom"
        custom_weights: JSON string of weight dict (only for method="custom")

    Returns:
        dict with tile_url, factor_urls, ahp_report
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    weights = None
    if method == "custom" and custom_weights:
        weights = json.loads(custom_weights) if isinstance(custom_weights, str) else custom_weights

    composite, factors, ahp = compute_flood_susceptibility(aoi_geom, weights)

    # Composite tile
    tile_url = composite.getMapId(MCA_VIZ)["tile_fetcher"].url_format

    # Individual factor tiles for paper figures
    factor_urls = {}
    for name, img in factors.items():
        factor_urls[name] = img.getMapId(FACTOR_VIZ)["tile_fetcher"].url_format

    return {
        "tile_url": tile_url,
        "factor_urls": factor_urls,
        "ahp": ahp,
    }


@cache_data(ttl=3600)
def get_ahp_weights():
    """Return AHP weights and consistency metrics (no GEE call needed)."""
    return compute_ahp_weights()


@cache_data(ttl=3600)
def get_factor_stats(aoi_json):
    """Compute per-factor area distribution across risk classes 1-5."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    factors = compute_factor_layers(aoi_geom)
    total_area = ee.Number(aoi_geom.area(maxError=1)).divide(1e6)  # km2

    stats = {}
    for name, img in factors.items():
        class_areas = {}
        for cls in range(1, 6):
            mask = img.eq(cls)
            area = (
                mask.multiply(ee.Image.pixelArea())
                .reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, bestEffort=True)
                .values()
                .get(0)
            )
            class_areas[str(cls)] = ee.Number(area).divide(1e6)  # km2

        stats[name] = ee.Dictionary(class_areas).getInfo()

    stats["total_area_km2"] = round(total_area.getInfo(), 2)
    return stats


# ── Legacy compatibility ────────────────────────────────────
# Keep old function signature working for existing callers


def calculate_flood_risk(aoi_geom, w_lulc=0.40, w_slope=0.30, w_rain=0.30):
    """Legacy 3-factor wrapper. Redirects to full AHP."""
    composite, _, _ = compute_flood_susceptibility(aoi_geom)
    return composite
