"""Advanced analysis modes — optical fusion, batch AOI, alert watchpoints."""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, SARRequest

router = APIRouter(prefix="/advanced", tags=["Advanced"])


# ── Optical + SAR Fusion ──

class FusionRequest(SARRequest):
    cloud_thresh: int = 40
    fusion_weight: float = 0.5


@router.post("/fusion", response_model=AnalysisResponse)
async def optical_sar_fusion(request: FusionRequest):
    """Run optical+SAR fused flood detection."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.fusion import get_fused_flood_mask

        result = await asyncio.to_thread(
            get_fused_flood_mask,
            aoi_json,
            request.f_start, request.f_end,
            request.p_start, request.p_end,
            request.threshold, request.polarization, request.speckle,
            request.cloud_thresh, request.fusion_weight,
        )
        if result is None:
            return AnalysisResponse(
                success=True,
                data={"message": "Optical data unavailable (too cloudy). Use SAR-only mode."},
            )
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Batch AOI Execution ──

class BatchAOIRequest(BaseModel):
    aois: List[dict]  # List of {name, geojson, ...params}
    analysis_type: str = "sar"  # sar, impact, hydrology


@router.post("/batch", response_model=AnalysisResponse)
async def batch_aoi_execution(request: BatchAOIRequest):
    """Execute analysis across multiple AOIs in parallel."""
    initialize_ee_api()

    if len(request.aois) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 AOIs per batch request")

    async def run_single(aoi_spec: dict):
        aoi_json = aoi_to_json(aoi_spec.get("geojson", {}))
        name = aoi_spec.get("name", "unnamed")
        try:
            if request.analysis_type == "sar":
                from gee_functions.sar import get_all_sar_data
                result = await asyncio.to_thread(
                    get_all_sar_data, aoi_json,
                    aoi_spec.get("f_start", "2024-07-01"),
                    aoi_spec.get("f_end", "2024-08-01"),
                    aoi_spec.get("p_start", "2024-01-01"),
                    aoi_spec.get("p_end", "2024-03-31"),
                    aoi_spec.get("threshold", 3.0),
                    aoi_spec.get("polarization", "VH"),
                    aoi_spec.get("speckle", True),
                )
                return {"name": name, "status": "success", "area_ha": result.get("area_ha", 0)}
            elif request.analysis_type == "hydrology":
                from gee_functions.watershed import get_all_hydrology_data
                result = await asyncio.to_thread(
                    get_all_hydrology_data, aoi_json, aoi_spec.get("stream_threshold", 100),
                )
                return {"name": name, "status": "success", "stream_length_km": result.get("stream_length_km", 0)}
            else:
                return {"name": name, "status": "error", "message": f"Unknown analysis type: {request.analysis_type}"}
        except Exception as e:
            return {"name": name, "status": "error", "message": str(e)}

    results = await asyncio.gather(*[run_single(aoi) for aoi in request.aois])
    return AnalysisResponse(success=True, data={"results": list(results), "count": len(results)})


# ── Alert / Watchpoint ──

class WatchpointRequest(BaseModel):
    geojson: dict
    name: str
    alert_threshold_ha: float = 100.0
    check_interval_days: int = 12  # Sentinel-1 revisit
    polarization: str = "VH"
    threshold: float = 3.0


@router.post("/watchpoint/check", response_model=AnalysisResponse)
async def check_watchpoint(request: WatchpointRequest):
    """Check a monitored location for recent flood activity.

    Compares the latest 12-day S1 window against the prior 90-day baseline.
    """
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        import datetime
        from gee_functions.sar import get_all_sar_data

        today = datetime.date.today()
        f_end = today.isoformat()
        f_start = (today - datetime.timedelta(days=request.check_interval_days)).isoformat()
        p_end = (today - datetime.timedelta(days=request.check_interval_days + 1)).isoformat()
        p_start = (today - datetime.timedelta(days=request.check_interval_days + 90)).isoformat()

        result = await asyncio.to_thread(
            get_all_sar_data,
            aoi_json, f_start, f_end, p_start, p_end,
            request.threshold, request.polarization, True,
            "rolling_baseline", 90, False,
        )

        area_ha = result.get("area_ha", 0)
        alert_triggered = area_ha >= request.alert_threshold_ha

        return AnalysisResponse(success=True, data={
            "name": request.name,
            "checked_at": today.isoformat(),
            "flood_area_ha": area_ha,
            "alert_threshold_ha": request.alert_threshold_ha,
            "alert_triggered": alert_triggered,
            "quality": result.get("quality"),
            "flood_url": result.get("flood_url"),
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
