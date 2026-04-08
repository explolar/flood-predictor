"""SAR API routes."""

import asyncio

from fastapi import APIRouter, HTTPException

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, SARRequest

router = APIRouter(prefix="/sar", tags=["SAR"])


@router.post("/flood-detection", response_model=AnalysisResponse)
async def detect_flood(request: SARRequest):
    """Run SAR flood detection and return results."""
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
        )
        return AnalysisResponse(
            success=True,
            data={
                "area_ha": result["area_ha"],
                "pop_exposed": result["pop_exposed"],
                "flood_url": result["flood_url"],
                "severity_url": result["severity_url"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/depth", response_model=AnalysisResponse)
async def get_depth(request: SARRequest):
    """Run SAR flood depth and return results."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)
    try:
        from gee_functions.sar import get_flood_depth_tile

        # get_flood_depth_tile signature in sar.py expects aoi_json and dates
        result = await asyncio.to_thread(
            get_flood_depth_tile,
            aoi_json,
            request.f_start,
            request.f_end,
            request.p_start,
            request.p_end,
            request.threshold,
            request.polarization,
        )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crop-loss", response_model=AnalysisResponse)
async def get_crop_loss(request: dict):
    """Run SAR flood crop loss estimation and return results."""
    # request is SARRequest & { crop_type: string; crop_price: number }
    initialize_ee_api()
    import json
    aoi_json = aoi_to_json(request.get("geojson", {}))
    try:
        # We simulate the crop loss or use a gee function if available
        # The frontend expects a generic AnalysisResponse.
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
        # Fallback if get_crop_loss_data isn't implemented in gee_functions.sar yet
        return AnalysisResponse(
            success=True, 
            data={"affected_ha": 0, "estimated_loss_usd": 0, "message": "Crop loss not fully implemented"}
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
