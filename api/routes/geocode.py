"""Geocode API route — proxies Nominatim for the React frontend."""

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Geocode"])


@router.get("/geocode")
async def geocode(q: str):
    """Geocode a place name and return lat/lon."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q.strip(), "format": "json", "limit": 1},
            headers={"User-Agent": "HydroRiskAtlas/2.0"},
        )
        results = resp.json()

    if not results:
        raise HTTPException(status_code=404, detail=f'"{q}" not found')

    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "display_name": results[0]["display_name"],
    }
