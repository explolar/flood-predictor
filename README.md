# HydroRisk Atlas

Satellite-powered flood risk intelligence platform built with FastAPI, React, and Google Earth Engine.

HydroRisk Atlas combines geospatial processing, machine learning, and climate analytics to deliver flood susceptibility mapping, SAR flood detection, drought monitoring, hydrology workflows, climate projections, and short-term weather forecast insights — all from a single web application.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Machine Learning Models](#machine-learning-models)
- [Data Sources](#data-sources)
- [Scientific Methodology & Physics](#scientific-methodology--physics)
- [Testing and Linting](#testing-and-linting)
- [CI/CD Pipeline](#cicd-pipeline)
- [Caching Strategy](#caching-strategy)
- [Notes](#notes)
- [License](#license)

---

## Features

### Multi-Criteria Flood Susceptibility (MCA)

Weighted overlay of land use/land cover (ESA WorldCover), terrain slope (SRTM DEM), and annual rainfall (CHIRPS) to produce a 5-class flood susceptibility map. Users can adjust weights interactively (default: 40 % LULC, 30 % slope, 30 % rainfall) and view AOI terrain summary statistics.

### SAR Flood Detection

Sentinel-1 pre-/post-flood change detection using VH or VV polarization with a 6-layer calibrated flood mask:

1. Terrain slope < 8° (removes radar shadow false positives)
2. Permanent water exclusion (JRC seasonality >= 10 months)
3. JRC flood frequency gate (occurrence >= 5 %)
4. Elevation <= 40th percentile (lowlands only)
5. Minimum patch >= 56 pixels (~5 ha)
6. Morphological cleanup (focal mode 40 m)

Outputs include flood extent area, 3-class severity map, affected population estimate, and configurable threshold (0.5–6.0 dB) with optional speckle filtering.

### Machine Learning Classification & Risk Prediction

- **Gradient Boosting** — pixel-wise flood/non-flood classification from SAR + terrain features.
- **Random Forest** — 5-class flood risk prediction from terrain and climate features.
- **XGBoost & LightGBM** — alternative classifiers for comparative analysis.
- **Ensemble Stacker** — meta-learner combining Gradient Boosting + XGBoost predictions.
- **LSTM Flood Forecaster** — 7–14 day flood probability from ERA5/GFS time-series (optional, requires PyTorch).
- **Foundation Models** — optional integration with Prithvi-EO-2.0 (NASA/IBM), Clay Foundation, ClimaX (Microsoft), and Pangu-Weather (Huawei) for advanced flood segmentation and weather forecasting. Gracefully falls back to GBM if unavailable.
- **Explainability** — SHAP-based feature importance for all models.

### Spectral Indices

Sentinel-2 derived indices (NDVI, NDBI, NDMI, NDWI, MNDWI) with configurable date range and cloud threshold. Generates comparison tile layers on the map.

### Drought Monitoring

- **SPI (Standardized Precipitation Index)** from a 20-year CHIRPS baseline.
- **NDVI Anomaly** from MODIS, categorized as Normal, Stressed, or Severe.
- 8-category drought classification from Extremely Dry to Extremely Wet.

### Hydrology & Watershed Analysis

Stream delineation, flow accumulation, and watershed boundary mapping from SRTM DEM. Optionally estimates flood depth and identifies buildings, roads, and infrastructure within flood zones.

### Weather & Flood Forecast

GFS-based weather forecast integration with 5–14 day look-ahead for precipitation and temperature predictions.

### Multi-Year Flood Comparison

Track SAR flood extents across 2019–2024 with temporal trend analysis, time-series charts, and per-year tile overlays.

### Climate Projections

CMIP6 model outputs (e.g. GFDL-ESM4) under SSP scenarios (245, 370, 585) for 2030–2050+ precipitation and temperature projections.

### Population & Infrastructure Exposure

WorldPop population exposure estimates and Microsoft building footprint analysis within detected flood zones. Includes crop loss estimation with commodity pricing.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 19, TypeScript, Vite, Leaflet, react-leaflet, Recharts, TanStack Query, Axios, Lucide React |
| **Backend** | FastAPI, Uvicorn, Pydantic, httpx |
| **Geospatial** | Google Earth Engine Python API |
| **ML / AI** | scikit-learn, XGBoost, LightGBM, Optuna, SHAP, joblib |
| **Optional ML** | PyTorch, Transformers, Hugging Face Hub (foundation models & LSTM forecaster) |
| **Infrastructure** | Docker (multi-stage), docker-compose, nginx, GitHub Actions, Google Cloud Run |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     Client Browser                    │
│              React + Leaflet + Recharts               │
└──────────────────┬───────────────────────────────────┘
                   │  HTTP (JSON)
┌──────────────────▼───────────────────────────────────┐
│                 nginx (port 8080)                      │
│         SPA fallback · gzip · asset caching           │
│         /api/* → proxy to uvicorn :8000               │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│            FastAPI / Uvicorn (port 8000)               │
│      Routes · Schemas · Dependency Injection          │
├───────────┬───────────┬───────────┬──────────────────┤
│ gee_func/ │ ml_models/│  utils/   │  External APIs   │
│  GEE API  │ sklearn   │ cache     │  Nominatim       │
│  Sentinel │ XGBoost   │ logging   │  OpenMeteo       │
│  CHIRPS   │ LightGBM  │ AOI val.  │                  │
│  ERA5     │ Ensemble  │           │                  │
│  CMIP6    │ SHAP      │           │                  │
└───────────┴───────────┴───────────┴──────────────────┘
```

---

## Repository Layout

```text
flood-predictor/
├── api/                          # FastAPI application
│   ├── main.py                   #   App init, CORS, lifespan
│   ├── schemas.py                #   Pydantic request/response models
│   ├── dependencies.py           #   EE initialization & shared utilities
│   └── routes/                   #   Endpoint modules
│       ├── mca.py                #     Multi-Criteria Assessment
│       ├── sar.py                #     SAR flood detection
│       ├── ml.py                 #     ML classification & prediction
│       ├── indices.py            #     Spectral indices
│       ├── drought.py            #     Drought monitoring
│       ├── forecast.py           #     Weather forecasting
│       ├── hydrology.py          #     Watershed analysis
│       ├── multiyear.py          #     Multi-year comparison
│       ├── projections.py        #     CMIP6 climate projections
│       └── geocode.py            #     Nominatim geocoding proxy
├── gee_functions/                # Google Earth Engine processing
│   ├── core.py                   #   EE init & AOI statistics
│   ├── sar.py                    #   SAR flood detection logic
│   ├── mca.py                    #   Multi-criteria analysis
│   ├── drought.py                #   Drought indices (SPI, NDVI)
│   ├── indices.py                #   Spectral indices (NDVI, NDBI, etc.)
│   ├── hydrology.py              #   Watershed & stream analysis
│   ├── watershed.py              #   Flow accumulation & delineation
│   ├── cmip6.py                  #   CMIP6 climate projections
│   ├── era5.py                   #   ERA5 reanalysis data
│   ├── chirps.py                 #   CHIRPS rainfall data
│   ├── gfs_forecast.py           #   GFS weather forecast
│   ├── population.py             #   WorldPop population exposure
│   ├── buildings.py              #   Building infrastructure analysis
│   ├── crop.py                   #   Crop loss estimation
│   └── multiyear.py              #   Multi-year flood comparison
├── ml_models/                    # ML model inference & training
│   ├── flood_risk_model.py       #   Random Forest (5-class risk)
│   ├── sar_classifier.py         #   Gradient Boosting SAR classifier
│   ├── xgb_classifier.py         #   XGBoost flood classifier
│   ├── lgbm_classifier.py        #   LightGBM classifier
│   ├── ensemble_stacker.py       #   Ensemble meta-learner
│   ├── flood_forecaster.py       #   LSTM flood forecaster (PyTorch)
│   ├── foundation_models.py      #   Prithvi, Clay, ClimaX, Pangu
│   ├── data_extraction.py        #   GEE feature extraction pipeline
│   ├── automl_tuner.py           #   Optuna hyperparameter tuning
│   ├── explainability.py         #   SHAP feature importance
│   └── anomaly_detector.py       #   Anomaly detection
├── training/                     # Offline model training scripts
│   ├── train_flood_risk.py       #   Train RF risk model
│   ├── train_sar_classifier.py   #   Train GB SAR classifier
│   ├── train_xgb_classifier.py   #   Train XGBoost
│   ├── train_lgbm_classifier.py  #   Train LightGBM
│   └── tune_hyperparams.py       #   Hyperparameter optimization
├── utils/                        # Shared utilities
│   ├── cache.py                  #   TTL caching (cachetools)
│   ├── logging_config.py         #   Logging setup
│   ├── aoi_validation.py         #   AOI geometry validation
│   └── alerts.py                 #   Alert system
├── tests/                        # Pytest suite
│   ├── test_ml_models.py         #   ML model tests
│   ├── test_ui_components.py     #   UI component tests
│   ├── test_utils.py             #   Utility tests
│   └── conftest.py               #   Fixtures & configuration
├── frontend/                     # React + TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx               #   Main app component
│   │   ├── api/                  #   Axios client & endpoint functions
│   │   ├── components/           #   Layout, Map, Common UI
│   │   ├── pages/                #   Tab views (Risk, SAR, Drought, etc.)
│   │   ├── hooks/                #   Custom React hooks
│   │   ├── types/                #   TypeScript interfaces
│   │   └── assets/               #   Static images & icons
│   ├── package.json
│   └── Dockerfile                #   Frontend build stage
├── .github/workflows/
│   ├── ci.yml                    #   Lint, test, Docker build
│   └── deploy.yml                #   Google Cloud Run deployment
├── Dockerfile                    # Production multi-stage build
├── docker-compose.yml            # Local multi-service orchestration
├── nginx.conf                    # Reverse proxy & SPA fallback
├── start.sh                      # Container startup (uvicorn + nginx)
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Ruff linting configuration
├── pytest.ini                    # Pytest configuration
└── LICENSE                       # MIT License
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 20+** and **npm 10+**
- **Google Earth Engine** access (authenticated account)
- **Docker Desktop** (optional, for containerized deployment)

---

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/flood-predictor.git
cd flood-predictor
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Authenticate Earth Engine

```bash
earthengine authenticate
```

### 4. Start the backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`. Visit `http://localhost:8080/docs` for the interactive Swagger UI.

### 5. Start the frontend (new terminal)

```bash
cd frontend
npm install
```

**PowerShell:**

```powershell
$env:VITE_API_URL='http://localhost:8080'; npm run dev
```

**Bash / Zsh:**

```bash
VITE_API_URL=http://localhost:8080 npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`).

---

## Docker Deployment

### Option A — Full production image

Builds a single Docker image with the React frontend served by nginx and the FastAPI backend proxied through it.

```bash
docker build -t hydrorisk-atlas .
docker run -p 8080:8080 -e GEE_PROJECT=your-gee-project hydrorisk-atlas
```

**What happens inside the container:**

1. **Stage 1 (Node 20-alpine):** Builds the React app with Vite.
2. **Stage 2 (Python 3.10-slim):** Installs Python dependencies, copies the backend code and the compiled frontend.
3. **Runtime:** `start.sh` launches Uvicorn (4 workers, port 8000) and nginx (port 8080) as a reverse proxy.

nginx serves static assets with 1-year cache headers, applies gzip compression, and proxies `/api/*` requests to Uvicorn with a 120-second read timeout for long-running GEE computations.

### Option B — docker-compose (split services)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | `http://localhost:3000` |
| API | `http://localhost:8080` |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GEE_PROJECT` | `xward-481405` | Google Earth Engine project ID used during initialization |
| `VITE_API_URL` | `""` | Frontend API base URL — set to `http://localhost:8080` for local development |
| `MODE` | *(unset)* | Container runtime mode (`MODE=api` in docker-compose for API-only service) |

---

## API Reference

**Base URL:** `http://localhost:8080`

All POST endpoints accept a JSON body containing a `geojson` field (GeoJSON geometry of the area of interest).

### General

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service metadata and advertised endpoint list |
| `/health` | GET | Health check — returns `{ "status": "ok" }` |
| `/geocode?q=<place>` | GET | Place name lookup via Nominatim proxy |

### Flood Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mca/risk-map` | POST | Generate a weighted flood susceptibility map (MCA) |
| `/mca/stats` | POST | Terrain and summary statistics for the AOI |
| `/sar/flood-detection` | POST | SAR-based flood extent and severity detection |
| `/ml/classify` | POST | ML flood classification (supports `gradient_boosting`, `xgboost`, `lightgbm`, `ensemble`) |
| `/ml/risk-prediction` | POST | 5-class flood risk prediction with Random Forest |
| `/multiyear/comparison` | POST | Multi-year SAR flood extent comparison (2019–2024) |

### Environmental Indices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/indices/tiles` | POST | Sentinel-2 spectral index tile layers (NDVI, NDBI, NDMI, NDWI, MNDWI) |
| `/drought/analysis` | POST | Drought monitoring — SPI + NDVI anomaly analysis |

### Hydrology & Climate

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hydrology/analysis` | POST | Watershed delineation, flow accumulation, stream network |
| `/forecast/weather` | POST | GFS-based weather and flood forecast (5–14 day look-ahead) |
| `/projections/analysis` | POST | CMIP6 climate projection analysis (SSP 245/370/585) |

### Key Request Schemas

```
AOIRequest
├── geojson: dict          # GeoJSON geometry (required)
└── name: str | null       # Optional area name

MCARequest (extends AOIRequest)
├── w_lulc: int = 40       # LULC weight (0–100)
├── w_slope: int = 30      # Slope weight (0–100)
└── w_rain: int | null     # Rainfall weight (auto-calculated)

SARRequest (extends AOIRequest)
├── f_start: str           # Flood period start (YYYY-MM-DD)
├── f_end: str             # Flood period end (YYYY-MM-DD)
├── p_start: str           # Pre-flood period start
├── p_end: str             # Pre-flood period end
├── threshold: float = 3.0 # Change threshold (0.5–6.0 dB)
├── polarization: str = "VH"  # VH or VV
└── speckle: bool = true   # Apply speckle filtering

MLRequest (extends SARRequest)
├── model: str = "gradient_boosting"  # Model choice
└── return_probability: bool = false  # Return probabilities
```

---

## Machine Learning Models

### Trained Models

Models are trained offline and serialized to the `models/` directory (not tracked in git).

| Model | Algorithm | Task | Features |
|-------|-----------|------|----------|
| `flood_risk_rf.joblib` | Random Forest | 5-class flood risk | elevation, slope, rainfall, LULC, JRC occurrence/extent, optional ERA5 climate |
| `sar_classifier_gb.joblib` | Gradient Boosting | Flood / non-flood | pre/post SAR, SAR diff/ratio, elevation, slope, JRC occurrence/seasonality |
| `xgb_classifier.joblib` | XGBoost | Flood / non-flood | Same as SAR classifier |
| `lgbm_classifier.joblib` | LightGBM | Flood / non-flood | Same as SAR classifier |
| `ensemble_stacker.joblib` | Stacking meta-learner | Flood / non-flood | GB + XGBoost predictions |

### Training Pipeline

```bash
# Train individual models
python training/train_flood_risk.py
python training/train_sar_classifier.py
python training/train_xgb_classifier.py
python training/train_lgbm_classifier.py

# Hyperparameter optimization with Optuna
python training/tune_hyperparams.py
```

Training scripts extract features from GEE across multi-region samples, perform train/test splits with class balancing, and save serialized models along with metadata.

### Foundation Models (Optional)

| Model | Provider | Parameters | Use Case |
|-------|----------|------------|----------|
| Prithvi-EO-2.0 | NASA / IBM | 300M | Multi-sensor flood segmentation |
| Clay Foundation | Clay | 70M | S1 + S2 + DEM flood mapping |
| ClimaX | Microsoft | 100M | Climate downscaling |
| Pangu-Weather | Huawei | 256M | 7-day weather forecasting |

These require `torch`, `transformers`, and `huggingface-hub`. The system automatically falls back to Gradient Boosting if these packages are not installed.

---

## Data Sources

| Dataset | Provider | Resolution | Usage |
|---------|----------|------------|-------|
| Sentinel-1 SAR | ESA / Copernicus | 10 m | Flood detection (VH/VV backscatter) |
| Sentinel-2 MSI | ESA / Copernicus | 10 m | Spectral indices (NDVI, NDWI, etc.) |
| SRTM DEM | NASA | 30 m | Elevation, slope, watershed analysis |
| CHIRPS | UCSB | 5 km | Precipitation (SPI, rainfall weights) |
| ERA5 | ECMWF | 31 km | Climate reanalysis (precip, runoff, soil moisture, temperature) |
| GFS | NOAA | 0.25° | Weather forecast (5–14 day) |
| CMIP6 | Various GCMs | Variable | Climate projections (SSP scenarios) |
| JRC Global Surface Water | EC-JRC | 30 m | Water occurrence, seasonality, flood frequency |
| ESA WorldCover | ESA | 10 m | Land use / land cover classification |
| MODIS | NASA | 250 m–1 km | NDVI anomaly for drought monitoring |
| WorldPop | WorldPop | 100 m | Population exposure estimates |
| Microsoft Buildings | Microsoft | Vector | Building footprint analysis in flood zones |

All geospatial datasets are accessed through the Google Earth Engine API — no local data downloads required.

---

## Scientific Methodology & Physics

This section documents the mathematical formulas, physical principles, classification thresholds, and algorithmic details underpinning each analysis module.

---

### SAR Backscatter Physics & Flood Detection

Synthetic Aperture Radar (SAR) measures microwave backscatter from the Earth's surface. Water surfaces act as specular reflectors — the radar pulse bounces away from the sensor — producing a characteristic drop in backscatter intensity (measured in decibels). The platform exploits this physical property for flood detection.

**Change Detection Formula:**

```
ΔSAR = SAR_pre − SAR_post   (in dB)
Flood pixel: ΔSAR > threshold
```

where `threshold` is user-configurable (default 3.0 dB, range 0.5–6.0 dB). A positive difference indicates backscatter decreased between the pre-flood and post-flood periods, consistent with water inundation.

**Speckle Filtering:**

SAR images contain multiplicative speckle noise inherent to coherent imaging systems. The platform applies a focal mean filter with a 1-pixel radius square kernel to both pre- and post-flood composites, smoothing noise while preserving spatial structure.

**Six-Layer Calibrated Flood Mask:**

Each layer addresses a known source of false positives in SAR flood mapping:

| Layer | Filter | Threshold | Physical Rationale |
|-------|--------|-----------|-------------------|
| 1 | Terrain slope | < 8° | Steep slopes cause radar shadow (dark returns that mimic water). SRTM DEM at 30 m. |
| 2 | Permanent water | JRC seasonality >= 10 months | Excludes lakes, reservoirs, and perennial rivers that are always dark in SAR. |
| 3 | Flood frequency gate | JRC occurrence >= 5% | Areas with < 5% historical water presence are unlikely flood zones; filters cropland false positives. |
| 4 | Elevation | <= 40th percentile within AOI | Floods concentrate in topographic lows. Computed dynamically via `ee.Reducer.percentile([40])`. |
| 5 | Connected pixel count | >= 56 pixels | Removes isolated noise patches. At 30 m resolution: 56 × 900 m² = 50,400 m² ≈ 5.04 ha minimum flood patch. |
| 6 | Morphological cleanup | `focal_mode(40 m, circle)` | Majority filter fills small holes and smooths boundaries for cartographic quality. |

**Flood Severity Classification:**

Severity is derived from the elevation distribution within the AOI:

```
p10 = 10th percentile elevation (from DEM)
p50 = 50th percentile elevation (median)

Severity 3 (High):     elevation <= p10   — deepest inundation zones
Severity 2 (Moderate): p10 < elevation <= p50
Severity 1 (Low):      elevation > p50    — shallow fringe flooding
```

**Water Depth Estimation:**

```
Water surface elevation = 95th percentile of DEM within flooded pixels
Depth = max(water_surface − DEM, 0)   (clamped >= 0, in meters)
```

The 95th percentile serves as a proxy for the water surface plane. Depth is binned into 8 classes over 0–4 m (0.5 m bin width) for visualization.

**Flooded Area Calculation:**

```
Area (ha) = Σ(flood_mask × pixel_area) / 10,000
```

Computed at 50 m scale using `ee.Image.pixelArea()` (projection-aware, accounts for Mercator distortion).

---

### Multi-Criteria Analysis (MCA) — Weighted Linear Combination

The flood susceptibility score combines three reclassified layers using a weighted linear combination:

```
Risk = (slope_r × w_slope/100) + (lulc_r × w_lulc/100) + (rain_r × w_rain/100)
```

**Default Weights:** LULC = 40%, Slope = 30%, Rainfall = 30%

**Slope Reclassification (SRTM DEM):**

Slope is computed via `ee.Terrain.slope(dem)` (gradient in degrees) and reclassified to a 1–5 risk scale:

```
Slope > 20°  →  Risk = 1 (very low)    — steep terrain sheds water quickly
Slope <= 2°  →  Risk = 5 (very high)   — flat terrain pools water
2° < slope <= 20°: linearly interpolated
```

Physical basis: steeper gradients produce faster overland flow and less ponding; flat areas accumulate runoff.

**LULC Reclassification (ESA WorldCover v200, 10 m):**

| WorldCover Class | Code | Risk Score | Rationale |
|-----------------|------|------------|-----------|
| Tree cover (closed) | 10 | 1 | High infiltration, canopy interception |
| Shrubland | 20 | 2 | Moderate infiltration |
| Herbaceous vegetation | 30 | 2 | Moderate infiltration |
| Herbaceous wetland | 40 | 3 | Naturally saturated soils |
| Moss and lichen | 50 | 5 | Thin soil, low absorption |
| Sparse vegetation | 60 | 4 | Low interception, exposed soil |
| Permanent water | 80 | 5 | Already inundated |
| Built-up (impervious) | 90 | 5 | Zero infiltration, maximum runoff |

**Rainfall Reclassification (CHIRPS Annual Total):**

```
< 1860 mm/yr  →  Risk = 1 (dry climate)
>= 1950 mm/yr →  Risk = 5 (extreme rainfall regime)
1860–1950 mm/yr: linearly interpolated
```

Thresholds are calibrated from 2023 annual totals across South Asian study regions.

---

### Spectral Index Band Math

All indices are computed from Sentinel-2 Level-2A surface reflectance. Cloud masking removes pixels with Scene Classification Layer (SCL) values 3 (cloud shadow), 8 (medium-probability cloud), 9 (high-probability cloud), and 10 (thin cirrus). The median of up to 40 least-cloudy scenes is used as the composite.

**NDVI — Normalized Difference Vegetation Index** (Tucker, 1979)

```
NDVI = (B8 − B4) / (B8 + B4)
       NIR (842 nm) − Red (665 nm)
Range: [−0.2, 0.8]
```

Chlorophyll in healthy vegetation strongly absorbs red light and reflects NIR. High NDVI indicates dense, photosynthetically active canopy.

| NDVI Range | Class |
|-----------|-------|
| <= 0.00 | Water / Non-vegetated |
| 0.00–0.20 | Barren / Urban |
| 0.20–0.40 | Sparse vegetation |
| 0.40–0.60 | Moderate vegetation |
| 0.60–1.00 | Dense vegetation |

**NDWI — Normalized Difference Water Index** (McFeeters, 1996)

```
NDWI = (B3 − B8) / (B3 + B8)
       Green (560 nm) − NIR (842 nm)
Range: [−0.5, 0.5]
```

Water absorbs NIR strongly, producing positive NDWI. Canonical water/non-water boundary at NDWI = 0; high-confidence water at > 0.3.

| NDWI Range | Class |
|-----------|-------|
| <= −0.20 | Non-water (dry) |
| −0.20–0.00 | Non-water (moist) |
| 0.00–0.20 | Potential wet area |
| 0.20–0.40 | Shallow / turbid water |
| 0.40–1.00 | Open water |

**MNDWI — Modified Normalized Difference Water Index** (Xu, 2006)

```
MNDWI = (B3 − B11) / (B3 + B11)
        Green (560 nm) − SWIR1 (1610 nm)
Range: [−0.5, 0.7]
```

Replaces NIR with SWIR1 to suppress built-up land noise. Water boundary at MNDWI > 0 (used in JRC Global Surface Water products). High-confidence water at > 0.3.

**NDBI — Normalized Difference Built-Up Index** (Zha et al., 2003)

```
NDBI = (B11 − B8) / (B11 + B8)
       SWIR1 (1610 nm) − NIR (842 nm)
Range: [−0.5, 0.5]
```

Impervious surfaces reflect more SWIR than NIR. Positive NDBI indicates built-up / paved areas — a key flood risk factor due to zero infiltration.

**NDMI — Normalized Difference Moisture Index**

```
NDMI = (B8 − B11) / (B8 + B11)
       NIR (842 nm) − SWIR1 (1610 nm)
Range: [−1.0, 1.0]
```

Measures vegetation water content. High NDMI indicates wet canopy/soil; low NDMI indicates water stress.

**SAVI — Soil-Adjusted Vegetation Index** (Huete, 1988)

```
SAVI = 1.5 × (B8 − B4) / (B8 + B4 + L)
where L = 0.5 (soil brightness correction factor)
```

Reduces soil background reflectance effects in arid/semi-arid regions. The coefficient 1.5 is an empirical scaling to match the NDVI value range.

**EVI — Enhanced Vegetation Index** (Huete et al., 2002)

```
EVI = 2.5 × (B8 − B4) / (B8 + C1×B4 − C2×B2 + L)
where C1 = 6.0, C2 = 7.5, L = 1.0
```

Incorporates the blue band (B2, 490 nm) for atmospheric aerosol resistance and reduces saturation in dense canopies. Coefficients are derived from MODIS calibration studies.

**BSI — Bare Soil Index** (Rikimaru et al., 2002)

```
BSI = ((B11 + B4) − (B8 + B2)) / ((B11 + B4) + (B8 + B2))
Range: [−0.5, 0.5]
```

Highlights bare, eroded, and degraded soil surfaces. High BSI indicates soil vulnerability to erosion and increased surface runoff — directly linked to higher flood peak discharge.

---

### Drought Monitoring — SPI & NDVI Anomaly

**Standardized Precipitation Index (SPI):**

The SPI quantifies precipitation anomalies relative to a long-term climatological baseline, following WMO standard methodology:

```
SPI = (P_target − μ) / σ
where:
  P_target = annual rainfall for the target year
  μ        = mean annual rainfall over the baseline period
  σ        = standard deviation over the baseline period
```

Default configuration: 20-year baseline (e.g., 2004–2024 for target year 2024). Division by zero is prevented by clamping σ >= 1 mm.

**SPI Classification (WMO Standard):**

| SPI Value | Category | Probability |
|-----------|----------|-------------|
| >= 2.0 | Extremely Wet | 2.3% tail |
| 1.5 to 2.0 | Severely Wet | 6.7% tail |
| 1.0 to 1.5 | Moderately Wet | 15.9% tail |
| −1.0 to 1.0 | Near Normal | Central 68.3% |
| −1.5 to −1.0 | Moderately Dry | 15.9% tail |
| −2.0 to −1.5 | Severely Dry | 6.7% tail |
| <= −2.0 | Extremely Dry | 2.3% tail |

Data source: CHIRPS daily (5 km resolution), aggregated to annual totals.

**NDVI Anomaly (MODIS):**

```
Anomaly = (NDVI_target − NDVI_baseline_mean) / 10000
```

Division by 10,000 accounts for MODIS NDVI scaling factor (raw values stored as integers × 10,000). Baseline is the 20-year MODIS mean from MOD13A2 (~1 km resolution).

| Anomaly | Interpretation |
|---------|---------------|
| < −0.10 | Significant vegetation stress (drought indicator) |
| −0.10 to −0.03 | Mild vegetation stress |
| −0.03 to 0.03 | Near-normal vegetation |
| >= 0.03 | Above-normal vegetation (wet conditions) |

Physical basis: NDVI measures chlorophyll content via the NIR/Red reflectance ratio. Negative anomalies indicate reduced photosynthetic activity due to water stress.

---

### Hydrology & Watershed Analysis

**Flow Accumulation (D8 Algorithm):**

Source: WWF HydroSHEDS 15-arc-second flow accumulation grid (~450 m). Each cell value represents the number of upstream cells draining through it, computed using the D8 (deterministic eight-neighbor) flow routing algorithm on the SRTM DEM.

**Stream Network Delineation:**

```
streams = flow_accumulation > stream_threshold
Default threshold = 100 pixels ≈ 45 km² upstream contributing area
```

This threshold captures perennial streams while excluding ephemeral rills and first-order headwaters.

**Stream Order (Strahler Approximation):**

True Strahler stream ordering requires junction analysis. The platform uses a log10-binning approximation of flow accumulation as a computationally efficient proxy:

```
log_acc = log10(max(flow_acc, 1))

Order 1: 2 <= log_acc < 3    (100–1K pixels, ~45–450 km²)
Order 2: 3 <= log_acc < 4    (1K–10K pixels)
Order 3: 4 <= log_acc < 5    (10K–100K pixels)
Order 4: 5 <= log_acc < 6    (100K–1M pixels)
Order 5: log_acc >= 6        (> 1M pixels, major rivers)
```

**Drainage Density:**

```
Local:  D_d = Σ(stream_pixels in 1500 m radius) × pixel_length / circle_area
Scalar: D_d = total_stream_length (km) / AOI_area (km²)
```

Typical range: 0.5–3.0 km/km². Higher drainage density indicates more dissected terrain with faster runoff response.

**HAND — Height Above Nearest Drainage:**

HAND quantifies each pixel's vertical distance above the nearest stream channel, a key indicator of flood susceptibility. The algorithm uses iterative focal minimum propagation:

1. **Identify drainage pixels:** Cells where `flow_acc > threshold`
2. **Extract drainage elevation:** DEM values at drainage cells
3. **Propagate elevation outward** via iterative focal minimum operations with increasing radii `[3, 5, 10, 20, 30, 40]` pixels (~1.8 km total reach):

```python
for radius in [3, 5, 10, 20, 30, 40]:
    filled = drainage_elev.focal_min(radius, "circle", "pixels")
    drainage_elev = drainage_elev.unmask(filled)
```

4. **Compute HAND:**

```
HAND = max(DEM − nearest_drainage_elevation, 0)
```

Physical interpretation: low HAND values (< 5 m) indicate valley bottoms and floodplains with high inundation probability. High HAND values indicate upland areas unlikely to flood.

**Flood Extent from HAND:**

```
Inundation mask: HAND <= flood_depth (m)
Depth at pixel:  max(flood_depth − HAND, 0)
```

**Basin Statistics:** Derived from HydroSHEDS Level-8 basins (WWF/HydroSHEDS/v1/Basins/hybas_8), reporting sub-basin area, upstream contributing area, and mean elevation per basin.

---

### Rainfall Return Period Analysis (Gumbel Distribution)

Extreme rainfall frequency is estimated by fitting a Gumbel (Type I Extreme Value) distribution to annual monsoon (June–October) rainfall totals from CHIRPS over 20+ years.

**Gumbel Parameter Estimation (Method of Moments):**

```
β = σ × √6 / π            (scale parameter)
u = μ − 0.5772 × β        (location parameter; 0.5772 = Euler–Mascheroni constant)
```

**Return Period Quantile:**

```
x_T = u − β × ln(−ln(1 − 1/T))
```

where T is the return period in years. Standard return periods computed:

| Return Period (T) | Annual Exceedance Probability | Interpretation |
|-------------------|-------------------------------|---------------|
| 2 years | 50% | Median annual flood |
| 5 years | 20% | Moderate event |
| 10 years | 10% | Significant event |
| 25 years | 4% | Major event |
| 50 years | 2% | Severe event |
| 100 years | 1% | Extreme / design event |

---

### Weather Forecasting (GFS)

Source: NOAA Global Forecast System at 0.25° (~28 km) resolution, providing 7–16 day forecasts.

**Unit Conversions:**

```
Precipitation:  mm/hr = precip_rate (kg m⁻² s⁻¹) × 3600
                mm/day = mm/hr × 24
Temperature:    °C = K − 273.15
Wind speed:     m/s = √(u² + v²)   (from u/v wind components)
```

**Flood Alert Thresholds:**

When return period data is available:

```
weekly_factor = 7 / 150 (empirical scaling: 7-day forecast window / seasonal total)

EXTREME: 7-day total >= RP100 × weekly_factor
SEVERE:  7-day total >= RP25 × weekly_factor
WARNING: 7-day total >= RP10 × weekly_factor
WATCH:   7-day total >= RP5 × weekly_factor
```

Fallback thresholds (without return period data):

| Alert Level | Max Daily Precipitation |
|-------------|------------------------|
| EXTREME | > 150 mm/day |
| SEVERE | > 100 mm/day |
| WARNING | > 60 mm/day |
| WATCH | > 30 mm/day |
| NORMAL | <= 30 mm/day |

---

### Climate Projections (CMIP6)

Source: NASA NEX-GDDP-CMIP6 (downscaled to ~25 km resolution, 2015–2100).

**Available Global Climate Models (GCMs):**

| Model | Institution |
|-------|------------|
| ACCESS-CM2 | CSIRO / Bureau of Meteorology, Australia |
| GFDL-ESM4 | NOAA GFDL, USA |
| MRI-ESM2-0 | Meteorological Research Institute, Japan |
| UKESM1-0-LL | Met Office Hadley Centre, UK |
| IPSL-CM6A-LR | Institut Pierre-Simon Laplace, France |
| MPI-ESM1-2-HR | Max Planck Institute, Germany |

**Shared Socioeconomic Pathways (SSPs):**

| Scenario | Radiative Forcing (2100) | Description |
|----------|-------------------------|-------------|
| SSP245 | ~2.4 W/m² | Moderate mitigation, intermediate emissions |
| SSP585 | ~8.5 W/m² | High emissions, fossil-fuel intensive development |

**Precipitation Conversion:**

```
mm/day = pr (kg m⁻² s⁻¹) × 86400
Annual total (mm) = daily mean × 365.25
```

**Temperature Conversion:**

```
°C = tasmax (K) − 273.15
```

**Precipitation Change Calculation:**

```
Δ% = ((P_future − P_baseline) / P_baseline) × 100
Baseline period: 2015–2025
Future periods: 2030–2050, 2050–2070, 2070–2100
```

**Multi-Model Ensemble for Future Flood Risk:**

The platform predicts future flood risk by replacing current CHIRPS rainfall with CMIP6-projected rainfall while holding elevation, slope, LULC, and JRC features static. Predictions are run independently on 4+ GCMs, and the final risk class is determined by majority voting (mode) across models. A risk delta map (future risk − current risk) highlights areas of increasing or decreasing flood susceptibility.

---

### Population & Infrastructure Exposure

**Population (WorldPop, 100 m resolution):**

```
Population exposed = Σ(population_raster × flood_mask)
Displaced estimate = population_exposed × 0.70
```

The 70% displacement rate is an empirical estimate based on observed evacuation rates in flood events. Age-disaggregated estimates use WorldPop age/sex bands:

- Children (< 15 years): sum of M_0–M_14 + F_0–F_14
- Elderly (>= 60 years): sum of M_60–M_80 + F_60–F_80

**Crop Damage Assessment:**

```
ΔNDVI = NDVI_pre − NDVI_post
Damaged = (ΔNDVI > 0.10) AND (pixel = ESA WorldCover crop class 40)
Damaged area (ha) = Σ(damaged_pixels × pixel_area) / 10,000
Economic loss = damaged_ha × crop_price_per_ha
```

A 10% NDVI decline threshold identifies significant vegetation loss consistent with flood damage to agricultural crops.

---

### ML Model Architectures & Hyperparameters

**Random Forest — Flood Risk (5-class):**

```
n_estimators   = 200 trees
max_depth      = 15
min_samples_leaf = 10
class_weight   = "balanced" (inverse-frequency weighting)
oob_score      = True (out-of-bag generalization estimate)

Features (6 base + 5 optional ERA5):
  Base:     elevation, slope, annual_rainfall, lulc_class, jrc_occurrence, jrc_max_extent
  ERA5:     era5_annual_precip, era5_annual_runoff, era5_mean_sm_shallow, era5_mean_sm_deep, era5_mean_temp

Target: risk_class derived from JRC occurrence
  Class 1: jrc_occurrence < 5%
  Class 2: 5% <= jrc < 20%
  Class 3: 20% <= jrc < 40%
  Class 4: 40% <= jrc < 70%
  Class 5: jrc >= 70%

Training: 5,000 stratified samples (1,000 per class) at 100 m scale
```

**Gradient Boosting — SAR Classification (binary):**

```
n_estimators   = 200 boosting rounds
max_depth      = 6
learning_rate  = 0.1
subsample      = 0.8
min_samples_leaf = 20

Features (8):
  pre_sar, post_sar, sar_diff, sar_ratio, elevation, slope, jrc_occurrence, jrc_seasonality

Target: flood_label (1 = flood, 0 = non-flood) from threshold-based SAR detection
Training: 4,000 stratified samples (~2,000 per class) at 30 m scale
```

**XGBoost Classifier:**

```
n_estimators    = 200
max_depth       = 6
learning_rate   = 0.08
subsample       = 0.8
colsample_bytree = 0.8
```

**Ensemble Stacker (Two-Level Architecture):**

```
Level 0 (Base Learners):
  - Gradient Boosting → P(flood | features)
  - XGBoost → P(flood | features)

Level 1 (Meta-Learner):
  - Logistic Regression
  - Input: [GB_probability, XGB_probability, threshold_label]
  - Output: final flood probability
```

The meta-learner learns the optimal weighting of base model predictions through calibrated probabilities.

**LSTM Flood Forecaster (PyTorch):**

```
Architecture:
  LSTM(input_size=5, hidden_size=64, num_layers=2, dropout=0.2)
  → Linear(64, 32) → ReLU → Dropout(0.2)
  → Linear(32, 1) → Sigmoid

Input:  30-day sequence of [precipitation, temperature, soil_moisture, runoff, humidity]
Output: Daily flood probability (0–1) for next 7–14 days
Loss:   Binary Cross-Entropy
Optimizer: Adam (lr=0.001), 50 epochs

Flood labels (training): 95th percentile precip AND 90th percentile soil moisture

Risk levels:
  HIGH:    probability >= 0.7
  MODERATE: 0.4–0.7
  LOW:     0.2–0.4
  MINIMAL: < 0.2

Fallback (no PyTorch): GradientBoostingClassifier with 7-day and 3-day rolling window features
  (mean, max, sum) for each of the 5 input variables → 20 engineered features
```

**SHAP Explainability:**

Uses `shap.TreeExplainer` for all tree-based models. Computes mean absolute SHAP values per feature to rank flood risk drivers. Generates summary bar charts and per-pixel spatial SHAP maps encoded as base64 PNG for web display.

---

### Physical Constants & Thresholds Reference

| Parameter | Value | Unit | Source |
|-----------|-------|------|--------|
| SAR slope cutoff | 8 | degrees | Empirical — radar shadow removal |
| JRC seasonality gate | 10 | months | Empirical — permanent water |
| JRC occurrence gate | 5 | % | Empirical — cropland false positive filter |
| Elevation percentile | 40 | % | Empirical — lowland restriction |
| Min flood patch | 56 | pixels (~5 ha) | Empirical — noise removal |
| Focal mode radius | 40 | meters | Empirical — morphological cleanup |
| SAVI L factor | 0.5 | unitless | Huete (1988) |
| EVI C1 (red) | 6.0 | unitless | Huete et al. (2002) |
| EVI C2 (blue) | 7.5 | unitless | Huete et al. (2002) |
| Euler–Mascheroni constant | 0.5772 | unitless | Mathematical constant (Gumbel) |
| ERA5 precip conversion | × 86,400 | s/day | kg m⁻² s⁻¹ → mm/day |
| CMIP6 temp conversion | − 273.15 | K → °C | Kelvin to Celsius |
| Displacement rate | 0.70 | fraction | Empirical — 70% evacuation |
| Crop NDVI damage threshold | 0.10 | ΔNDVI | Empirical — 10% decline |
| CHIRPS resolution | 5 | km | UCSB-CHG native |
| ERA5-Land resolution | 11 | km | ECMWF native |
| GFS resolution | 28 | km | NOAA (0.25°) |
| CMIP6 resolution | 25 | km | NASA NEX-GDDP |
| Cache TTL | 3,600 | seconds | 1-hour default |
| GFS max forecast horizon | 384 | hours | 16-day limit |

---

### References

1. Tucker, C.J. (1979). Red and photographic infrared linear combinations for monitoring vegetation. *Remote Sensing of Environment*, 8(2), 127–150.
2. McFeeters, S.K. (1996). The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. *International Journal of Remote Sensing*, 17(7), 1425–1432.
3. Xu, H. (2006). Modification of normalised difference water index (NDWI) to enhance open water features in remotely sensed imagery. *International Journal of Remote Sensing*, 27(14), 3025–3033.
4. Huete, A.R. (1988). A soil-adjusted vegetation index (SAVI). *Remote Sensing of Environment*, 25(3), 295–309.
5. Huete, A.R. et al. (2002). Overview of the radiometric and biophysical performance of the MODIS vegetation indices. *Remote Sensing of Environment*, 83(1–2), 195–213.
6. Zha, Y., Gao, J., & Ni, S. (2003). Use of normalized difference built-up index in automatically mapping urban areas from TM imagery. *International Journal of Remote Sensing*, 24(3), 583–594.
7. Rikimaru, A., Roy, P.S., & Miyatake, S. (2002). Tropical forest cover density mapping. *Tropical Ecology*, 43(1), 39–47.

---

## Testing and Linting

### Linting

```bash
# Check for errors
ruff check .

# Check formatting
ruff format --check .
```

Configured in `pyproject.toml` with Python 3.10 target, 120-character line length, and E/F/W/I rule sets.

### Testing

```bash
# Run fast tests (no GEE connectivity required)
pytest -m "not slow" --tb=short -q

# Run full suite including slow GEE-dependent tests
pytest -m slow
```

Test modules:

- `tests/test_ml_models.py` — ML model inference and training pipelines
- `tests/test_ui_components.py` — UI constants and visualization palettes
- `tests/test_utils.py` — Caching, AOI validation, and logging utilities

---

## CI/CD Pipeline

### `ci.yml` — Continuous Integration

Triggers on push and pull requests to `main` and `develop`.

1. **Lint** — Ruff format check and import sorting.
2. **Test** — Pytest with mocked GEE (no live connectivity required).
3. **Build** — Docker image build verification (no push).

### `deploy.yml` — Deployment

Triggers on tag push matching `v*`.

1. Authenticates to Google Cloud with service account credentials.
2. Builds and pushes Docker image to GCP Artifact Registry.
3. Deploys to **Google Cloud Run** with:
   - 2 vCPUs, 2 GiB memory
   - Min instances: 0, Max instances: 3
   - Unauthenticated access enabled

---

## Caching Strategy

The backend uses TTL-based caching (via `cachetools`) to avoid redundant GEE computations.

| Scope | TTL | Max Entries | Fallback |
|-------|-----|-------------|----------|
| GEE tile results | 3600 s (1 hr) | 512 | `functools.lru_cache(256)` |
| EE initialization | 86400 s (24 hr) | Singleton | — |

Cached functions include: AOI stats, MCA tiles, SAR flood data, drought indices, spectral indices, and hydrology outputs.

---

## Notes

- **CORS** is configured to allow all origins (`*`) for development convenience.
- **Geocoding** uses OpenStreetMap Nominatim via the backend and requires outbound internet access.
- Some advanced ML/foundation-model functionality is optional and degrades gracefully if extra packages (`torch`, `transformers`, `huggingface-hub`) are not installed.
- The platform works globally — no hard-coded regional restrictions.
- **Read timeout** for GEE-backed endpoints is 120 seconds via nginx to accommodate complex computations.

---

## License

MIT License. See [LICENSE](LICENSE).
