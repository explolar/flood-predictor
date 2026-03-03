# HydroRisk Atlas
### Satellite-Powered Flood Risk Intelligence | IIT Kharagpur

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://flood-predictor-518484395506.asia-south1.run.app)
[![GitHub](https://img.shields.io/badge/GitHub-explolar-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/explolar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Ankit%20Kumar-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ankit-kumar-9b3b06228/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Earth Engine](https://img.shields.io/badge/Google%20Earth%20Engine-GEE-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](https://opensource.org/licenses/MIT)

> Live app: https://flood-predictor-518484395506.asia-south1.run.app

HydroRisk Atlas is a modular flood intelligence platform that combines Google Earth Engine geospatial analytics with machine learning for flood susceptibility mapping, SAR-based inundation detection, impact estimation, and hydrology workflows.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Quick Start](#quick-start)
3. [Application Modules](#application-modules)
4. [Core Methodology](#core-methodology)
5. [Machine Learning Stack](#machine-learning-stack)
6. [Data Sources](#data-sources)
7. [Project Structure](#project-structure)
8. [Training Models](#training-models)
9. [Run with Docker](#run-with-docker)
10. [REST API](#rest-api)
11. [Dependencies](#dependencies)
12. [Author](#author)
13. [License](#license)

---

## What It Does

HydroRisk Atlas provides six primary modules:

- **RISK**: Multi-Criteria Analysis (MCA) flood susceptibility and urban vulnerability mapping.
- **SAR**: Sentinel-1 flood detection, pre/post comparison, progression, depth, crop loss, and impact overlays.
- **ML Intelligence**: Random Forest risk mapping, SAR classifiers (GB/XGB/LGBM/Ensemble), SHAP analysis, anomaly detection.
- **CLIMATE**: Multi-year flood comparison and drought monitoring (SPI + NDVI anomaly).
- **INDICES**: Sentinel-2 spectral indices (NDVI/NDWI/MNDWI/NDBI/SAVI/EVI/BSI) with export tools.
- **HYDROLOGY**: Watershed delineation, stream extraction, and terrain-flow analysis using HydroSHEDS.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/explolar/flood-predictor.git
cd flood-predictor
pip install -r requirements.txt
```

### 2. Authenticate Earth Engine

```bash
earthengine authenticate
```

### 3. Run Streamlit app

```bash
streamlit run app.py
```

---

## Application Modules

### RISK (MCA Susceptibility)

- Weighted MCA using LULC, slope, and rainfall layers.
- AOI terrain metrics and flood-frequency overlays.
- Urban Flood Vulnerability Index.
- GeoTIFF export.

### SAR (Detection, Comparison, Progression)

- Flood mask, severity, depth, SAR change layers, and crop-loss estimation.
- Dual-map pre/post comparison and 3D terrain visualization.
- Monthly progression (Jun-Oct) with rainfall trends and timelapse.
- Optional overlays: population displacement, building damage, soil moisture, water quality.

### ML Intelligence (Classifiers, Analytics, Tools)

- Random Forest 5-class risk prediction.
- SAR classifiers: Gradient Boosting, XGBoost, LightGBM, ensemble stacking.
- SHAP-based feature explanation.
- Isolation Forest anomaly detection.
- Optuna hyperparameter tuning.

### CLIMATE

- Multi-year flood trend comparison.
- Drought diagnostics using SPI and NDVI anomaly.

### INDICES

- Seven Sentinel-2 indices at 10 m visualization resolution.
- Interactive map overlays, threshold classes, legends.
- GeoTIFF and cartographic PDF export.

### HYDROLOGY

- HydroSHEDS basin hierarchy mapping (levels 6/8/10).
- Stream network extraction from flow accumulation thresholds.
- Flow direction, accumulation, and terrain hydrology diagnostics.

---

## Core Methodology

### 1. Multi-Criteria Analysis (MCA)

Each layer is reclassified to hazard rank (1-5), then combined with user-defined weights:

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

### 4. Return Period Analysis

- CHIRPS monsoon series (~24 years).
- Gumbel Type-I fitting for 2/5/10/25/50/100-year return levels.

---

## Machine Learning Stack

### Random Forest (Flood Risk)

- **Features**: elevation, slope, rainfall, LULC, JRC water metrics.
- **Target**: 5 risk classes derived from water occurrence.
- **Output**: tile-rendered risk classification.

### SAR Classifiers (GB / XGB / LGBM / Ensemble)

- **Features**: pre/post SAR, difference, ratio, elevation, slope, JRC indicators.
- **Target**: binary flood/non-flood derived from SAR thresholding workflow.
- **Output**: class mask or probability heatmap.

### Explainability and Monitoring

- SHAP TreeExplainer for feature attribution.
- Isolation Forest for SAR time-series anomaly detection.
- Optuna for hyperparameter optimization.

---

## Data Sources

| Dataset | GEE Asset ID | Resolution | Purpose |
|---|---|:---:|---|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 10 m | SAR change detection |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Spectral indices and true color |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | 10 m | Land cover and crop mask |
| SRTM DEM | `USGS/SRTMGL1_003` | 30 m | Slope and terrain analysis |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | ~5.5 km | Rainfall and return periods |
| JRC Surface Water | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Water occurrence and seasonality |
| WorldPop | `WorldPop/GP/100m/pop_age_sex_cons_unadj` | 100 m | Population exposure |
| Open Buildings | `GOOGLE/Research/open-buildings/v3/polygons` | Vector | Building impact |
| NASA SMAP | `NASA/SMAP/SPL3SMP_E/005` | 9 km | Soil moisture |
| HydroSHEDS | `WWF/HydroSHEDS/*` | ~90 m / Vector | Watershed and stream analysis |

---

## Project Structure

```text
flood-predictor/
|-- app.py
|-- requirements.txt
|-- Dockerfile
|-- tabs/                # Streamlit tab renderers
|-- gee_functions/       # Earth Engine geospatial logic
|-- ml_models/           # ML training/inference modules
|-- training/            # Offline training scripts
|-- api/                 # FastAPI app and routes
|-- database/            # SQLAlchemy models and CRUD
|-- ui_components/       # Styling, legends, reports, i18n
|-- utils/               # Caching, logging, alerts
|-- tests/               # Unit/integration tests
`-- models/              # Serialized .joblib models
```

---

## Training Models

Pre-trained `.joblib` files are expected in `models/`. To retrain:

```bash
python training/train_flood_risk.py
python training/train_sar_classifier.py
python training/train_xgb_classifier.py
python training/train_lgbm_classifier.py
python training/tune_hyperparams.py
```

---

## Run with Docker

```bash
# Build image
docker build -t hydrorisk-atlas .

# Run Streamlit mode (default)
docker run -p 8080:8080 hydrorisk-atlas

# Run FastAPI mode
docker run -p 8080:8080 -e MODE=api hydrorisk-atlas
```

Cloud Run can use attached service-account credentials for Earth Engine access.

---

## REST API

When `MODE=api`, the following endpoints are available:

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Service information |
| `/health` | GET | Health check |
| `/mca/risk-map` | POST | MCA susceptibility |
| `/mca/stats` | POST | AOI terrain stats |
| `/sar/flood-detection` | POST | SAR flood detection |
| `/ml/classify` | POST | SAR ML classification |
| `/ml/risk-prediction` | POST | Flood risk prediction |

---

## Dependencies

- Core: `streamlit`, `earthengine-api`, `folium`, `streamlit-folium`, `pandas`, `numpy`
- ML: `scikit-learn`, `xgboost`, `lightgbm`, `optuna`, `shap`, `joblib`
- Backend: `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `bcrypt`
- Reporting/Visualization: `fpdf2`, `pydeck`, `matplotlib`

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
