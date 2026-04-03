"""Multi-year comparison API routes."""

import asyncio
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.dependencies import aoi_to_json, initialize_ee_api

router = APIRouter(prefix="/multiyear", tags=["Multi-Year"])


class MultiyearRequest(BaseModel):
    geojson: dict
    years: List[int] = Field(default=[2019, 2020, 2021, 2022, 2023, 2024])
    polarization: str = Field("VH", pattern="^(VH|VV)$")
    threshold: float = Field(3.0, ge=0.5, le=6.0)


@router.post("/comparison")
async def multiyear_comparison(request: MultiyearRequest):
    """Compare flood extents across multiple years."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.multiyear import get_multiyear_flood_comparison

        result = await asyncio.to_thread(
            get_multiyear_flood_comparison, aoi_json, request.years, request.polarization, request.threshold
        )
        return {"success": True, "data": result}
    except Exception as e:
        import logging

        logging.exception("Multiyear comparison failed")
        return {"success": False, "error": str(e)}
