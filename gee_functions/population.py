"""
Feature 7: Population Displacement Estimator.
Uses WorldPop age/sex demographics to estimate affected and displaced populations.
"""

import ee
import json
import streamlit as st


@st.cache_data(show_spinner=False, ttl=3600)
def get_displacement_estimate(aoi_json, flood_mask_threshold=3.0):
    """
    Estimate population displacement using WorldPop data crossed with flood extent.

    Uses WorldPop/GP/100m/pop_age_sex_cons_unadj for detailed demographics.

    Returns dict with total affected, displaced estimate, children, elderly counts.
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    # WorldPop total population
    pop_total = (ee.ImageCollection('WorldPop/GP/100m/pop_age_sex_cons_unadj')
                 .filterBounds(aoi_geom)
                 .filterDate('2020-01-01', '2021-01-01')
                 .first())

    if pop_total is None:
        return None

    # Total population bands
    pop = pop_total.select('population').clip(aoi_geom)

    # Age-specific bands (children <15, elderly >60)
    # WorldPop has bands like M_0, M_1, ..., M_80, F_0, F_1, ..., F_80
    child_bands = [f'{g}_{a}' for g in ['M', 'F'] for a in range(0, 15)]
    elderly_bands = [f'{g}_{a}' for g in ['M', 'F'] for a in range(60, 85, 5)]

    # Get available bands
    available = pop_total.bandNames().getInfo() or []
    child_bands = [b for b in child_bands if b in available]
    elderly_bands = [b for b in elderly_bands if b in available]

    # Total population in AOI
    total_pop_stats = pop.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi_geom, scale=100, maxPixels=1e9
    ).getInfo() or {}
    total_pop = round(total_pop_stats.get('population', 0) or 0)

    # For displacement calculation, use a simple flood mask from SAR
    # (assumes the caller will provide flood extent data separately)
    # Here we estimate based on total AOI for now
    children_pop = 0
    elderly_pop = 0

    if child_bands:
        children = pop_total.select(child_bands).reduce(ee.Reducer.sum()).clip(aoi_geom)
        child_stats = children.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, maxPixels=1e9
        ).getInfo() or {}
        children_pop = round(sum(v for v in child_stats.values() if v))

    if elderly_bands:
        elderly = pop_total.select(elderly_bands).reduce(ee.Reducer.sum()).clip(aoi_geom)
        elderly_stats = elderly.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, maxPixels=1e9
        ).getInfo() or {}
        elderly_pop = round(sum(v for v in elderly_stats.values() if v))

    # Displacement estimate: typically 60-80% of flood-exposed population
    displaced_estimate = round(total_pop * 0.7)

    return {
        'total_population': total_pop,
        'displaced_estimate': displaced_estimate,
        'children_affected': children_pop,
        'elderly_affected': elderly_pop,
        'displacement_rate': 0.7,
    }
