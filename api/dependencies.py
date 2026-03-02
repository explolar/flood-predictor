"""FastAPI dependencies and shared utilities."""

import ee
import json
import os

_ee_initialized = False


def initialize_ee_api():
    """Initialize Earth Engine for API context."""
    global _ee_initialized
    if _ee_initialized:
        return

    project_id = os.getenv('GEE_PROJECT', 'xward-481405')
    try:
        from ee import compute_engine
        creds = compute_engine.ComputeEngineCredentials()
        ee.Initialize(creds, project=project_id)
    except Exception:
        ee.Initialize(project=project_id)
    _ee_initialized = True


def aoi_to_json(geojson_dict):
    """Convert a GeoJSON dict to the JSON string format used by GEE functions."""
    return json.dumps(geojson_dict)
