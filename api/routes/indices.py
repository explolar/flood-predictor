"""Spectral indices API routes."""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse

router = APIRouter(prefix="/indices", tags=["Indices"])


class IndicesRequest(BaseModel):
    geojson: dict
    date_start: str
    date_end: str
    cloud_thresh: int = Field(60, ge=10, le=100)


@router.post("/tiles", response_model=AnalysisResponse)
async def compute_indices(request: IndicesRequest):
    """Compute all spectral index tiles."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.indices import get_all_index_tiles

        tiles = await asyncio.to_thread(
            get_all_index_tiles, aoi_json, request.date_start, request.date_end, request.cloud_thresh
        )
        return AnalysisResponse(success=True, data={"indices": tiles})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
