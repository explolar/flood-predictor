"""SAR API routes."""

from fastapi import APIRouter, HTTPException
from api.schemas import SARRequest, AnalysisResponse
from api.dependencies import initialize_ee_api, aoi_to_json

router = APIRouter(prefix="/sar", tags=["SAR"])


@router.post("/flood-detection", response_model=AnalysisResponse)
async def detect_flood(request: SARRequest):
    """Run SAR flood detection and return results."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.sar import get_all_sar_data
        result = get_all_sar_data(
            aoi_json, request.f_start, request.f_end,
            request.p_start, request.p_end,
            request.threshold, request.polarization, request.speckle
        )
        return AnalysisResponse(success=True, data={
            'area_ha': result['area_ha'],
            'pop_exposed': result['pop_exposed'],
            'flood_url': result['flood_url'],
            'severity_url': result['severity_url'],
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
