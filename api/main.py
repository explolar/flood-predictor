"""
Feature 21: FastAPI wrapper for HydroRisk Atlas.
Provides REST API endpoints for programmatic access.

Usage:
    MODE=api uvicorn api.main:app --host 0.0.0.0 --port 8080
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import (
    advanced,
    drought,
    forecast,
    geocode,
    hydrology,
    impact,
    indices,
    mca,
    ml,
    multiyear,
    projections,
    sar,
)

app = FastAPI(
    title="HydroRisk Atlas API",
    description="REST API for SAR-based flood risk analysis using Google Earth Engine",
    version="3.0.0",
)

_default_origins = ["http://localhost:5173", "http://localhost:3000"]
_extra = os.environ.get("ALLOWED_ORIGINS", "")
_allowed_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mca.router)
app.include_router(sar.router)
app.include_router(ml.router)
app.include_router(indices.router)
app.include_router(drought.router)
app.include_router(multiyear.router)
app.include_router(forecast.router)
app.include_router(projections.router)
app.include_router(hydrology.router)
app.include_router(impact.router)
app.include_router(advanced.router)
app.include_router(geocode.router)


@app.get("/api")
async def api_info():
    return {
        "service": "FluviaAI API",
        "version": "3.0.0",
        "endpoints": [
            "/mca/risk-map",
            "/mca/ahp-weights",
            "/mca/factor-stats",
            "/mca/stats",
            "/sar/flood-detection",
            "/ml/classify",
            "/ml/risk-prediction",
            "/indices/tiles",
            "/drought/analysis",
            "/multiyear/comparison",
            "/forecast/weather",
            "/projections/analysis",
            "/geocode",
            "/sar/depth",
            "/sar/crop-loss",
            "/sar/timeseries",
            "/projections/scenario-comparison",
            "/hydrology/analysis",
            "/impact/assessment",
            "/forecast/inundation",
            "/advanced/fusion",
            "/advanced/batch",
            "/advanced/watchpoint/check",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve static frontend in production (when /var/www/html exists from Docker build)
_static_dir = Path("/var/www/html")
if _static_dir.is_dir():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

    @app.get("/favicon.svg")
    async def favicon():
        return FileResponse(_static_dir / "favicon.svg")

    @app.get("/")
    async def serve_index():
        return FileResponse(_static_dir / "index.html")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = _static_dir / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_static_dir / "index.html")
