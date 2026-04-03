"""
Feature 21: FastAPI Pydantic schemas.
Request/response models for the REST API.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AOIRequest(BaseModel):
    """AOI definition for API requests."""

    geojson: Dict[str, Any] = Field(..., description="GeoJSON geometry")
    name: Optional[str] = None


class MCARequest(AOIRequest):
    """AHP-MCDM flood susceptibility parameters."""

    method: str = Field("ahp", pattern="^(ahp|custom)$", description="Weight method: ahp or custom")
    custom_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom factor weights (sum to 1.0). Keys: distance_to_river, rainfall, slope, elevation, drainage_density, twi, lulc, soil, ndvi, curvature",
    )

    # Legacy fields — kept for backward compatibility
    w_lulc: int = Field(40, ge=0, le=100)
    w_slope: int = Field(30, ge=0, le=100)
    w_rain: Optional[int] = None


class SARRequest(AOIRequest):
    """SAR analysis parameters."""

    f_start: str = Field(..., description="Flood start date YYYY-MM-DD")
    f_end: str = Field(..., description="Flood end date YYYY-MM-DD")
    p_start: str = Field(..., description="Pre-flood start date YYYY-MM-DD")
    p_end: str = Field(..., description="Pre-flood end date YYYY-MM-DD")
    threshold: float = Field(3.0, ge=0.5, le=6.0)
    polarization: str = Field("VH", pattern="^(VH|VV)$")
    speckle: bool = True


class MLRequest(SARRequest):
    """ML model parameters."""

    model: str = Field("gradient_boosting", description="Model type: gradient_boosting, xgboost, lightgbm, ensemble")
    return_probability: bool = False


class AnalysisResponse(BaseModel):
    """Standard analysis response."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TileResponse(BaseModel):
    """Response with tile URL."""

    tile_url: str
    metadata: Dict[str, Any] = {}
