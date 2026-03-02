import ee
import json
import math
import requests
import streamlit as st


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@st.cache_data(show_spinner=False, ttl=3600)
def get_osm_infrastructure(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        bb = aoi_geom.bounds().getInfo()['coordinates'][0]
        lats = [c[1] for c in bb];  lons = [c[0] for c in bb]
        s, n, w, e = min(lats), max(lats), min(lons), max(lons)
        query = f"""[out:json][timeout:20];
(node["amenity"~"hospital|school|fire_station|police"]({s},{w},{n},{e});
 way["amenity"~"hospital|school|fire_station|police"]({s},{w},{n},{e}););
out center 100;"""
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=25)
        r.raise_for_status()
        elements = r.json().get('elements', [])
        infra = []
        for el in elements:
            lat = el.get('lat') or (el.get('center') or {}).get('lat')
            lon = el.get('lon') or (el.get('center') or {}).get('lon')
            if lat and lon:
                amenity = el.get('tags', {}).get('amenity', 'unknown')
                name    = el.get('tags', {}).get('name', amenity.replace('_',' ').title())
                infra.append({'lat': lat, 'lon': lon, 'type': amenity, 'name': name})
        return infra
    except Exception:
        return []


@st.cache_data(show_spinner=False, ttl=3600)
def get_osm_roads(aoi_json):
    """Fetch road network from OSM Overpass."""
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        bb   = aoi_geom.bounds().getInfo()['coordinates'][0]
        lats = [c[1] for c in bb]; lons = [c[0] for c in bb]
        s, n, w, e = min(lats), max(lats), min(lons), max(lons)
        query = f"""[out:json][timeout:30];
way["highway"~"motorway|trunk|primary|secondary|tertiary"]({s},{w},{n},{e});
out geom 500;"""
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=35)
        r.raise_for_status()
        elements = r.json().get('elements', [])
        roads, km_by_type = [], {}
        margin = max((n - s), (e - w)) * 0.15
        for el in elements:
            geom = el.get('geometry', [])
            if len(geom) < 2:
                continue
            hw   = el.get('tags', {}).get('highway', 'road')
            name = el.get('tags', {}).get('name', '')
            coords = [[p['lon'], p['lat']] for p in geom]
            length_km = sum(
                _haversine_km(geom[i]['lat'], geom[i]['lon'], geom[i+1]['lat'], geom[i+1]['lon'])
                for i in range(len(geom) - 1)
            )
            km_by_type[hw] = km_by_type.get(hw, 0) + length_km
            near_edge = any(
                p['lat'] < s + margin or p['lat'] > n - margin or
                p['lon'] < w + margin or p['lon'] > e - margin
                for p in geom
            )
            evacuation = near_edge and hw in ('motorway', 'trunk', 'primary', 'secondary')
            roads.append({'coords': coords, 'highway': hw, 'name': name,
                          'length_km': round(length_km, 2), 'evacuation': evacuation})
        return {'roads': roads, 'km_by_type': {k: round(v, 1) for k, v in km_by_type.items()}}
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=7200)
def get_dam_data(aoi_json):
    """Return dams/reservoirs within 150 km of AOI from GRanD v1.3."""
    try:
        aoi_geom    = ee.Geometry(json.loads(aoi_json))
        aoi_buf     = aoi_geom.buffer(150000)
        dams_fc     = ee.FeatureCollection('projects/sat-io/open-datasets/GRanD/GRAND_Dams_v1_3').filterBounds(aoi_buf)
        dam_info    = dams_fc.getInfo()
        result = []
        for feat in dam_info.get('features', []):
            p    = feat.get('properties', {})
            geom = feat.get('geometry', {})
            if geom.get('type') == 'Point':
                lon, lat = geom['coordinates']
                result.append({
                    'lat':          lat,
                    'lon':          lon,
                    'name':         p.get('DAM_NAME', 'Unknown'),
                    'river':        p.get('RIVER', '\u2014'),
                    'capacity_mcm': round(float(p.get('CAP_MCM') or 0), 0),
                    'main_use':     p.get('MAIN_USE', '\u2014'),
                    'year':         int(p.get('YEAR') or 0) or '\u2014',
                })
        result.sort(key=lambda x: x['capacity_mcm'], reverse=True)
        return result
    except Exception:
        return []
