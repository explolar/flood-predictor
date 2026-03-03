# HydroRisk Atlas
### Satellite-Powered Flood Risk Intelligence · IIT Kharagpur

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://flood-predictor-518484395506.asia-south1.run.app)
[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-GEE-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **Live app →** https://flood-predictor-518484395506.asia-south1.run.app

A satellite-powered flood risk assessment platform built with **Google Earth Engine**, **Sentinel-1 SAR**, **Sentinel-2 SR**, **scikit-learn**, **XGBoost**, **LightGBM**, and **Streamlit**. Combines real-time satellite imagery with an ensemble of ML classifiers for flood inundation mapping, risk prediction, anomaly detection, and multi-hazard analysis at 10–30 m resolution.

---

## Table of Contents

1. [Overview](#overview)
2. [Technical Architecture](#technical-architecture)
3. [Project Structure](#project-structure)
4. [Analytical Methodology](#analytical-methodology)
5. [ML Models](#ml-models)
6. [Data Sources](#data-sources)
7. [Features](#features)
8. [Installation](#installation)
9. [Model Training](#model-training)
10. [Docker / Cloud Run Deployment](#docker--cloud-run-deployment)
11. [REST API](#rest-api)
12. [Dependencies](#dependencies)
13. [Author](#author)
14. [License](#license)

---

## Overview

HydroRisk Atlas is a modular geospatial flood intelligence platform with 6 consolidated tabs (RISK, SAR, ML, CLIMATE, INDICES, HYDROLOGY) that combines rule-based geospatial analysis with a suite of ML classifiers. The analytical pipeline covers:

**Core Analysis**
- **MCA Susceptibility** — Weighted multi-criteria analysis of land cover, terrain slope, and historical rainfall producing a static flood susceptibility index.
- **SAR Inundation Detection** — Sentinel-1 SAR change-detection between a dry-season reference and a user-defined post-event window with a 6-layer quality filter chain.
- **Flood Depth Estimation** — Per-pixel water depth from SRTM DEM and a water-surface elevation proxy.
- **Crop Loss Assessment** — ESA WorldCover cropland mask × NDVI drop with configurable price-per-hectare valuation.
- **Flood Return Period** — Gumbel Type-I distribution fitted to 24 years of CHIRPS monsoon rainfall.

**ML Classifiers**
- **Random Forest** — 5-class flood risk from terrain, climate, land cover, and historical water features.
- **Gradient Boosting / XGBoost / LightGBM** — Pixel-wise SAR flood classification with 8 multi-source features.
- **Ensemble Stacking** — LogisticRegression meta-learner combining GB + XGB base classifiers.
- **Isolation Forest** — Anomaly detection on monthly SAR backscatter time series.

**Advanced Modules**
- SHAP explainability, Optuna hyperparameter tuning, population displacement estimation, building damage assessment, soil moisture integration, urban flood vulnerability index, water quality assessment, multi-year comparison, drought monitoring (SPI + NDVI), spectral indices download (NDVI/NDWI/MNDWI/NDBI/SAVI/EVI/BSI with GeoTIFF & cartographic PDF export), HydroSHEDS watershed delineation, stream network extraction, terrain hydrology analysis, 3D terrain visualization, timelapse animation, real-time rainfall alerts, multi-language UI, FastAPI REST wrapper, SQLite/PostgreSQL backend.

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                       │
│  Sidebar controls  →  Session state  →  6-tab render engine    │
└────────────────────┬──────────────────────┬─────────────────────┘
                     │                      │
    @st.cache_data   │                      │  Tab 5: ML Intelligence
    (TTL 3600 s)     │                      │  (sub-tabs: Classifiers │
                     ▼                      │   Analytics │ Tools)    │
┌────────────────────────────┐  ┌───────────┴────────────────────────┐
│   GEE Python Client        │  │   ML Models (Python)               │
│   ee.ImageCollection       │  │   RF · GB · XGB · LGBM · Ensemble  │
│   ee.Image · ee.Reducer    │──│   Isolation Forest · SHAP          │
│   ee.Geometry              │  │   SHAP · Optuna AutoML             │
└────────────────────┬───────┘  └────────────┬───────────────────────┘
                     │                       │
                     │ getMapId() → tiles    │ reduceToImage() → tiles
                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Folium / Leaflet.js / PyDeck                   │
│  TileLayer · GeoJson · DualMap · 3D Terrain · Timelapse        │
│  Fullscreen · MiniMap · LayerControl · st_folium                │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- GEE `Image` objects are not serializable — `@st.cache_data` functions return **tile URL strings** instead. EE initialization uses `@st.cache_resource` for a singleton session.
- Folium legends are injected as Leaflet `L.control` objects via JavaScript, persisting during fullscreen mode.
- **ML round-trip:** GEE samples features via `stratifiedSample()` → Python `.predict()` → `ee.FeatureCollection` → `reduceToImage()` → `getMapId()` for tile rendering.
- Modular tab architecture: each tab is a standalone module in `tabs/`, receiving `aoi_json` and a `params` dict from `app.py`.
- **S2 scene cap:** Collections are capped at 40 least-cloudy scenes to keep GEE computation graphs under the 50 MB request-size limit.
- **On-demand downloads:** GeoTIFF download URLs are generated per-index on click (not during batch computation) to avoid blocking the main pipeline.

---

## Project Structure

```
flood-predictor/
├── app.py                            # Streamlit entrypoint — sidebar + 6-tab dispatch
├── requirements.txt
├── Dockerfile                        # Dual-mode: MODE=api (FastAPI) or Streamlit
├── pyproject.toml                    # Ruff linting config
├── pytest.ini
│
├── tabs/                             # Per-tab render modules
│   ├── tab_mca.py                    # RISK — MCA susceptibility + Urban Vulnerability
│   ├── tab_sar.py                    # SAR — Detection + Comparison + Progression (sub-tabs)
│   ├── tab_dual.py                   # SAR sub-tab: Dual-view comparison + 3D Terrain (PyDeck)
│   ├── tab_progression.py            # SAR sub-tab: Flood progression + Timelapse animation
│   ├── tab_ml.py                     # ML — Classifiers / Analytics / Tools (sub-tabs)
│   ├── tab_multiyear.py              # CLIMATE sub-tab: Multi-year flood comparison
│   ├── tab_drought.py                # CLIMATE sub-tab: SPI + NDVI anomaly drought monitoring
│   ├── tab_indices.py                # INDICES — Spectral indices (NDVI, NDWI, MNDWI, NDBI, SAVI, EVI, BSI)
│   └── tab_hydrology.py             # HYDROLOGY — Watershed / Streams / Terrain (sub-tabs)
│
├── gee_functions/                    # Google Earth Engine computation modules
│   ├── core.py                       # EE init, AOI terrain stats
│   ├── mca.py                        # Multi-Criteria Analysis
│   ├── sar.py                        # SAR flood detection, depth, recession
│   ├── chirps.py                     # CHIRPS rainfall, Gumbel return periods
│   ├── layers.py                     # NDVI, JRC frequency, S2 RGB
│   ├── infrastructure.py             # OSM infrastructure, roads, GRanD dams
│   ├── crop.py                       # NDVI-based crop loss
│   ├── watershed.py                  # HydroSHEDS watershed, stream network, terrain hydrology
│   ├── population.py                 # WorldPop displacement estimates
│   ├── buildings.py                  # Google Open Buildings damage assessment
│   ├── soil_moisture.py              # NASA SMAP soil moisture
│   ├── urban_vulnerability.py        # Urban Flood Vulnerability Index
│   ├── drought.py                    # SPI + NDVI anomaly
│   ├── water_quality.py              # Sentinel-2 turbidity / chlorophyll-a
│   ├── multiyear.py                  # Multi-year flood comparison
│   ├── sar_timeseries.py             # Monthly SAR stats for anomaly detection
│   └── indices.py                    # Sentinel-2 spectral indices (NDVI, NDWI, MNDWI, NDBI, SAVI, EVI, BSI)
│
├── ml_models/                        # Machine learning models
│   ├── flood_risk_model.py           # Random Forest (5-class risk)
│   ├── sar_classifier.py             # Gradient Boosting (SAR classification)
│   ├── xgb_classifier.py             # XGBoost classifier
│   ├── lgbm_classifier.py            # LightGBM classifier
│   ├── ensemble_stacker.py           # Ensemble meta-learner (GB + XGB + LR)
│   ├── anomaly_detector.py           # Isolation Forest anomaly detection
│   ├── explainability.py             # SHAP TreeExplainer
│   ├── automl_tuner.py               # Optuna hyperparameter optimization
│   └── data_extraction.py            # GEE pixel sampling for training
│
├── ui_components/                    # Frontend utilities
│   ├── styles.py                     # CSS injection (dark theme)
│   ├── constants.py                  # Viz palettes, crop prices
│   ├── legends.py                    # Leaflet L.control legends
│   ├── reports.py                    # Text and PDF reports
│   ├── animation.py                  # Leaflet.js timelapse
│   ├── deck_viz.py                   # PyDeck 3D terrain
│   └── i18n.py                       # Multi-language support
│
├── training/                         # Offline training scripts
│   ├── train_flood_risk.py
│   ├── train_sar_classifier.py
│   ├── train_xgb_classifier.py
│   ├── train_lgbm_classifier.py
│   └── tune_hyperparams.py           # Optuna offline tuning
│
├── api/                              # FastAPI REST wrapper
│   ├── main.py
│   ├── schemas.py
│   ├── dependencies.py
│   └── routes/
│       ├── mca.py
│       ├── sar.py
│       └── ml.py
│
├── database/                         # SQLAlchemy backend
│   ├── models.py
│   ├── connection.py
│   └── crud.py
│
├── auth/                             # Authentication
│   └── auth_manager.py
│
├── utils/
│   ├── cache.py                      # Caching abstraction (Streamlit + FastAPI)
│   ├── logging_config.py             # Structured logging + Sentry
│   └── alerts.py                     # Real-time rainfall alerts
│
├── tests/
│   ├── conftest.py
│   ├── test_ml_models.py
│   ├── test_utils.py
│   └── test_ui_components.py
│
├── .github/workflows/
│   ├── ci.yml                        # Lint + test + Docker build
│   └── deploy.yml                    # Cloud Run deploy
│
└── models/                           # Serialized trained models (.joblib)
```

---

## Analytical Methodology

### Phase 1 — Multi-Criteria Analysis (MCA)

Each input layer is reclassified to a 1–5 hazard rank, then combined as a weighted sum:

```
Risk Score = (LULC_rank × w₁) + (Slope_rank × w₂) + (Rainfall_rank × w₃)
```

| Layer | Source | Reclassification |
|-------|--------|-----------------|
| LULC | ESA WorldCover v200 | Built-up/Water → 5, Cropland → 3, Trees → 1 |
| Slope | SRTM 30 m | Flat ≤ 2° → 5, Steep > 20° → 1 |
| Rainfall | CHIRPS annual | < 1860 mm → 1, ≥ 1950 mm → 5 |

### Phase 2 — SAR Change-Detection Flood Mapping

```
S1 GRD (VH/VV) → median composites (pre/post) → DIFF = PRE − POST
→ Threshold > T dB → 6-filter quality chain:
  1. Terrain guard (slope < 8°)
  2. Permanent water exclusion (JRC seasonality ≥ 10 months)
  3. Historical flood gate (JRC occurrence ≥ 5%)
  4. Lowland restriction (elevation ≤ 40th percentile)
  5. Minimum patch (≥ 56 connected pixels ≈ 5 ha)
  6. Morphological cleanup (focal_mode 40 m)
```

### Flood Depth Estimation

```
water_surface ≈ 95th-percentile elevation of flooded pixels
depth = water_surface − pixel_elevation  (clamped ≥ 0 m)
```

### Flood Return Period (Gumbel Type-I)

24 years of CHIRPS monsoon rainfall → Gumbel parameters → return period thresholds for 2/5/10/25/50/100-year events.

---

## ML Models

### Random Forest — 5-Class Flood Risk

| | |
|---|---|
| **Features** | elevation, slope, annual_rainfall, lulc_class, jrc_occurrence, jrc_max_extent |
| **Target** | JRC water occurrence → 5 risk classes |
| **Params** | 200 trees, max_depth=15, balanced weights, OOB scoring |
| **Inference** | GEE samples → RF predict → reduceToImage → map tiles |

### Gradient Boosting / XGBoost / LightGBM — SAR Flood Classification

| | |
|---|---|
| **Features** | pre_sar, post_sar, sar_diff, sar_ratio, elevation, slope, jrc_occ, jrc_season |
| **Target** | Binary flood/non-flood (self-supervised from threshold method) |
| **Output** | Classification mask or probability heatmap |
| **Selection** | User picks GB, XGB, LGBM, or Ensemble via radio selector |

### Ensemble Stacking

LogisticRegression meta-learner trained on out-of-fold predictions from GB + XGB base classifiers.

### Isolation Forest — Anomaly Detection

Detects anomalous months in SAR backscatter time series (2018–2024). No training labels needed — unsupervised.

### SHAP Explainability

TreeExplainer computes Shapley values for SAR classifiers, producing feature importance tables and summary plots.

### Optuna AutoML

Bayesian hyperparameter optimization for GB and XGBoost with cross-validated F1 scoring.

---

## Data Sources

| Dataset | GEE Asset ID | Resolution | Use |
|---------|-------------|:----------:|-----|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 10 m | SAR backscatter, change detection |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | 10 m | LULC, crop mask |
| SRTM DEM | `USGS/SRTMGL1_003` | 30 m | Slope, terrain masking, flood depth |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | ~5.5 km | Rainfall, return periods |
| JRC Global Surface Water | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Water occurrence, flood gate |
| JRC Monthly History | `JRC/GSW1_4/MonthlyHistory` | 30 m | Flood frequency 1984–2021 |
| WorldPop | `WorldPop/GP/100m/pop_age_sex_cons_unadj` | 100 m | Population displacement |
| Google Open Buildings | `GOOGLE/Research/open-buildings/v3/polygons` | vector | Building damage assessment |
| NASA SMAP | `NASA/SMAP/SPL3SMP_E/005` | 9 km | Soil moisture |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | NDVI, NDWI, MNDWI, NDBI, SAVI, EVI, BSI, true color, water quality |
| MODIS NDVI | `MODIS/061/MOD13A2` | 1 km | Drought NDVI anomaly |
| HydroSHEDS Basins | `WWF/HydroSHEDS/v1/Basins/hybas_{6,8,10}` | vector | Watershed delineation |
| HydroSHEDS Flow Acc | `WWF/HydroSHEDS/03ACC` | ~90 m | Flow accumulation, stream extraction |
| HydroSHEDS Flow Dir | `WWF/HydroSHEDS/03DIR` | ~90 m | D8 flow direction |
| HydroSHEDS Cond. DEM | `WWF/HydroSHEDS/03CONDEM` | ~90 m | Hydrologically conditioned DEM |
| GRanD Dams | `projects/sat-io/open-datasets/GRanD/GRAND_Dams_v1_3` | vector | Dam context (150 km) |

---

## Features

### Tab 1 — RISK (MCA Susceptibility)
- Weighted MCA (LULC + Slope + Rainfall) with interactive sliders
- AOI terrain stats, JRC flood frequency, S2 true color, watershed overlay
- Urban Flood Vulnerability Index (imperviousness + elevation + slope + population)
- GeoTIFF download

### Tab 2 — SAR (sub-tabs: Detection | Comparison | Progression)
- **Detection** — 8 selectable layers: Flood mask, severity, depth, pre/post SAR, change, NDVI damage, crop loss; flood depth raster with histogram; population displacement (WorldPop); building damage (Google Open Buildings); soil moisture (SMAP); water quality (S2 turbidity/chlorophyll-a); recession curve, infrastructure overlay, road risk, dam context
- **Comparison** — Synchronized side-by-side pre/post SAR maps (DualMap); Sentinel-2 true-color pre/post comparison; 3D terrain flood visualization (PyDeck)
- **Progression** — Monthly SAR flood extent (Jun–Oct) with CHIRPS rainfall chart; timelapse animation with play/pause controls

### Tab 3 — ML Intelligence (sub-tabs: Classifiers | Analytics | Tools)
- **Classifiers** — Random Forest risk, SAR multi-model (GB/XGB/LGBM/Ensemble)
- **Analytics** — SHAP explainability, Isolation Forest anomaly detection
- **Tools** — Optuna hyperparameter tuning, model diagnostics

### Tab 4 — CLIMATE (sub-tabs: Multi-Year | Drought)
- **Multi-Year** — Side-by-side flood maps across years, comparative bar chart, trend analysis
- **Drought** — Standardized Precipitation Index (SPI), MODIS NDVI anomaly vs 20-year climatology

### Tab 5 — INDICES (Spectral Indices Download)

- 7 indices from Sentinel-2 SR at 10 m: **NDVI**, **NDWI**, **MNDWI**, **NDBI**, **SAVI**, **EVI**, **BSI**
- Classified maps with per-index thresholds and color ramps
- Interactive folium map with index tile overlay and dynamic legend
- GeoTIFF download (30 m) for each index
- Cartographic PDF export with north arrow, coordinate labels, classified legend, statistics, and methodology
- Info/methodology panel with classification basis and threshold table for each index

### Tab 6 — HYDROLOGY (sub-tabs: Watershed | Streams | Terrain)
- **Watershed** — Multi-level HydroSHEDS basin hierarchy (Levels 6, 8, 10) with interactive map overlay and per-basin statistics (area, upstream area, mean elevation)
- **Streams** — Stream network extracted from HydroSHEDS 3 arc-sec flow accumulation with configurable upstream cell threshold (50–500); Strahler order proxy via log10 binning; drainage density computation (km/km²)
- **Terrain** — Flow accumulation (log scale), D8 flow direction, and hydrologically conditioned DEM visualization from HydroSHEDS

### Sidebar
- Place name geocoding → auto AOI
- Bounding box / GeoJSON upload
- MCA weight sliders, SAR date pickers, polarization, threshold, speckle filter
- Crop type + price selector
- Technical report (TXT + PDF) download

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

---

## Model Training

Pre-trained models (`.joblib`) are stored in `models/`. To retrain:

```bash
python training/train_flood_risk.py         # Random Forest (~5 min)
python training/train_sar_classifier.py      # Gradient Boosting (~10 min)
python training/train_xgb_classifier.py      # XGBoost
python training/train_lgbm_classifier.py     # LightGBM
python training/tune_hyperparams.py          # Optuna tuning
```

Without pre-trained files, models train on-the-fly using the current AOI.

---

## Docker / Cloud Run Deployment

```bash
# Build
docker build -t hydrorisk-atlas .

# Run (Streamlit — default)
docker run -p 8080:8080 hydrorisk-atlas

# Run (FastAPI)
docker run -p 8080:8080 -e MODE=api hydrorisk-atlas
```

On Cloud Run, the service account's GEE credentials are picked up automatically.

---

## REST API

When running with `MODE=api`, a FastAPI server provides programmatic access:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/mca/risk-map` | POST | MCA susceptibility analysis |
| `/mca/stats` | POST | AOI terrain statistics |
| `/sar/flood-detection` | POST | SAR flood detection |
| `/ml/classify` | POST | ML flood classification |
| `/ml/risk-prediction` | POST | ML risk prediction |

---

## Dependencies

```
# Core
streamlit, earthengine-api, folium, streamlit-folium, pandas, numpy, requests

# ML
scikit-learn>=1.3, joblib, xgboost, lightgbm, optuna, shap, matplotlib

# Reports
fpdf2

# Visualization
pydeck

# Backend
fastapi, uvicorn, pydantic, sqlalchemy, bcrypt
```

---

## Author

**Ankit Kumar**
(email-Ankituday123@gmail.com)
M.Tech
Land and Water Resource Engineering,
Department of Agricultural and Food Engineering,
Indian Institute of Technology Kharagpur

[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)

---

## License

MIT License — free to use and modify with attribution.
