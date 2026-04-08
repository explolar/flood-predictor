"""Forecast API routes — weather forecast + HAND-based inundation forecast."""

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


class InundationRequest(BaseModel):
    geojson: dict
    flood_depth_m: Optional[float] = 2.0
    stream_threshold: Optional[int] = 100
    forecast_days: Optional[int] = 7
    # Optional SAR params to include observed extent
    f_start: Optional[str] = None
    f_end: Optional[str] = None
    p_start: Optional[str] = None
    p_end: Optional[str] = None
    threshold: Optional[float] = 3.0
    polarization: Optional[str] = "VH"
    speckle: Optional[bool] = True


@router.post("/weather", response_model=AnalysisResponse)
async def forecast_weather(request: ForecastRequest):
    """Get GFS weather forecast data."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.gfs_forecast import get_gfs_forecast

        forecast_hours = (request.forecast_days or 5) * 24
        result = await asyncio.to_thread(get_gfs_forecast, aoi_json, forecast_hours)
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inundation", response_model=AnalysisResponse)
async def forecast_inundation(request: InundationRequest):
    """Generate HAND-based inundation forecast with optional SAR observed comparison.

    Combines:
    - HAND-based projected flood extent at given depth
    - GFS weather forecast (near-term rainfall trigger)
    - Discharge exceedance alert level
    - Optionally: observed SAR flood extent for comparison
    """
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        result = {}

        # Step 1: HAND-based inundation at the given flood depth
        from gee_functions.watershed import get_hand_data

        hand_result = await asyncio.to_thread(
            get_hand_data,
            aoi_json,
            request.stream_threshold or 100,
            request.flood_depth_m,
        )
        if hand_result:
            result["forecast_flood_url"] = hand_result.get("flood_url")
            result["forecast_depth_url"] = hand_result.get("depth_url")
            result["forecast_area_ha"] = hand_result.get("flood_area_ha")
            result["hand_stats"] = {
                "mean_hand_m": hand_result.get("mean_hand_m"),
                "p10_hand_m": hand_result.get("p10_hand_m"),
                "p50_hand_m": hand_result.get("p50_hand_m"),
                "p90_hand_m": hand_result.get("p90_hand_m"),
            }
            result["hand_url"] = hand_result.get("hand_url")
            result["flood_depth_m"] = request.flood_depth_m
            result["pct_inundated"] = hand_result.get("pct_inundated")

        # Step 2: Discharge exceedance forecast
        try:
            from gee_functions.glofas import get_flood_exceedance_forecast

            exceedance = await asyncio.to_thread(
                get_flood_exceedance_forecast, aoi_json, request.forecast_days or 7,
            )
            if exceedance:
                result["alert_level"] = exceedance.get("level")
                result["alert_color"] = exceedance.get("color")
                result["forecast_max_precip_mm"] = exceedance.get("forecast_max_precip_mm")
                result["exceedance_return_period"] = exceedance.get("exceedance_return_period")
                result["return_levels"] = exceedance.get("return_levels")
        except Exception:
            pass  # Non-critical — alert is best-effort

        # Step 3: Optional observed SAR extent for comparison
        if request.f_start and request.f_end and request.p_start and request.p_end:
            try:
                from gee_functions.sar import get_all_sar_data

                sar_result = await asyncio.to_thread(
                    get_all_sar_data,
                    aoi_json,
                    request.f_start, request.f_end,
                    request.p_start, request.p_end,
                    request.threshold or 3.0,
                    request.polarization or "VH",
                    request.speckle if request.speckle is not None else True,
                )
                result["observed_flood_url"] = sar_result.get("flood_url")
                result["observed_area_ha"] = sar_result.get("area_ha")
            except Exception:
                pass  # Non-critical — observed is optional

        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
