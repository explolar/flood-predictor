"""Forecast API routes."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse

router = APIRouter(prefix="/forecast", tags=["Forecast"])


class ForecastRequest(BaseModel):
    geojson: dict
    forecast_days: Optional[int] = 5


@router.post("/weather", response_model=AnalysisResponse)
async def forecast_weather(request: ForecastRequest):
    """Get GFS weather forecast data."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.gfs_forecast import get_gfs_forecast

        result = await asyncio.to_thread(get_gfs_forecast, aoi_json, request.forecast_days)
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
