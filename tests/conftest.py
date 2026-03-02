"""Shared fixtures for HydroRisk Atlas test suite."""

import json
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch


# ── AOI Fixtures ──────────────────────────────────────

PATNA_BBOX = {
    "type": "Polygon",
    "coordinates": [[[84.90, 25.50], [85.30, 25.50], [85.30, 25.80], [84.90, 25.80], [84.90, 25.50]]]
}


@pytest.fixture
def aoi_json():
    """Patna bounding box as a GEE-compatible JSON string."""
    return json.dumps(PATNA_BBOX)


@pytest.fixture
def aoi_geojson():
    """Patna bounding box as a dict."""
    return PATNA_BBOX


# ── Mock ee module ────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_ee(monkeypatch):
    """Mock the ee module so tests don't need GEE credentials."""
    mock = MagicMock()

    # ee.Geometry returns a mock geometry
    mock.Geometry.return_value = MagicMock()
    mock.Geometry.BBox.return_value = MagicMock()
    mock.Geometry.Point.return_value = MagicMock()
    mock.Geometry.Polygon.return_value = MagicMock()

    # ee.Image returns chainable mock
    mock_image = MagicMock()
    mock_image.select.return_value = mock_image
    mock_image.clip.return_value = mock_image
    mock_image.rename.return_value = mock_image
    mock_image.addBands.return_value = mock_image
    mock_image.where.return_value = mock_image
    mock_image.gte.return_value = mock_image
    mock_image.lt.return_value = mock_image
    mock_image.And.return_value = mock_image
    mock_image.subtract.return_value = mock_image
    mock_image.divide.return_value = mock_image
    mock_image.add.return_value = mock_image
    mock_image.unmask.return_value = mock_image
    mock_image.selfMask.return_value = mock_image
    mock_image.getMapId.return_value = {
        'tile_fetcher': MagicMock(url_format='https://earthengine.googleapis.com/map/test/{z}/{x}/{y}')
    }
    mock_image.reduceRegion.return_value = MagicMock(
        getInfo=MagicMock(return_value={
            'elev_min': 30, 'elev_max': 120, 'elev_mean': 55,
            'slope_mean': 2.3
        })
    )
    mock.Image.return_value = mock_image
    mock.Image.side_effect = lambda *a, **kw: mock_image

    # ee.Terrain
    mock.Terrain.slope.return_value = mock_image

    # ee.ImageCollection
    mock_ic = MagicMock()
    mock_ic.filterBounds.return_value = mock_ic
    mock_ic.filterDate.return_value = mock_ic
    mock_ic.filter.return_value = mock_ic
    mock_ic.select.return_value = mock_ic
    mock_ic.median.return_value = mock_image
    mock_ic.sum.return_value = mock_image
    mock_ic.mosaic.return_value = mock_image
    mock.ImageCollection.return_value = mock_ic
    mock.ImageCollection.side_effect = lambda *a, **kw: mock_ic

    # ee.Feature / ee.FeatureCollection
    mock.Feature.return_value = MagicMock()
    mock_fc = MagicMock()
    mock_fc.reduceToImage.return_value = mock_image
    mock.FeatureCollection.return_value = mock_fc

    # ee.Filter
    mock.Filter.listContains.return_value = MagicMock()

    # ee.Reducer
    mock.Reducer.minMax.return_value = MagicMock(combine=MagicMock(return_value=MagicMock()))
    mock.Reducer.mean.return_value = MagicMock()
    mock.Reducer.first.return_value = MagicMock()

    monkeypatch.setitem(__import__('sys').modules, 'ee', mock)
    return mock


# ── Sample Data Fixtures ──────────────────────────────

@pytest.fixture
def sample_risk_df():
    """Fake training data for FloodRiskPredictor."""
    rng = np.random.RandomState(42)
    n = 500
    return pd.DataFrame({
        'elevation': rng.uniform(20, 150, n),
        'slope': rng.uniform(0, 15, n),
        'annual_rainfall': rng.uniform(800, 2000, n),
        'lulc_class': rng.choice([10, 20, 30, 40, 50, 60], n),
        'jrc_occurrence': rng.uniform(0, 100, n),
        'jrc_max_extent': rng.choice([0, 1], n),
        'risk_class': rng.choice([1, 2, 3, 4, 5], n),
        'latitude': rng.uniform(25.5, 25.8, n),
        'longitude': rng.uniform(84.9, 85.3, n),
    })


@pytest.fixture
def sample_sar_df():
    """Fake training data for SARFloodClassifier."""
    rng = np.random.RandomState(42)
    n = 600
    return pd.DataFrame({
        'pre_sar': rng.uniform(-25, -5, n),
        'post_sar': rng.uniform(-30, -5, n),
        'sar_diff': rng.uniform(-10, 10, n),
        'sar_ratio': rng.uniform(0.5, 2.0, n),
        'elevation': rng.uniform(20, 150, n),
        'slope': rng.uniform(0, 15, n),
        'jrc_occ': rng.uniform(0, 100, n),
        'jrc_season': rng.uniform(0, 12, n),
        'flood_label': rng.choice([0, 1], n, p=[0.7, 0.3]),
        'latitude': rng.uniform(25.5, 25.8, n),
        'longitude': rng.uniform(84.9, 85.3, n),
    })


