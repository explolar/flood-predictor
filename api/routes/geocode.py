"""Geocode API route — proxies Nominatim for the React frontend."""

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Geocode"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "HydroRiskAtlas/2.0 (research; IIT Kharagpur)"


@router.get("/geocode")
async def geocode(q: str):
    """Geocode a place name and return lat/lon."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={"q": q.strip(), "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            )
            resp.raise_for_status()
            results = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Geocoding service timed out. Try again.")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot reach geocoding service. Check network.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Geocoding service returned {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)[:200]}")

    if not results:
        raise HTTPException(status_code=404, detail=f'"{q}" not found')

    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "display_name": results[0]["display_name"],
    }
