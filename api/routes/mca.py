"""MCA API routes."""

from fastapi import APIRouter, HTTPException
from api.schemas import MCARequest, AnalysisResponse
from api.dependencies import initialize_ee_api, aoi_to_json

router = APIRouter(prefix="/mca", tags=["MCA"])


@router.post("/risk-map", response_model=AnalysisResponse)
async def compute_mca(request: MCARequest):
    """Compute MCA flood risk map and return tile URL."""
    initialize_ee_api()

    w_rain = request.w_rain or max(0, 100 - request.w_lulc - request.w_slope)
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.mca import get_mca_tile
        tile_url = get_mca_tile(aoi_json, request.w_lulc, request.w_slope, w_rain)
        return AnalysisResponse(success=True, data={'tile_url': tile_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats", response_model=AnalysisResponse)
async def get_stats(request: MCARequest):
    """Get AOI terrain statistics."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.core import get_aoi_stats
        stats = get_aoi_stats(aoi_json)
        return AnalysisResponse(success=True, data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
