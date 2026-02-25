# HydroRisk Atlas
### Flood Risk Intelligence Platform · IIT Kharagpur

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://flood-predictor-518484395506.asia-south1.run.app)
[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-GEE-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Live app →** https://flood-predictor-518484395506.asia-south1.run.app

A satellite-powered flood risk assessment dashboard built with **Google Earth Engine**, **Sentinel-1 SAR**, and **Streamlit**. Designed for rapid geospatial flood inundation mapping and multi-hazard risk analysis at 30 m resolution using freely available Earth observation data.

---

## Table of Contents

1. [Overview](#overview)
2. [Technical Architecture](#technical-architecture)
3. [Analytical Methodology](#analytical-methodology)
4. [Data Sources](#data-sources)
5. [Features](#features)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Docker / Cloud Run Deployment](#docker--cloud-run-deployment)
9. [Usage](#usage)
10. [Caching Strategy](#caching-strategy)
11. [Dependencies](#dependencies)
12. [Author](#author)
13. [License](#license)

---

## Overview

HydroRisk Atlas is a multi-module geospatial flood intelligence platform. Its core analytical pipeline covers:

- **Phase 1 — MCA Susceptibility:** Weighted multi-criteria analysis of land cover, terrain slope, and historical rainfall to produce a static flood susceptibility index.
- **Phase 2 — SAR Inundation:** Sentinel-1 SAR change-detection between a dry-season reference window and a user-defined post-event window to map active inundation extent with a 6-layer quality filter chain.
- **Flood Depth Estimation:** Per-pixel water depth derived from SRTM DEM and a water-surface elevation proxy (95th-percentile elevation of flooded pixels).
- **Crop Loss Assessment:** ESA WorldCover cropland mask × NDVI drop (Sentinel-2) with configurable price-per-hectare monetary valuation.
- **Flood Return Period:** Gumbel Type-I distribution fitted to 24 years of CHIRPS monsoon rainfall.
- **Flood Recession Tracking:** SAR flood extent at T+0, +12 d, +24 d, +36 d after the flood peak.
- **Historical Flood Frequency:** JRC Monthly Water History (1984–2021) aggregated per year.
- **Infrastructure & Road Risk:** OSM amenity points (hospitals, schools, police, fire) and road network with automated evacuation-route flagging.
- **Dam / Reservoir Context:** GRanD v1.3 dams within 150 km of the AOI.

All computation runs server-side on GEE; no raster data is downloaded to the client. Tile URLs returned by `getMapId()` are served directly from Google's tile infrastructure to the Folium map in the browser.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                       │
│  Sidebar controls  →  Session state  →  4-tab render engine    │
└────────────────────┬────────────────────────────────────────────┘
                     │ @st.cache_data (TTL 3600 s)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GEE Python Client Library                     │
│   ee.ImageCollection  ·  ee.Image  ·  ee.FeatureCollection     │
│   ee.Reducer  ·  ee.Geometry  ·  ee.Algorithms                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ getMapId() → tile URL strings
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Folium / Leaflet.js Maps                       │
│  TileLayer  ·  GeoJson  ·  DualMap  ·  L.control legends       │
│  Fullscreen  ·  MiniMap  ·  LayerControl  ·  st_folium         │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- GEE `Image` objects are not serializable, so `@st.cache_data` functions return **tile URL strings** (serializable) instead of Image objects. This avoids redundant GEE computation on every Streamlit rerun.
- EE initialization is wrapped in `@st.cache_resource` to create a singleton authenticated session shared across all users.
- Folium legends are injected as Leaflet `L.control` objects via JavaScript (not raw HTML divs), ensuring they persist inside the map container during fullscreen mode.
- The AOI geometry is serialized to a JSON string (`json.dumps(aoi.getInfo())`) to serve as a hashable cache key, then deserialized with `json.loads()` inside cached functions before passing to `ee.Geometry()`.

---

## Analytical Methodology

### Phase 1 — Multi-Criteria Analysis (MCA)

Each input layer is reclassified to a 1–5 integer hazard rank, then combined as a weighted sum:

```
Risk Score = (LULC_rank × w₁) + (Slope_rank × w₂) + (Rainfall_rank × w₃)
```

where w₁ + w₂ + w₃ = 100 % (user-adjustable; w₃ auto-computed as remainder).

**LULC reclassification** (ESA WorldCover v200):

| Class code | Land cover type | Hazard rank |
|:----------:|----------------|:-----------:|
| 10 | Trees | 1 |
| 20, 30 | Shrubland / Grassland | 2 |
| 40 | Cropland | 3 |
| 50 | Built-up | 5 |
| 60 | Bare / sparse | 4 |
| 80, 90 | Permanent water / Wetland | 5 |

**Slope reclassification** (SRTM 30 m):

| Slope range | Interpretation | Hazard rank |
|:-----------:|---------------|:-----------:|
| ≤ 2° | Flat floodplain | 5 |
| 2° – 20° | Gentle to moderate | interpolated |
| > 20° | Steep terrain | 1 |

**Rainfall reclassification** (CHIRPS annual cumulative, 2023):

| Cumulative rainfall | Hazard rank |
|:-------------------:|:-----------:|
| < 1860 mm | 1 |
| ≥ 1950 mm | 5 |

Final score is rounded to the nearest integer (1–5) to produce a discrete risk class.

---

### Phase 2 — SAR Change-Detection Flood Mapping

**Processing chain:**

```
S1 GRD (VH or VV)
    │
    ├── filterDate(pre_start, pre_end)  → median composite  → PRE image
    └── filterDate(post_start, post_end) → median composite → POST image
             │
             ▼  [optional] Lee speckle filter: focal_mean(radius=1, kernelType='square')
             │
             ▼  Change image: DIFF = PRE − POST
             │  (positive values = backscatter drop = open water / inundation)
             │
             ▼  Threshold: DIFF > T dB  →  raw flood candidates
             │
             ├── Filter 1 — Terrain guard: slope < 8°  (radar shadow removal, SRTM)
             ├── Filter 2 — Permanent water exclusion: JRC seasonality ≥ 10 months
             ├── Filter 3 — Historical flood gate: JRC occurrence ≥ 5 %  (crop false-positive suppression)
             ├── Filter 4 — Lowland restriction: elevation ≤ 40th percentile of AOI DEM
             ├── Filter 5 — Minimum patch: ≥ 56 connected pixels ≈ 5 ha at 30 m  (noise removal)
             └── Filter 6 — Morphological cleanup: focal_mode(40 m radius, circular kernel)
```

**SAR visualization parameters:**

| View | Band | min | max | Palette |
|------|------|-----|-----|---------|
| Raw backscatter | VH or VV | −25 dB | 0 dB | dark-navy → white |
| Change intensity | DIFF | −2 dB | 8 dB | dark-navy → cyan → white |
| Severity zones | classified | 1 | 3 | yellow → orange → red |

**Flood severity classification** uses DEM elevation percentiles within the AOI:

| Elevation zone | Severity class |
|---------------|:--------------:|
| ≤ 10th percentile | Deep (3) |
| 10th – 50th percentile | Moderate (2) |
| > 50th percentile | Shallow (1) |

---

### Flood Return Period — Gumbel Extreme Value Distribution

Annual monsoon rainfall totals (Jun–Oct) are extracted from CHIRPS for 2000–2023 using a server-side GEE `map()` operation (single `getInfo()` call for 24 years).

Gumbel Type-I parameters:

```
β  = σ × √6 / π
u  = μ − 0.5772 × β

x(T) = u − β × ln(−ln(1 − 1/T))
```

where μ = sample mean, σ = sample standard deviation, T = return period in years.

---

### NDVI Crop Damage Index

```
NDVI_pre  = (B8 − B4) / (B8 + B4)   [Sentinel-2 SR, pre-flood composite]
NDVI_post = (B8 − B4) / (B8 + B4)   [Sentinel-2 SR, post-flood composite]
Damage    = NDVI_pre − NDVI_post     [positive = vegetation loss]
```

Visualized on a green → yellow → red scale (min = −0.3, max = 0.5).

---

### Flood Progression (Multi-date)

Each month (Jun–Oct) of the selected year uses the Jan–Mar median composite of that year as the dry-season reference. A separate `get_month_sar_tile()` function (cached per month) performs the full change-detection chain and returns a tile URL for the selected month's flood extent.

---

### Flood Depth Estimation

Water depth per pixel is estimated from the SRTM DEM and the flood mask:

```
water_surface ≈ 95th-percentile elevation of flooded pixels  (ee.Reducer.percentile([95]))
depth_px      = water_surface − pixel_elevation  (clamped ≥ 0 m)
```

Output includes a depth raster tile (0–3 m palette), mean/max depth statistics, and a fixed-histogram (8 bins, 0–4 m in 0.5 m steps) computed server-side in a single `reduceRegion` call.

---

### Crop Loss Assessment

Damaged cropland is defined as agricultural pixels (ESA WorldCover class 40) where NDVI drops by more than a configurable threshold:

```
crop_mask  = ESA WorldCover == 40  (Cropland)
damaged    = (NDVI_pre − NDVI_post > threshold) AND crop_mask
damaged_ha = sum(damaged × pixelArea) / 10 000
loss_₹     = damaged_ha × price_per_ha
```

Supported crops and default prices (₹/ha): Rice 40 000, Wheat 35 000, Sugarcane 1 20 000, Cotton 60 000, Maize 30 000, Soybean 45 000, plus a user-defined Custom option.

---

### Historical Flood Frequency (JRC)

JRC Monthly Water History (`JRC/GSW1_4/MonthlyHistory`, 1984–2021) is used to count flood-active months per year. A single server-side `map()` operation iterates all 38 years; `aggregate_sum('w')` counts months where any AOI pixel showed detected water (class = 2). One `getInfo()` call retrieves all years.

---

### Flood Recession Tracker

Post-flood SAR images at four snapshots after the event end are computed using the same 6-filter flood mask pipeline:

| Snapshot | Window |
|:--------:|--------|
| T + 0 d  | flood end → +12 d |
| T + 12 d | +12 → +24 d |
| T + 24 d | +24 → +36 d |
| T + 36 d | +36 → +48 d |

Inundated area (ha) is computed at each snapshot using `ee.Image.pixelArea()`, giving a four-point recession curve.

---

## Data Sources

| Dataset | GEE Asset ID | Resolution | Use |
|---------|-------------|:----------:|-----|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 10 m | SAR backscatter, change detection, recession |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | 10 m | LULC classification, crop mask |
| SRTM DEM | `USGS/SRTMGL1_003` | 30 m | Slope, terrain masking, severity, flood depth |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | ~5.5 km | Rainfall time series, return period |
| JRC Global Surface Water | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Permanent water mask, occurrence gate |
| JRC Monthly Water History | `JRC/GSW1_4/MonthlyHistory` | 30 m | Historical flood frequency 1984–2021 |
| WorldPop 100m | `WorldPop/GP/100m/pop` | 100 m | Population exposure |
| Sentinel-2 SR (Harmonized) | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | NDVI damage, crop loss, true color |
| HydroSHEDS Basins L8 | `WWF/HydroSHEDS/v1/Basins/hybas_8` | vector | Watershed delineation |
| GRanD Dams v1.3 | `projects/sat-io/open-datasets/GRanD/GRAND_Dams_v1_3` | vector | Dam/reservoir context (150 km radius) |
| OSM via Overpass API | `https://overpass-api.de` | vector | Infrastructure points, road network |

---

## Features

### Tab 1 — MCA Susceptibility Map
- Weighted three-layer MCA (LULC + Slope + Rainfall) with interactive weight sliders
- AOI terrain statistics: area (km²), elevation min/max/mean, mean slope
- Optional layers: JRC Flood Frequency, Sentinel-2 True Color, HydroSHEDS Watershed boundaries
- Coordinate click picker (via `st_folium`) — clicked lat/lon shown as overlay pill
- GeoTIFF direct download via GEE `getDownloadUrl()`

### Tab 2 — SAR Inundation Detection
- Eight selectable map layers: Flood Mask, Severity Zones, Flood Depth, Pre-SAR, Post-SAR, Change Intensity, NDVI Damage, Crop Loss
- **Flood depth raster** — per-pixel depth (m) derived from DEM + water-surface percentile; mean/max stats and 8-bin depth histogram
- **Crop loss assessment** — damaged cropland area (ha), damage %, and estimated monetary loss (₹) with crop/price selector
- **Population exposure** — WorldPop 2020 sum within flood mask
- **Flood recession curve** — inundated area (ha) at T+0 / +12 / +24 / +36 days after flood end
- **Historical flood frequency** — JRC-derived bar chart of flood-active months per year (1984–2021)
- **Sentinel-2 true-color comparison** — side-by-side pre/post optical imagery
- **OSM infrastructure overlay** — hospitals, schools, fire stations, police (Overpass API)
- **Road network overlay** — classified by type (motorway → tertiary) with automated evacuation-route flagging and km-by-type breakdown
- **Dam / reservoir context** — GRanD v1.3 dams within 150 km, sorted by capacity (MCM)
- CHIRPS daily rainfall time series chart (AOI mean, `st.area_chart`)
- Gumbel flood return period table (2 / 5 / 10 / 25 / 50 / 100-year)

### Tab 3 — Dual-View SAR Comparison
- `folium.plugins.DualMap` synchronized side-by-side map
- Left panel: pre-flood SAR backscatter; right panel: post-flood SAR + flood mask overlay
- Rendered via `components.html()` for full DualMap compatibility

### Tab 4 — Flood Progression
- CHIRPS monthly rainfall bar chart (Jun–Oct) for selected year
- Per-month SAR flood mask (selectbox-driven, cached per month)
- Dry-season reference: Jan–Mar of the selected year
- Season-total and peak-month statistics

### Sidebar
- Place name geocoding (Nominatim) → auto-fill AOI bounding box
- Bounding box inputs or GeoJSON file upload
- MCA weight sliders (LULC %, Slope %; Rainfall % = 100 − sum)
- SAR date pickers: pre-flood and post-flood windows
- VH / VV polarization toggle
- Backscatter threshold slider (0.5 – 6.0 dB)
- Lee speckle filter checkbox
- Crop type + price-per-hectare selector for loss estimation
- Progression year selector (2019 – 2024)
- Plain-text technical report download (includes return-period table)
- PDF report download (fpdf2)

---

## Installation

```bash
git clone https://github.com/explolar/flood-predictor.git
cd flood-predictor
pip install -r requirements.txt
```

### Google Earth Engine Authentication

```bash
earthengine authenticate
```

A browser window will open for OAuth2 sign-in. Once complete, credentials are stored in `~/.config/earthengine/credentials`.

---

## Configuration

Open `app.py` and set your GEE Cloud Project ID on line:

```python
project_id = 'your-gee-project-id'
```

The project must have the **Earth Engine API** enabled in Google Cloud Console. On Compute Engine or Cloud Run the app will automatically use `ComputeEngineCredentials`; locally it uses the credentials written by `earthengine authenticate`.

---

## Docker / Cloud Run Deployment

A `Dockerfile` is included for containerised deployment (e.g. Google Cloud Run):

```bash
# Build image
docker build -t hydrorisk-atlas .

# Run locally
docker run -p 8080:8080 hydrorisk-atlas
```

On **Cloud Run**, mount your GEE credentials as a secret or rely on the attached service account — `ComputeEngineCredentials` are picked up automatically. The live demo runs at:

> https://flood-predictor-518484395506.asia-south1.run.app

---

## Usage

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

**Typical workflow:**

1. Enter a place name (e.g. `Patna, Bihar`) and click **SEARCH & SET AOI**, or manually enter bounding box coordinates and click **INITIALIZE AOI**.
2. Adjust MCA weights in the sidebar. The Rainfall weight auto-computes as `100 − LULC% − Slope%`.
3. Set pre-flood and post-flood date windows for SAR analysis.
4. Choose VH or VV polarization and set the backscatter change threshold.
5. Switch between tabs to explore susceptibility, inundation, dual-view comparison, and monthly progression.
6. Download the technical report or PDF from the sidebar.

---

## Caching Strategy

| Scope | Decorator | Key inputs | Notes |
|-------|-----------|-----------|-------|
| EE session | `@st.cache_resource` | — | Singleton across reruns |
| MCA tile URL | `@st.cache_data(ttl=3600)` | aoi_json, w_lulc, w_slope, w_rain | String output — serializable |
| SAR all tiles + stats | `@st.cache_data(ttl=3600)` | aoi_json, dates, threshold, polar, speckle | All outputs serializable |
| NDVI tile URL | `@st.cache_data(ttl=3600)` | aoi_json, pre/post dates | Computed only when selected |
| Flood depth tile + stats | `@st.cache_data(ttl=3600)` | aoi_json, dates, threshold, polar, speckle | Dict: tile_url, mean_depth, max_depth, histogram |
| Crop loss data | `@st.cache_data(ttl=3600)` | aoi_json, dates, price, ndvi_threshold | Dict: tile_url, damaged_ha, damage_pct, loss_estimate |
| AOI terrain stats | `@st.cache_data(ttl=3600)` | aoi_json | Dict of floats |
| CHIRPS time series | `@st.cache_data(ttl=3600)` | aoi_json, start, end | Pandas DataFrame |
| JRC / S2 / Watershed tiles | `@st.cache_data(ttl=3600)` | aoi_json | Computed only when selected |
| S2 pre/post RGB tiles | `@st.cache_data(ttl=3600)` | aoi_json, pre/post dates | Dict of two tile URLs |
| Return period | `@st.cache_data(ttl=7200)` | aoi_json | 24-yr batch GEE call |
| JRC flood history | `@st.cache_data(ttl=7200)` | aoi_json | 38-yr batch, single getInfo() |
| Progression stats | `@st.cache_data(ttl=7200)` | aoi_json, year | 5-month batch GEE call |
| Monthly SAR tile | `@st.cache_data(ttl=3600)` | aoi_json, year, month, params | Per-month cache key |
| Flood recession data | `@st.cache_data(ttl=3600)` | aoi_json, f_end, p_start, p_end, params | 4-snapshot SAR series |
| OSM infrastructure | `@st.cache_data(ttl=3600)` | aoi_json | Overpass API HTTP call |
| OSM road network | `@st.cache_data(ttl=3600)` | aoi_json | Roads + km-by-type + evacuation flags |
| Dam / reservoir data | `@st.cache_data(ttl=7200)` | aoi_json | GRanD FeatureCollection, 150 km buffer |

The AOI geometry is serialized to a JSON string for cache keying (`json.dumps(aoi.getInfo())`) and deserialized back to a dict inside each function (`json.loads(aoi_json)`) before passing to `ee.Geometry()`.

---

## Dependencies

Core (listed in `requirements.txt`):

```
streamlit
earthengine-api
folium
streamlit-folium
```

Optional extras used by the app (install manually if needed):

```
pandas             >= 2.0    # data manipulation
requests           >= 2.31   # Overpass API calls
geopy              >= 2.4    # place name geocoding
fpdf2              >= 2.7    # PDF report export
```

---

## Project Structure

```
flood-predictor/
├── app.py            # Single-file Streamlit application (~1800 lines)
├── requirements.txt  # Python dependencies
├── Dockerfile        # Container build for Cloud Run deployment
├── LICENSE           # MIT License
└── README.md
```

---

## Author

**Ankit Kumar**
Land and Water Resource Engineering,
 Department of Agricultural and Food Engineering, 
 Indian Institute of Technology Kharagpur

[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)

---

## License

MIT License — free to use and modify with attribution.
