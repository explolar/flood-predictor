"""
GEE pixel sampling functions for ML training data extraction.
Returns pandas DataFrames suitable for scikit-learn model training.
"""

import ee
import json
import pandas as pd
import numpy as np


def _features_from_info(sample_info, feature_names, label_name=None):
    """Convert ee.FeatureCollection.getInfo() output to a pandas DataFrame."""
    records = []
    for feat in sample_info.get('features', []):
        props = feat.get('properties', {})
        row = {}
        for fn in feature_names:
            row[fn] = props.get(fn)
        if label_name:
            row[label_name] = props.get(label_name)
        # Keep geometry for reconstruction
        geom = feat.get('geometry')
        if geom and geom.get('type') == 'Point':
            row['longitude'] = geom['coordinates'][0]
            row['latitude'] = geom['coordinates'][1]
        records.append(row)
    df = pd.DataFrame(records).dropna()
    return df


def extract_risk_training_samples(aoi_json, n_points=5000, scale=100):
    """
    Sample pixels within AOI, extracting terrain/climate features and
    JRC-derived flood risk labels for training the Random Forest risk model.

    Features: elevation, slope, annual_rainfall, lulc_class, jrc_occurrence, jrc_max_extent
    Target: risk_class (1-5, derived from JRC occurrence)

    Returns: pandas DataFrame
    """
    aoi_geom = ee.Geometry(json.loads(aoi_json))

    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom).rename('slope')
    rainfall = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                .filterDate('2023-01-01', '2024-01-01').sum()
                .clip(aoi_geom).rename('annual_rainfall'))
    lulc = (ee.ImageCollection("ESA/WorldCover/v200").mosaic()
            .select('Map').clip(aoi_geom).rename('lulc_class'))
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
    jrc_occ = jrc.select('occurrence').clip(aoi_geom).rename('jrc_occurrence')
    jrc_max = jrc.select('max_extent').clip(aoi_geom).rename('jrc_max_extent')

    # Target: reclassify JRC occurrence to 5 risk classes
    risk_target = (jrc_occ
                   .where(jrc_occ.lt(5), 1)
                   .where(jrc_occ.gte(5).And(jrc_occ.lt(20)), 2)
                   .where(jrc_occ.gte(20).And(jrc_occ.lt(40)), 3)
                   .where(jrc_occ.gte(40).And(jrc_occ.lt(70)), 4)
                   .where(jrc_occ.gte(70), 5)
                   .rename('risk_class'))

    feature_stack = (dem.rename('elevation')
                     .addBands(slope)
                     .addBands(rainfall)
                     .addBands(lulc)
                     .addBands(jrc_occ)
                     .addBands(jrc_max)
                     .addBands(risk_target))

    samples = feature_stack.stratifiedSample(
        numPoints=n_points // 5,
        classBand='risk_class',
        region=aoi_geom,
        scale=scale,
        seed=42,
        geometries=True
    )

    sample_info = samples.getInfo()
    feature_names = ['elevation', 'slope', 'annual_rainfall',
                     'lulc_class', 'jrc_occurrence', 'jrc_max_extent']
    return _features_from_info(sample_info, feature_names, label_name='risk_class')


def extract_sar_training_samples(aoi_json, f_start, f_end, p_start, p_end,
                                  threshold, polarization, speckle,
                                  n_points=4000, scale=30):
    """
    Sample pixels with SAR + terrain features and threshold-based flood labels
    for training the Gradient Boosting SAR classifier.

    Features: pre_sar, post_sar, sar_diff, sar_ratio, elevation, slope, jrc_occ, jrc_season
    Target: flood_label (binary 0/1 from threshold-based flood mask)

    Returns: pandas DataFrame
    """
    from gee_functions.sar import _make_flood_mask

    aoi_geom = ee.Geometry(json.loads(aoi_json))

    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi_geom)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
          .select(polarization))

    pre = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
    post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
    if speckle:
        pre = pre.focal_mean(radius=1, kernelType='square', units='pixels')
        post = post.focal_mean(radius=1, kernelType='square', units='pixels')

    flood_mask, dem = _make_flood_mask(pre, post, threshold, aoi_geom)

    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")

    # Build feature stack
    diff = pre.subtract(post)
    ratio = pre.divide(post.add(ee.Image(0.001)))

    # Create binary label: flood=1, non-flood=0
    # For non-flood areas we need to fill with 0 where flood_mask is masked
    label = flood_mask.unmask(0).rename('flood_label')

    feature_stack = (pre.rename('pre_sar')
                     .addBands(post.rename('post_sar'))
                     .addBands(diff.rename('sar_diff'))
                     .addBands(ratio.rename('sar_ratio'))
                     .addBands(dem.rename('elevation'))
                     .addBands(slope.rename('slope'))
                     .addBands(jrc.select('occurrence').clip(aoi_geom).rename('jrc_occ'))
                     .addBands(jrc.select('seasonality').clip(aoi_geom).rename('jrc_season'))
                     .addBands(label))

    samples = feature_stack.stratifiedSample(
        numPoints=n_points // 2,
        classBand='flood_label',
        region=aoi_geom,
        scale=scale,
        seed=42,
        geometries=True
    )

    sample_info = samples.getInfo()
    feature_names = ['pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
                     'elevation', 'slope', 'jrc_occ', 'jrc_season']
    return _features_from_info(sample_info, feature_names, label_name='flood_label')


def dataframe_to_ee_fc(df, value_col, lat_col='latitude', lon_col='longitude',
                       max_features=4500):
    """Convert a DataFrame with lat/lon + prediction column to an ee.FeatureCollection.

    GEE client-side FeatureCollections are limited to ~5000 elements.
    If the DataFrame exceeds max_features, it is subsampled.
    """
    if len(df) > max_features:
        df = df.sample(n=max_features, random_state=42)

    features = []
    for _, row in df.iterrows():
        geom = ee.Geometry.Point([row[lon_col], row[lat_col]])
        features.append(ee.Feature(geom, {value_col: int(row[value_col])}))
    return ee.FeatureCollection(features)
