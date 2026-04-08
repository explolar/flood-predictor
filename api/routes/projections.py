"""Climate projections API routes."""

import asyncio
from typing import Optional

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


class ScenarioComparisonRequest(BaseModel):
    geojson: dict
    model: str = "ACCESS-CM2"
    periods: Optional[list] = None


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
        if result is None:
            return AnalysisResponse(success=True, data={"message": "No CMIP6 data available for this region/period"})
        return AnalysisResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenario-comparison", response_model=AnalysisResponse)
async def scenario_comparison(request: ScenarioComparisonRequest):
    """Compare SSP245 vs SSP585 across multiple time periods."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.cmip6 import get_cmip6_scenario_comparison

        result = await asyncio.to_thread(
            get_cmip6_scenario_comparison, aoi_json, request.model, request.periods
        )
        if result is None:
            return AnalysisResponse(success=True, data={"message": "No CMIP6 data available", "comparison": []})
        # Convert DataFrame to JSON-safe records
        df = result.get("comparison_df")
        records = df.to_dict(orient="records") if df is not None and hasattr(df, "to_dict") else []
        return AnalysisResponse(success=True, data={"comparison": records, "model": result.get("model")})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
