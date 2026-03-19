# HydroRisk Atlas
### Satellite-Powered Flood Risk Intelligence | IIT Kharagpur

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-4f8ff7?style=for-the-badge&logo=google-cloud&logoColor=white)](https://flood-predictor-518484395506.asia-south1.run.app)
[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-GEE-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](https://opensource.org/licenses/MIT)

> Live app: https://flood-predictor-518484395506.asia-south1.run.app

HydroRisk Atlas is a modular flood intelligence platform built with **React + FastAPI** that combines Google Earth Engine geospatial analytics with machine learning, climate projections, and AI foundation models for flood susceptibility mapping, SAR-based inundation detection, weather forecasting, and hydrology workflows.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Tech Stack](#tech-stack)
3. [Quick Start](#quick-start)
4. [Application Modules](#application-modules)
5. [Core Methodology](#core-methodology)
6. [Machine Learning Stack](#machine-learning-stack)
7. [Foundation Models](#foundation-models)
8. [Data Sources](#data-sources)
9. [Project Structure](#project-structure)
10. [REST API](#rest-api)
11. [Deployment](#deployment)
12. [Keyboard Shortcuts](#keyboard-shortcuts)
13. [Dependencies](#dependencies)
14. [Author](#author)
15. [License](#license)

---

## What It Does

HydroRisk Atlas provides seven primary modules:

- **RISK**: Multi-Criteria Analysis (MCA) flood susceptibility and urban vulnerability mapping.
- **SAR**: Sentinel-1 flood detection, pre/post comparison, progression, depth, crop loss, and impact overlays.
- **ML Intelligence**: Random Forest risk mapping, SAR classifiers (GB/XGB/LGBM/Ensemble), SHAP analysis, anomaly detection.
- **CLIMATE**: Multi-year flood comparison, drought monitoring (SPI + NDVI anomaly), ERA5 historical climate, CMIP6 future projections (SSP245/SSP585), and future flood risk maps with multi-model ensemble.
- **INDICES**: Sentinel-2 spectral indices (NDVI/NDWI/MNDWI/NDBI/SAVI/EVI/BSI) with export tools.
- **HYDROLOGY**: Watershed delineation, stream extraction, terrain-flow analysis, and HAND (Height Above Nearest Drainage) flood simulation.
- **FORECAST**: NOAA GFS weather forecasts (7-16 day), LSTM/GBM flood probability prediction, GloFAS-style river discharge analysis, and AI foundation model classification (Prithvi-EO-2.0, Clay, ClimaX, Pangu-Weather).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Maps** | Leaflet + react-leaflet |
| **Charts** | Recharts |
| **State** | TanStack React Query |
| **Backend** | FastAPI + Uvicorn |
| **Geospatial** | Google Earth Engine (Python API) |
| **ML** | scikit-learn, XGBoost, LightGBM, PyTorch |
| **Cache** | cachetools (TTLCache) |
| **Proxy** | Nginx (gzip, static assets, API reverse proxy) |
| **Deployment** | Docker multi-stage + Google Cloud Run |
| **CI/CD** | GitHub Actions (lint + test + deploy on tags) |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/explolar/flood-predictor.git
cd flood-predictor
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
```

### 3. (Optional) Install advanced ML dependencies

```bash
pip install torch transformers huggingface-hub   # Foundation models + LSTM
```

Without these, the app falls back to scikit-learn GBM classifiers automatically.

### 4. Authenticate Earth Engine

```bash
earthengine authenticate
```

### 5. Run development servers

```bash
# Terminal 1: Backend
uvicorn api.main:app --host 0.0.0.0 --port 8080

# Terminal 2: Frontend
cd frontend
VITE_API_URL=http://localhost:8080 npm run dev
```

### 6. Run with Docker (production)

```bash
docker build -t hydrorisk-atlas .
docker run -p 8080:8080 hydrorisk-atlas
```

Or use docker-compose:

```bash
docker-compose up --build
```

---

## Application Modules

### RISK (MCA Susceptibility)

- Weighted MCA using LULC, slope, and rainfall layers.
- AOI terrain metrics and flood-frequency overlays.
- Urban Flood Vulnerability Index.

### SAR (Detection, Comparison, Progression)

- Flood mask, severity, depth, SAR change layers, and crop-loss estimation.
- Pre/post comparison with dual maps.
- Monthly progression (Jun-Oct) with rainfall trends.
- Optional overlays: population displacement, building damage, soil moisture, water quality.

### ML Intelligence (Classifiers, Analytics, Tools)

- Random Forest 5-class risk prediction (with optional ERA5 features).
- SAR classifiers: Gradient Boosting, XGBoost, LightGBM, ensemble stacking.
- SHAP-based feature explanation.
- Isolation Forest anomaly detection.
- Optuna hyperparameter tuning.

### CLIMATE (Projections + Drought)

- Multi-year flood trend comparison.
- Drought diagnostics using SPI and NDVI anomaly.
- ERA5-Land historical climate: annual temperature, precipitation, runoff, evapotranspiration, soil moisture, and monsoon profiles.
- CMIP6 future projections: NASA NEX-GDDP-CMIP6 under SSP245/SSP585 scenarios from 6 GCMs.
- Future flood risk maps: current vs. projected with multi-model ensemble.

### INDICES

- Seven Sentinel-2 indices at 10 m resolution.
- Interactive map overlays with threshold classes.

### HYDROLOGY

- HydroSHEDS basin hierarchy mapping (levels 6/8/10).
- Stream network extraction from flow accumulation.
- HAND (Height Above Nearest Drainage) flood simulation.

### FORECAST (Weather + Flood Prediction + AI Models)

- NOAA GFS 0.25-degree forecasts for 7-16 days.
- LSTM or GBM flood probability prediction.
- GloFAS-style discharge estimation with Gumbel return periods.
- AI Foundation Models: Prithvi-EO-2.0, Clay, ClimaX, Pangu-Weather.

---

## Core Methodology

### 1. Multi-Criteria Analysis (MCA)

```text
Risk Score = (LULC_rank x w1) + (Slope_rank x w2) + (Rainfall_rank x w3)
```

### 2. SAR Flood Detection

```text
Sentinel-1 pre/post composites -> DIFF = PRE - POST
-> Threshold > T dB
-> Quality filters (terrain, permanent water, lowland mask, patch-size, morphology)
```

### 3. Flood Depth Proxy

```text
water_surface ~ 95th percentile elevation of flooded pixels
depth = water_surface - pixel_elevation (clamped >= 0)
```

### 4. HAND (Height Above Nearest Drainage)

```text
Drainage network = flow_accumulation > threshold
HAND = pixel_elevation - nearest_drainage_elevation (>= 0)
Flood extent = pixels where HAND <= simulated_depth
```

### 5. Return Period Analysis

- CHIRPS monsoon series (~24 years) for rainfall.
- ERA5 runoff series (~20 years) for discharge.
- Gumbel Type-I fitting for 2/5/10/25/50/100-year return levels.

### 6. Flood Forecasting

```text
Training:   ERA5-Land daily (precip, temp, soil moisture, runoff) x 6 monsoon seasons
Labels:     flood = 1 if precip >= P95 AND soil_moisture >= P90
Model:      LSTM (2-layer, 64 hidden) or GBM with rolling-window features
Input:      30-day ERA5 history + 7-day GFS forecast
Output:     daily flood probability for next 7-14 days
```

---

## Machine Learning Stack

### Random Forest (Flood Risk)

- **Features**: elevation, slope, rainfall, LULC, JRC water metrics (+ optional ERA5).
- **Target**: 5 risk classes derived from water occurrence.

### SAR Classifiers (GB / XGB / LGBM / Ensemble)

- **Features**: pre/post SAR, difference, ratio, elevation, slope, JRC indicators.
- **Target**: binary flood/non-flood.

### LSTM Flood Forecaster

- **Features**: daily precipitation, temperature, soil moisture, runoff, humidity (30-day sequence).
- **Fallback**: GBM with 7-day rolling mean/max/sum features.

### Explainability

- SHAP TreeExplainer for feature attribution.
- Isolation Forest for SAR time-series anomaly detection.
- Optuna for hyperparameter optimization.

---

## Foundation Models

| Model | Params | Input | Task | Source |
|---|---|---|---|---|
| Prithvi-EO-2.0 | 300M | HLS (S1+S2) | Flood segmentation | IBM/NASA |
| Clay Foundation | 70M | S1+S2+DEM | Multi-modal flood mapping | Made With Clay |
| ClimaX | 100M | ERA5 variables | Climate downscaling | Microsoft |
| Pangu-Weather | 256M | ERA5 pressure levels | Weather forecasting | Huawei |

All models gracefully fall back to a 12-feature Gradient Boosting classifier when weights are unavailable.

---

## Data Sources

| Dataset | GEE Asset ID | Resolution | Purpose |
|---|---|:---:|---|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 10 m | SAR change detection |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Spectral indices |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | 10 m | Land cover |
| SRTM DEM | `USGS/SRTMGL1_003` | 30 m | Slope, terrain, HAND |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | ~5.5 km | Rainfall |
| ERA5-Land Daily | `ECMWF/ERA5_LAND/DAILY_AGGR` | ~11 km | Climate variables |
| NOAA GFS | `NOAA/GFS0P25` | ~25 km | Weather forecasts |
| NASA NEX-GDDP-CMIP6 | `NASA/GDDP-CMIP6` | ~25 km | Climate projections |
| JRC Surface Water | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Water occurrence |
| WorldPop | `WorldPop/GP/100m/pop_age_sex_cons_unadj` | 100 m | Population |
| HydroSHEDS | `WWF/HydroSHEDS/*` | ~90 m | Watershed, HAND |

---

## Project Structure

```text
flood-predictor/
|-- frontend/                # React + Vite + TypeScript
|   |-- src/
|   |   |-- api/             #   Axios API client + endpoints
|   |   |-- components/      #   Layout, Map, Common UI components
|   |   |-- hooks/           #   useAOI, useAnalysis
|   |   |-- pages/           #   7 tab pages (lazy loaded)
|   |   |-- types/           #   TypeScript API types
|   |   |-- App.tsx           #   Main app with routing + shortcuts
|   |   `-- index.css         #   Global dark theme styles
|   |-- Dockerfile            #   Frontend build (Node + nginx)
|   `-- package.json
|-- api/                     # FastAPI REST API
|   |-- main.py              #   App entry, CORS, router registration
|   |-- schemas.py           #   Pydantic request/response models
|   |-- dependencies.py      #   GEE initialization
|   `-- routes/              #   12 route modules
|       |-- mca.py           #     /mca/risk-map, /mca/stats
|       |-- sar.py           #     /sar/flood-detection
|       |-- ml.py            #     /ml/classify, /ml/risk-prediction
|       |-- indices.py       #     /indices/tiles
|       |-- drought.py       #     /drought/analysis
|       |-- hydrology.py     #     /hydrology/analysis
|       |-- multiyear.py     #     /multiyear/comparison
|       |-- forecast.py      #     /forecast/weather
|       |-- projections.py   #     /projections/analysis
|       `-- geocode.py       #     /geocode
|-- gee_functions/           # Earth Engine geospatial logic (20 modules)
|-- ml_models/               # ML training/inference (12 modules)
|-- training/                # Offline training scripts
|-- utils/                   # Caching (TTLCache), logging, alerts
|-- ui_components/           # Shared constants (viz palettes)
|-- tests/                   # Unit/integration tests
|-- Dockerfile               # Multi-stage build (Node + Python + nginx)
|-- docker-compose.yml       # Two-service dev setup
|-- nginx.conf               # Reverse proxy + gzip + static caching
|-- start.sh                 # Production entrypoint
`-- .github/workflows/
    |-- ci.yml               # Lint (ruff) + test (pytest) + build
    `-- deploy.yml           # Deploy to Cloud Run on v* tags
```

---

## REST API

12 endpoints available at the API root:

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/geocode?q=` | GET | Geocode place name |
| `/mca/risk-map` | POST | MCA flood susceptibility |
| `/mca/stats` | POST | AOI terrain statistics |
| `/sar/flood-detection` | POST | SAR flood detection |
| `/ml/classify` | POST | ML flood classification |
| `/ml/risk-prediction` | POST | Flood risk prediction |
| `/indices/tiles` | POST | Spectral index tiles |
| `/drought/analysis` | POST | SPI + NDVI anomaly |
| `/hydrology/analysis` | POST | Watershed analysis |
| `/multiyear/comparison` | POST | Multi-year flood comparison |
| `/forecast/weather` | POST | GFS weather forecast |
| `/projections/analysis` | POST | CMIP6 climate projections |

All POST endpoints accept a `geojson` field with a GeoJSON geometry for the area of interest.

---

## Deployment

### CI/CD Pipeline

| Trigger | Workflow | Action |
|---------|----------|--------|
| Push to `main` or PR | `ci.yml` | Ruff lint + pytest + Docker build |
| Push `v*` tag | `deploy.yml` | Build image + deploy to Cloud Run |

### Deploy to Cloud Run

```bash
git tag v2.1
git push origin v2.1
```

This triggers the deploy workflow which:
1. Builds a multi-stage Docker image (React frontend + FastAPI + nginx)
2. Pushes to Artifact Registry
3. Deploys to Cloud Run (2 vCPU, 2GB RAM, auto-scaling 0-3 instances)

### Architecture

```text
Browser ──> Cloud Run ──> nginx (:8080)
                            |
                            |──> /static assets (React SPA)
                            |──> /api routes ──> uvicorn (:8000) ──> FastAPI ──> GEE
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` - `7` | Switch between tabs (Risk, SAR, ML, Climate, Indices, Hydro, Forecast) |
| `Esc` | Toggle sidebar collapse |

---

## Dependencies

**Frontend:**

```
react, react-dom, typescript, vite, leaflet, react-leaflet, recharts,
@tanstack/react-query, axios, lucide-react
```

**Backend:**

```
fastapi, uvicorn, pydantic, httpx, cachetools, earthengine-api,
pandas, numpy, requests
```

**ML:**

```
scikit-learn, xgboost, lightgbm, optuna, shap, joblib, matplotlib
```

**Optional (for advanced features):**

```
torch              # LSTM flood forecaster
transformers       # Foundation models (Prithvi, Clay, ClimaX)
huggingface-hub    # Model availability checking
```

Without optional dependencies, all features gracefully fall back to scikit-learn classifiers.

---

## Author

**Ankit Kumar**
ankituday123@gmail.com
M.Tech, Land and Water Resource Engineering
Department of Agricultural and Food Engineering
Indian Institute of Technology Kharagpur

[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)

---

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
