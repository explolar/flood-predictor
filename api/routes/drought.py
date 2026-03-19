"""Drought analysis API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse

router = APIRouter(prefix="/drought", tags=["Drought"])


class DroughtRequest(BaseModel):
    geojson: dict
    year: int


@router.post("/analysis", response_model=AnalysisResponse)
async def drought_analysis(request: DroughtRequest):
    """Compute SPI and NDVI anomaly for a given year."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from gee_functions.drought import get_ndvi_anomaly, get_spi_index

        spi = get_spi_index(aoi_json, request.year)
        ndvi = get_ndvi_anomaly(aoi_json, request.year)
        return AnalysisResponse(
            success=True,
            data={
                "spi": {"tile_url": spi.get("tile_url"), "value": spi.get("value")},
                "ndvi_anomaly": {
                    "tile_url": ndvi.get("tile_url"),
                    "value": ndvi.get("value"),
                },
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
