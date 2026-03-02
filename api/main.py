"""
Feature 21: FastAPI wrapper for HydroRisk Atlas.
Provides REST API endpoints for programmatic access.

Usage:
    MODE=api uvicorn api.main:app --host 0.0.0.0 --port 8080
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import mca, sar, ml

app = FastAPI(
    title="HydroRisk Atlas API",
    description="REST API for SAR-based flood risk analysis using Google Earth Engine",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mca.router)
app.include_router(sar.router)
app.include_router(ml.router)


@app.get("/")
async def root():
    return {
        "service": "HydroRisk Atlas API",
        "version": "2.0.0",
        "endpoints": ["/mca/risk-map", "/mca/stats", "/sar/flood-detection",
                       "/ml/classify", "/ml/risk-prediction"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
