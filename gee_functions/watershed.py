"""Hydrology module — watershed delineation, stream network, flow analysis, HAND."""

import json

import ee
import streamlit as st

from ui_components.constants import (
    COND_DEM_VIZ,
    DRAINAGE_DENSITY_VIZ,
    FLOW_ACC_VIZ,
    FLOW_DIR_VIZ,
    HAND_VIZ,
    STREAM_ORDER_VIZ,
)

# ── Existing: basin boundary lookup ──────────────────────────


@st.cache_data(show_spinner=False, ttl=7200)
def get_watershed_geojson(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    hydrobasins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8")
    ws = hydrobasins.filterBounds(aoi_geom)
    return ws.geometry().getInfo()


# ── Batch hydrology computation ──────────────────────────────


@st.cache_data(show_spinner=False, ttl=3600)
def get_all_hydrology_data(aoi_json, stream_threshold=100):
    """Compute flow accumulation, stream network, flow direction tiles and stats.

    Raises on failure so st.cache_data does NOT cache error results.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    flow_acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1").clip(aoi_geom)
    flow_dir = ee.Image("WWF/HydroSHEDS/15DIR").select("b1").clip(aoi_geom)
    cond_dem = ee.Image("WWF/HydroSHEDS/15CONDEM").select("b1").clip(aoi_geom)

    # Stream network from flow accumulation threshold
    streams = flow_acc.gt(stream_threshold).selfMask()

    # Stream order proxy via log10 binning (Strahler approximation)
    log_acc = flow_acc.max(1).log10()
    order = (
        ee.Image(0)
        .where(log_acc.gte(2).And(log_acc.lt(3)), 1)
        .where(log_acc.gte(3).And(log_acc.lt(4)), 2)
        .where(log_acc.gte(4).And(log_acc.lt(5)), 3)
        .where(log_acc.gte(5).And(log_acc.lt(6)), 4)
        .where(log_acc.gte(6), 5)
        .updateMask(streams)
        .rename("stream_order")
    )

    # Tile URLs
    flow_acc_log = flow_acc.max(1).log10().clip(aoi_geom)
    flow_acc_url = flow_acc_log.getMapId(FLOW_ACC_VIZ)["tile_fetcher"].url_format
    flow_dir_url = flow_dir.getMapId(FLOW_DIR_VIZ)["tile_fetcher"].url_format
    stream_url = order.getMapId(STREAM_ORDER_VIZ)["tile_fetcher"].url_format
    cond_dem_url = cond_dem.getMapId(COND_DEM_VIZ)["tile_fetcher"].url_format

    # Stats
    stats = flow_acc.reduceRegion(
        reducer=ee.Reducer.max().combine(ee.Reducer.mean(), sharedInputs=True),
        geometry=aoi_geom,
        scale=100,
        bestEffort=True,
    ).getInfo()

    stream_count = streams.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=aoi_geom,
        scale=90,
        bestEffort=True,
    ).getInfo()

    dem_stats = cond_dem.reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), sharedInputs=True),
        geometry=aoi_geom,
        scale=100,
        bestEffort=True,
    ).getInfo()

    pixel_count = stream_count.get("b1", 0) or 0
    stream_length_km = round(pixel_count * 0.09, 1)

    return {
        "flow_acc_url": flow_acc_url,
        "flow_dir_url": flow_dir_url,
        "stream_url": stream_url,
        "cond_dem_url": cond_dem_url,
        "stream_length_km": stream_length_km,
        "max_accumulation": stats.get("b1_max", 0),
        "mean_accumulation": round(stats.get("b1_mean", 0), 1),
        "dem_min": round(dem_stats.get("b1_min", 0), 1),
        "dem_max": round(dem_stats.get("b1_max", 0), 1),
        "dem_mean": round(dem_stats.get("b1_mean", 0), 1),
    }


# ── Multi-level basin hierarchy ──────────────────────────────


@st.cache_data(show_spinner=False, ttl=7200)
def get_multi_basin_geojson(aoi_json):
    """Return GeoJSON for HydroSHEDS basin levels 6, 8, 10."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    result = {}
    for level in [6, 8, 10]:
        asset = f"WWF/HydroSHEDS/v1/Basins/hybas_{level}"
        fc = ee.FeatureCollection(asset).filterBounds(aoi_geom).limit(50)
        count = fc.size().getInfo()
        geojson = fc.geometry().getInfo() if count > 0 else None
        result[f"hybas_{level}"] = {"geojson": geojson, "count": count}
    return result


# ── Drainage density ─────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=3600)
def get_drainage_density(aoi_json, stream_threshold=100):
    """Compute spatial drainage density (km/km2) and scalar metric."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    flow_acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1").clip(aoi_geom)
    streams = flow_acc.gt(stream_threshold).selfMask()

    # Local density: count stream pixels in 1.5 km radius, normalize
    local_density = (
        streams.reduceNeighborhood(ee.Reducer.sum(), ee.Kernel.circle(1500, "meters"))
        .multiply(0.09)
        .divide(3.14159 * 1.5 * 1.5)
        .rename("drainage_density")
    )

    density_url = local_density.getMapId(DRAINAGE_DENSITY_VIZ)["tile_fetcher"].url_format

    # Scalar: total stream length / AOI area
    stream_count = streams.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=aoi_geom,
        scale=90,
        bestEffort=True,
    ).getInfo()
    area_km2 = ee.Number(aoi_geom.area(maxError=1)).divide(1e6).getInfo()

    pixel_count = stream_count.get("b1", 0) or 0
    total_length_km = pixel_count * 0.09
    scalar_density = round(total_length_km / max(area_km2, 0.01), 2)

    return {
        "density_url": density_url,
        "scalar_density": scalar_density,
        "total_length_km": round(total_length_km, 1),
        "area_km2": round(area_km2, 1),
    }


# ── HAND (Height Above Nearest Drainage) ─────────────────────


@st.cache_data(show_spinner=False, ttl=3600)
def get_hand_data(aoi_json, stream_threshold=100, flood_depth_m=None):
    """
    Compute HAND (Height Above Nearest Drainage) for the AOI.

    Algorithm:
        1. Identify drainage pixels from HydroSHEDS flow accumulation > threshold
        2. Assign drainage pixel elevations from the conditioned DEM
        3. Propagate drainage elevation to all pixels via cost-distance
           (approximate via focal reduction at expanding radii)
        4. HAND = pixel_elevation - nearest_drainage_elevation

    When flood_depth_m is provided, also returns a flood extent mask
    (HAND <= flood_depth_m) and affected area statistics.

    Returns dict with HAND tile URL, stats, and optional flood extent tile.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    cond_dem = ee.Image("WWF/HydroSHEDS/15CONDEM").select("b1").clip(aoi_geom)
    flow_acc = ee.Image("WWF/HydroSHEDS/15ACC").select("b1").clip(aoi_geom)

    # Drainage network mask
    drainage_mask = flow_acc.gt(stream_threshold)

    # Elevation at drainage pixels only (masked elsewhere)
    drainage_elev = cond_dem.updateMask(drainage_mask)

    # Propagate nearest drainage elevation using iterative focal minimum
    # Each iteration spreads drainage elevation by ~90m (1 pixel)
    # 20 iterations ≈ 1.8 km reach, 40 ≈ 3.6 km
    nearest_drainage = drainage_elev
    for radius in [3, 5, 10, 20, 30, 40]:
        filled = nearest_drainage.focal_min(radius=radius, kernelType="circle", units="pixels")
        nearest_drainage = nearest_drainage.unmask(filled)

    # Final fallback: fill any remaining gaps with the minimum DEM in AOI
    dem_min = cond_dem.reduceRegion(
        reducer=ee.Reducer.min(),
        geometry=aoi_geom,
        scale=90,
        bestEffort=True,
    )
    nearest_drainage = nearest_drainage.unmask(ee.Number(dem_min.get("b1")))

    # HAND = DEM - nearest drainage elevation (clamped >= 0)
    hand = cond_dem.subtract(nearest_drainage).max(0).rename("hand")

    # Stats
    hand_stats = (
        hand.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.percentile([10, 50, 90]),
                sharedInputs=True,
            ),
            geometry=aoi_geom,
            scale=90,
            bestEffort=True,
        ).getInfo()
        or {}
    )

    # HAND tile
    hand_url = hand.getMapId(HAND_VIZ)["tile_fetcher"].url_format

    result = {
        "hand_url": hand_url,
        "mean_hand_m": round(hand_stats.get("hand_mean", 0) or 0, 2),
        "p10_hand_m": round(hand_stats.get("hand_p10", 0) or 0, 2),
        "p50_hand_m": round(hand_stats.get("hand_p50", 0) or 0, 2),
        "p90_hand_m": round(hand_stats.get("hand_p90", 0) or 0, 2),
        "stream_threshold": stream_threshold,
    }

    # Optional: flood inundation extent at a given water depth
    if flood_depth_m is not None and flood_depth_m > 0:
        flood_mask = hand.lte(flood_depth_m).selfMask().rename("flood")

        # Flood area in hectares
        flood_area = (
            flood_mask.multiply(ee.Image.pixelArea())
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=aoi_geom,
                scale=90,
                bestEffort=True,
            )
            .getInfo()
        )
        flood_ha = round((flood_area.get("flood", 0) or 0) / 10000, 1)

        # Total AOI area
        aoi_area = ee.Number(aoi_geom.area(maxError=1)).divide(10000).getInfo()
        pct_inundated = round(flood_ha / max(aoi_area, 0.01) * 100, 1)

        flood_url = flood_mask.getMapId(
            {
                "min": 0,
                "max": 1,
                "palette": ["00000000", "0077be"],
            }
        )["tile_fetcher"].url_format

        # Depth proxy within flooded zone: flood_depth_m - HAND
        depth = ee.Image(flood_depth_m).subtract(hand).max(0).updateMask(flood_mask).rename("depth")
        depth_url = depth.getMapId(
            {
                "min": 0,
                "max": flood_depth_m,
                "palette": ["ffffcc", "fed976", "fd8d3c", "f03b20", "bd0026"],
            }
        )["tile_fetcher"].url_format

        result.update(
            {
                "flood_url": flood_url,
                "depth_url": depth_url,
                "flood_depth_m": flood_depth_m,
                "flood_area_ha": flood_ha,
                "aoi_area_ha": round(aoi_area, 1),
                "pct_inundated": pct_inundated,
            }
        )

    return result


# ── Basin statistics ─────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=3600)
def get_basin_statistics(aoi_json):
    """Per-basin stats at hybas_8 level: area, upstream area, mean elevation."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    fc = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8").filterBounds(aoi_geom).limit(30)
    dem = ee.Image("USGS/SRTMGL1_003").select("elevation")

    def add_elev(feature):
        mean_elev = dem.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=feature.geometry(),
            scale=100,
            bestEffort=True,
        ).get("elevation")
        return feature.set("mean_elev", ee.Number(mean_elev).round())

    enriched = fc.map(add_elev)
    features = enriched.getInfo().get("features", [])

    rows = []
    for f in features:
        props = f.get("properties", {})
        rows.append(
            {
                "HYBAS_ID": props.get("HYBAS_ID", ""),
                "Sub-basin Area (km2)": round(props.get("SUB_AREA", 0), 1),
                "Upstream Area (km2)": round(props.get("UP_AREA", 0), 1),
                "Mean Elevation (m)": props.get("mean_elev", "N/A"),
            }
        )
    return rows
