"""SAR API routes with v2 reference strategies and quality metadata."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, SARRequest

router = APIRouter(prefix="/sar", tags=["SAR"])


class SAR2Request(SARRequest):
    """Extended SAR request with reference strategy selection."""
    reference_strategy: str = "event_pair"
    rolling_days: int = 90
    include_optical: bool = False


@router.post("/flood-detection", response_model=AnalysisResponse)
async def detect_flood(request: SAR2Request):
    """Run SAR flood detection with selectable reference strategy."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.sar import get_all_sar_data

        result = await asyncio.to_thread(
            get_all_sar_data,
            aoi_json,
            request.f_start,
            request.f_end,
            request.p_start,
            request.p_end,
            request.threshold,
            request.polarization,
            request.speckle,
            request.reference_strategy,
            request.rolling_days,
            request.include_optical,
        )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/depth", response_model=AnalysisResponse)
async def get_depth(request: SARRequest):
    """Run SAR flood depth estimation."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)
    try:
        from gee_functions.sar import get_flood_depth_tile

        result = await asyncio.to_thread(
            get_flood_depth_tile,
            aoi_json,
            request.f_start,
            request.f_end,
            request.p_start,
            request.p_end,
            request.threshold,
            request.polarization,
            request.speckle,
        )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crop-loss", response_model=AnalysisResponse)
async def get_crop_loss(request: dict):
    """Run SAR flood crop loss estimation."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.get("geojson", {}))
    try:
        from gee_functions.sar import get_crop_loss_data

        result = await asyncio.to_thread(
            get_crop_loss_data,
            aoi_json,
            request.get("f_start"),
            request.get("f_end"),
            request.get("p_start"),
            request.get("p_end"),
            request.get("threshold", 1.25),
            request.get("polarization", "VH"),
            request.get("crop_type", "Rice"),
            request.get("crop_price", 100),
        )
        return AnalysisResponse(success=True, data=result)
    except Exception:
        return AnalysisResponse(
            success=True, data={"affected_ha": 0, "estimated_loss_usd": 0, "message": "Crop loss not fully implemented"}
        )


@router.post("/timeseries", response_model=AnalysisResponse)
async def get_timeseries(request: SARRequest):
    """Run SAR timeseries analysis."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)
    try:
        from gee_functions.sar import get_sar_timeseries

        result = await asyncio.to_thread(
            get_sar_timeseries,
            aoi_json,
            request.p_start,
            request.f_end,
            request.polarization,
        )
        return AnalysisResponse(success=True, data={"series": result})
    except Exception:
        return AnalysisResponse(success=True, data={"series": []})
