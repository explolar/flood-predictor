"""AHP-MCDM flood susceptibility API routes."""

import asyncio
import json

from fastapi import APIRouter, HTTPException

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, MCARequest, AOIRequest

router = APIRouter(prefix="/mca", tags=["MCA"])


@router.post("/risk-map", response_model=AnalysisResponse)
async def compute_mca(request: MCARequest):
    """Compute AHP-MCDM flood susceptibility map with 10 conditioning factors.

    Returns composite tile URL, individual factor tile URLs, and AHP metadata
    (weights, CR, lambda_max, consistency status).
    """
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    custom_weights = None
    if request.method == "custom" and request.custom_weights:
        custom_weights = json.dumps(request.custom_weights)

    try:
        from gee_functions.mca import get_mca_tile

        result = await asyncio.to_thread(
            get_mca_tile, aoi_json, request.method, custom_weights
        )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ahp-weights", response_model=AnalysisResponse)
async def get_weights():
    """Return AHP weights and consistency metrics (no GEE call needed)."""
    try:
        from gee_functions.mca import compute_ahp_weights

        report = compute_ahp_weights()
        return AnalysisResponse(success=True, data=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/factor-stats", response_model=AnalysisResponse)
async def get_factor_statistics(request: AOIRequest):
    """Compute per-factor area distribution across risk classes 1-5."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.mca import get_factor_stats

        stats = await asyncio.to_thread(get_factor_stats, aoi_json)
        return AnalysisResponse(success=True, data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats", response_model=AnalysisResponse)
async def get_stats(request: MCARequest):
    """Get AOI terrain statistics."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.core import get_aoi_stats

        stats = await asyncio.to_thread(get_aoi_stats, aoi_json)
        return AnalysisResponse(success=True, data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
