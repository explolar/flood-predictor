"""
Feature 15: 3D Terrain Flood Visualization using PyDeck.
Creates interactive 3D terrain with flood extent overlay.
"""

import json
import numpy as np

try:
    import pydeck as pdk
    _PYDECK = True
except ImportError:
    _PYDECK = False


def create_3d_terrain_view(aoi_json, dem_data=None, flood_data=None, map_center=None):
    """
    Create an interactive 3D PyDeck visualization of terrain with flood overlay.

    Args:
        aoi_json: GEE AOI JSON string.
        dem_data: List of dicts with lat, lon, elevation keys.
        flood_data: List of dicts with lat, lon, flood_depth keys (optional).
        map_center: [lat, lon].

    Returns:
        pydeck.Deck object for rendering, or None if pydeck unavailable.
    """
    if not _PYDECK:
        return None

    if not dem_data or not map_center:
        return None

    # DEM as ColumnLayer
    terrain_layer = pdk.Layer(
        'ColumnLayer',
        data=dem_data,
        get_position=['lon', 'lat'],
        get_elevation='elevation',
        elevation_scale=50,
        radius=50,
        get_fill_color='[40, 100 + elevation * 1.5, 80, 200]',
        pickable=True,
        auto_highlight=True,
    )

    layers = [terrain_layer]

    # Flood overlay
    if flood_data:
        flood_layer = pdk.Layer(
            'ColumnLayer',
            data=flood_data,
            get_position=['lon', 'lat'],
            get_elevation='flood_depth',
            elevation_scale=500,
            radius=50,
            get_fill_color='[0, 180, 255, 180]',
            pickable=True,
        )
        layers.append(flood_layer)

    view_state = pdk.ViewState(
        latitude=map_center[0],
        longitude=map_center[1],
        zoom=11,
        pitch=45,
        bearing=-30,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/dark-v10',
        tooltip={
            'text': 'Elevation: {elevation}m\nLat: {lat}\nLon: {lon}'
        }
    )

    return deck


def extract_dem_grid(aoi_json, scale=200):
    """
    Extract DEM grid from GEE for 3D visualization.

    Returns list of dicts with lat, lon, elevation.
    """
    import ee

    aoi_geom = ee.Geometry(json.loads(aoi_json))
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)

    # Sample grid points
    points = dem.sample(
        region=aoi_geom, scale=scale, numPixels=3000,
        seed=42, geometries=True
    )

    data = points.getInfo()
    if not data or not data.get('features'):
        return []

    records = []
    for feat in data['features']:
        geom = feat.get('geometry', {})
        props = feat.get('properties', {})
        if geom.get('type') == 'Point' and props.get('elevation') is not None:
            records.append({
                'lon': geom['coordinates'][0],
                'lat': geom['coordinates'][1],
                'elevation': round(props['elevation'], 1),
            })

    return records
