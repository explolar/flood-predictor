"""Climate projections API routes."""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse

router = APIRouter(prefix="/projections", tags=["Projections"])


class ProjectionsRequest(BaseModel):
    geojson: dict
    scenario: str = "ssp245"
    model: str = "GFDL-ESM4"
    start_year: int = 2030
    end_year: int = 2050


@router.post("/analysis", response_model=AnalysisResponse)
async def projections_analysis(request: ProjectionsRequest):
    """Run CMIP6 climate projections."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.cmip6 import get_cmip6_projections

        result = await asyncio.to_thread(
            get_cmip6_projections, aoi_json, request.scenario, request.model, request.start_year, request.end_year
        )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
