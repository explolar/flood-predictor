"""AOI size validation to prevent GEE computation timeouts and quota errors.

GEE limits:
    - getInfo() calls timeout after ~5 minutes
    - reduceRegion maxPixels default 1e8
    - Client-side FeatureCollections limited to ~5000 elements
    - Large AOIs cause slow tile rendering and memory errors

This module enforces AOI size limits and provides adaptive scale parameters.
"""

import math

# Maximum AOI area in km2 (adjust based on your GEE quota)
MAX_AOI_AREA_KM2 = 50_000  # ~220 km x 220 km
WARN_AOI_AREA_KM2 = 10_000  # Warning threshold

# Maximum bbox span in degrees (prevents full-country selections)
MAX_BBOX_SPAN_DEG = 3.0


def estimate_bbox_area_km2(min_lon, min_lat, max_lon, max_lat):
    """Estimate bounding box area in km2 (approximate, no GEE call)."""
    dlon = abs(max_lon - min_lon)
    dlat = abs(max_lat - min_lat)
    # 1 degree latitude ~ 111 km, longitude varies with latitude
    mid_lat = (min_lat + max_lat) / 2
    km_per_deg_lon = 111.32 * math.cos(math.radians(mid_lat))
    km_per_deg_lat = 111.32
    return round(dlon * km_per_deg_lon * dlat * km_per_deg_lat, 1)


def validate_bbox(min_lon, min_lat, max_lon, max_lat):
    """
    Validate bounding box dimensions.

    Returns (is_valid, message, area_km2).
    """
    if min_lon >= max_lon or min_lat >= max_lat:
        return False, "Invalid bounds: min must be less than max.", 0

    dlon = max_lon - min_lon
    dlat = max_lat - min_lat

    if dlon > MAX_BBOX_SPAN_DEG or dlat > MAX_BBOX_SPAN_DEG:
        return (
            False,
            f"AOI too large: max span is {MAX_BBOX_SPAN_DEG}° "
            f"(got {dlon:.2f}° x {dlat:.2f}°). Reduce your bounding box.",
            0,
        )

    area = estimate_bbox_area_km2(min_lon, min_lat, max_lon, max_lat)

    if area > MAX_AOI_AREA_KM2:
        return (
            False,
            f"AOI too large: {area:,.0f} km² exceeds the {MAX_AOI_AREA_KM2:,} km² limit. "
            "Use a smaller region to avoid GEE timeouts.",
            area,
        )

    if area > WARN_AOI_AREA_KM2:
        return (
            True,
            f"Large AOI ({area:,.0f} km²) — some computations may be slow.",
            area,
        )

    return True, "", area


def validate_geojson_aoi(geojson_dict):
    """
    Validate a GeoJSON AOI.

    Returns (is_valid, message).
    """
    try:
        geom = geojson_dict.get("features", [{}])[0].get("geometry", {})
        coords = geom.get("coordinates", [[]])

        if geom.get("type") == "Polygon":
            ring = coords[0]
        elif geom.get("type") == "MultiPolygon":
            ring = coords[0][0]
        else:
            return True, ""  # Can't validate, let GEE handle it

        if len(ring) < 3:
            return False, "GeoJSON polygon has fewer than 3 vertices."

        lons = [c[0] for c in ring]
        lats = [c[1] for c in ring]
        area = estimate_bbox_area_km2(min(lons), min(lats), max(lons), max(lats))

        if area > MAX_AOI_AREA_KM2:
            return (
                False,
                f"GeoJSON AOI too large: ~{area:,.0f} km² exceeds {MAX_AOI_AREA_KM2:,} km² limit.",
            )

        return True, ""
    except Exception:
        return True, ""  # Don't block on parse errors, let GEE validate


def get_adaptive_scale(area_km2, base_scale=30):
    """
    Return an adaptive processing scale based on AOI size.

    Larger AOIs need coarser scales to stay within GEE compute limits.
    """
    if area_km2 > 20_000:
        return max(base_scale, 500)
    if area_km2 > 5_000:
        return max(base_scale, 250)
    if area_km2 > 1_000:
        return max(base_scale, 100)
    return base_scale


def get_adaptive_num_pixels(area_km2, base_pixels=5000):
    """
    Return adaptive sample count based on AOI size.

    Keeps total computation manageable while maintaining density for small AOIs.
    """
    if area_km2 > 10_000:
        return min(base_pixels, 2000)
    if area_km2 > 3_000:
        return min(base_pixels, 3000)
    return base_pixels
