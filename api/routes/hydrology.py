"""Hydrology API routes."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse

router = APIRouter(prefix="/hydrology", tags=["Hydrology"])


class HydrologyRequest(BaseModel):
    geojson: dict
    stream_threshold: Optional[int] = 500
    flood_depth: Optional[float] = None


@router.post("/analysis", response_model=AnalysisResponse)
async def hydrology_analysis(request: HydrologyRequest):
    """Run watershed and stream analysis."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.watershed import get_all_hydrology_data

        result = await asyncio.to_thread(get_all_hydrology_data, aoi_json, request.stream_threshold)
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
