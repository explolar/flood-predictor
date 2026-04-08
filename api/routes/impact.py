"""Impact assessment API — combines population, buildings, infrastructure, and crop loss."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, SARRequest

router = APIRouter(prefix="/impact", tags=["Impact"])


class ImpactRequest(SARRequest):
    """Impact assessment request — SAR params + toggles for each module."""
    include_population: bool = True
    include_buildings: bool = True
    include_infrastructure: bool = True
    include_crop_loss: bool = True
    crop_type: str = "Rice"
    crop_price: float = 100.0


@router.post("/assessment", response_model=AnalysisResponse)
async def impact_assessment(request: ImpactRequest):
    """Run combined impact assessment using SAR flood mask."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        # Step 1: Get base flood detection for the flood mask
        from gee_functions.sar import get_all_sar_data

        sar_result = await asyncio.to_thread(
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
        flood_area_ha = sar_result.get("area_ha", 0)

        impact = {
            "flood_area_ha": flood_area_ha,
            "flood_url": sar_result.get("flood_url"),
            "severity_url": sar_result.get("severity_url"),
        }

        # Step 2: Run sub-modules concurrently
        tasks = {}

        if request.include_population:
            async def get_pop():
                from gee_functions.population import get_displacement_estimate
                return await asyncio.to_thread(get_displacement_estimate, aoi_json)
            tasks["population"] = get_pop()

        if request.include_buildings:
            async def get_buildings():
                from gee_functions.buildings import get_building_damage
                return await asyncio.to_thread(
                    get_building_damage,
                    aoi_json,
                    request.f_start, request.f_end,
                    request.p_start, request.p_end,
                    request.threshold, request.polarization, request.speckle,
                )
            tasks["buildings"] = get_buildings()

        if request.include_infrastructure:
            async def get_infra():
                from gee_functions.infrastructure import get_osm_infrastructure, get_osm_roads, get_dam_data
                facilities = await asyncio.to_thread(get_osm_infrastructure, aoi_json)
                roads_data = await asyncio.to_thread(get_osm_roads, aoi_json)
                dams = await asyncio.to_thread(get_dam_data, aoi_json)
                roads_summary = None
                if roads_data:
                    total_km = sum(roads_data.get("km_by_type", {}).values())
                    roads_summary = {
                        "total_km": round(total_km, 1),
                        "km_by_type": roads_data.get("km_by_type", {}),
                    }
                return {
                    "facilities": facilities or [],
                    "roads": roads_summary,
                    "dams": [
                        {"name": d["name"], "river": d["river"], "capacity_mcm": d["capacity_mcm"]}
                        for d in (dams or [])[:10]
                    ],
                }
            tasks["infrastructure"] = get_infra()

        if request.include_crop_loss:
            async def get_crops():
                from gee_functions.sar import get_crop_loss_data
                return await asyncio.to_thread(
                    get_crop_loss_data,
                    aoi_json,
                    request.f_start, request.f_end,
                    request.p_start, request.p_end,
                    request.threshold, request.polarization,
                    request.crop_type, request.crop_price,
                )
            tasks["crop_loss"] = get_crops()

        # Gather all sub-results
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), gathered):
                if isinstance(result, Exception):
                    impact[key] = {"error": str(result)}
                elif result is not None:
                    impact[key] = result

        return AnalysisResponse(success=True, data=impact)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
