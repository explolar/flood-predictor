"""Curated historical flood AOIs and non-flood controls for validation.

Each entry contains:
  - name: human-readable identifier
  - geojson: GeoJSON Polygon geometry
  - f_start / f_end: flood event dates
  - p_start / p_end: pre-flood reference dates
  - is_flood: True for known flood, False for dry control
  - expected_area_ha: approximate ground-truth flooded area (None for controls)
  - source: provenance of the ground-truth label
"""

BENCHMARK_AOIS = [
    # ── Known flood events ──
    {
        "name": "Patna Bihar 2024 Monsoon",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[84.95, 25.50], [85.30, 25.50], [85.30, 25.70], [84.95, 25.70], [84.95, 25.50]]],
        },
        "f_start": "2024-08-01",
        "f_end": "2024-08-20",
        "p_start": "2024-04-01",
        "p_end": "2024-05-30",
        "is_flood": True,
        "expected_area_ha": 5000,
        "source": "NDMA / Sentinel-1 visual confirmation",
    },
    {
        "name": "Assam Brahmaputra 2023",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[91.50, 26.00], [91.90, 26.00], [91.90, 26.30], [91.50, 26.30], [91.50, 26.00]]],
        },
        "f_start": "2023-06-15",
        "f_end": "2023-07-15",
        "p_start": "2023-02-01",
        "p_end": "2023-04-30",
        "is_flood": True,
        "expected_area_ha": 8000,
        "source": "ASDMA / Copernicus EMS",
    },
    {
        "name": "Kerala 2018 Floods",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[76.10, 9.80], [76.50, 9.80], [76.50, 10.10], [76.10, 10.10], [76.10, 9.80]]],
        },
        "f_start": "2018-08-10",
        "f_end": "2018-08-25",
        "p_start": "2018-01-01",
        "p_end": "2018-03-31",
        "is_flood": True,
        "expected_area_ha": 12000,
        "source": "NRSC / Copernicus EMS EMSR299",
    },
    {
        "name": "Pakistan Sindh 2022",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[67.50, 26.50], [68.00, 26.50], [68.00, 27.00], [67.50, 27.00], [67.50, 26.50]]],
        },
        "f_start": "2022-08-20",
        "f_end": "2022-09-15",
        "p_start": "2022-03-01",
        "p_end": "2022-05-31",
        "is_flood": True,
        "expected_area_ha": 20000,
        "source": "UNOSAT / Copernicus EMS",
    },
    # ── Non-flood controls (dry season / no-event) ──
    {
        "name": "Control: Patna Dry Season",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[84.95, 25.50], [85.30, 25.50], [85.30, 25.70], [84.95, 25.70], [84.95, 25.50]]],
        },
        "f_start": "2024-02-01",
        "f_end": "2024-02-28",
        "p_start": "2023-11-01",
        "p_end": "2024-01-15",
        "is_flood": False,
        "expected_area_ha": 0,
        "source": "Dry season control — no reported flooding",
    },
    {
        "name": "Control: Rajasthan Desert",
        "geojson": {
            "type": "Polygon",
            "coordinates": [[[71.00, 26.50], [71.50, 26.50], [71.50, 27.00], [71.00, 27.00], [71.00, 26.50]]],
        },
        "f_start": "2023-08-01",
        "f_end": "2023-08-30",
        "p_start": "2023-03-01",
        "p_end": "2023-05-31",
        "is_flood": False,
        "expected_area_ha": 0,
        "source": "Arid zone control — no historical flooding",
    },
]
