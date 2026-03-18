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

HydroRisk Atlas is a modular flood intelligence platform that combines Google Earth Engine geospatial analytics with machine learning, climate projections, and AI foundation models for flood susceptibility mapping, SAR-based inundation detection, weather forecasting, and hydrology workflows.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Quick Start](#quick-start)
3. [Application Modules](#application-modules)
4. [Core Methodology](#core-methodology)
5. [Machine Learning Stack](#machine-learning-stack)
6. [Foundation Models](#foundation-models)
7. [Data Sources](#data-sources)
8. [Project Structure](#project-structure)
9. [Training Models](#training-models)
10. [Run with Docker](#run-with-docker)
11. [REST API](#rest-api)
12. [Dependencies](#dependencies)
13. [Author](#author)
14. [License](#license)

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

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/explolar/flood-predictor.git
cd flood-predictor
pip install -r requirements.txt
```

### 2. (Optional) Install advanced ML dependencies

```bash
pip install torch transformers huggingface-hub   # Foundation models + LSTM
```

Without these, the app falls back to scikit-learn GBM classifiers automatically.

### 3. Authenticate Earth Engine

```bash
earthengine authenticate
```

### 4. Run Streamlit app

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

- Random Forest 5-class risk prediction (with optional ERA5 features).
- SAR classifiers: Gradient Boosting, XGBoost, LightGBM, ensemble stacking.
- SHAP-based feature explanation.
- Isolation Forest anomaly detection.
- Optuna hyperparameter tuning.

### CLIMATE (Projections + Drought)

- Multi-year flood trend comparison.
- Drought diagnostics using SPI and NDVI anomaly.
- **ERA5-Land historical climate**: annual temperature, precipitation, runoff, evapotranspiration, soil moisture, and monsoon profiles.
- **CMIP6 future projections**: NASA NEX-GDDP-CMIP6 under SSP245/SSP585 scenarios from 6 GCMs (ACCESS-CM2, GFDL-ESM4, MRI-ESM2-0, UKESM1-0-LL, IPSL-CM6A-LR, MPI-ESM1-2-HR).
- **Future flood risk maps**: side-by-side current vs. projected risk using CMIP6 rainfall in the trained RF model.
- **Multi-model ensemble**: majority vote across multiple GCMs with spatial risk delta map.
- **Scenario comparison**: SSP245 vs SSP585 across 2030-2050, 2050-2070, 2070-2100.

### INDICES

- Seven Sentinel-2 indices at 10 m visualization resolution.
- Interactive map overlays, threshold classes, legends.
- GeoTIFF and cartographic PDF export.

### HYDROLOGY

- HydroSHEDS basin hierarchy mapping (levels 6/8/10).
- Stream network extraction from flow accumulation thresholds.
- Flow direction, accumulation, and terrain hydrology diagnostics.
- **HAND (Height Above Nearest Drainage)**: terrain-based flood susceptibility with configurable stream threshold and flood depth simulation.

### FORECAST (Weather + Flood Prediction + AI Models)

- **Weather**: NOAA GFS 0.25-degree forecasts for 7-16 days (precipitation, temperature, humidity, wind) with spatial maps and flood alert assessment.
- **Flood Forecast**: LSTM (PyTorch) or GBM (scikit-learn) trained on 6 years of ERA5-Land monsoon data, predicts 7-14 day flood probability using GFS forecast as input.
- **River Discharge**: GloFAS-style discharge estimation using ERA5 runoff weighted by HydroSHEDS flow accumulation, Gumbel return periods, and flood exceedance alerts.
- **AI Foundation Models**: select from Prithvi-EO-2.0, Clay Foundation, ClimaX, or Pangu-Weather for enhanced 12-feature SAR flood classification. Falls back to GBM when model weights unavailable.

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

### 4. HAND (Height Above Nearest Drainage)

```text
Drainage network = flow_accumulation > threshold
HAND = pixel_elevation - nearest_drainage_elevation (>= 0)
Flood extent = pixels where HAND <= simulated_depth
```

Reference: Rennó et al. (2008), Nobre et al. (2011).

### 5. Return Period Analysis

- CHIRPS monsoon series (~24 years) for rainfall.
- ERA5 runoff series (~20 years) for discharge.
- Gumbel Type-I fitting for 2/5/10/25/50/100-year return levels.

### 6. Climate Projections

```text
Current risk map: RF model trained on CHIRPS + terrain + JRC
Future risk map:  same RF model with CMIP6 projected rainfall replacing CHIRPS
Risk delta:       future_class - current_class per pixel
Ensemble:         majority vote across N climate models
```

### 7. Flood Forecasting

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

- **Features**: elevation, slope, rainfall, LULC, JRC water metrics (+ optional ERA5: runoff, soil moisture, temperature).
- **Target**: 5 risk classes derived from water occurrence.
- **Output**: tile-rendered risk classification.

### SAR Classifiers (GB / XGB / LGBM / Ensemble)

- **Features**: pre/post SAR, difference, ratio, elevation, slope, JRC indicators.
- **Target**: binary flood/non-flood derived from SAR thresholding workflow.
- **Output**: class mask or probability heatmap.

### LSTM Flood Forecaster

- **Features**: daily precipitation, temperature, soil moisture, runoff, humidity (30-day sequence).
- **Target**: binary flood event (next day).
- **Output**: 7-14 day flood probability timeline.
- **Fallback**: GBM with 7-day rolling mean/max/sum features.

### Explainability and Monitoring

- SHAP TreeExplainer for feature attribution.
- Isolation Forest for SAR time-series anomaly detection.
- Optuna for hyperparameter optimization.

---

## Foundation Models

HydroRisk Atlas integrates geospatial AI foundation models for enhanced flood classification. All models gracefully fall back to a 12-feature Gradient Boosting classifier when weights are unavailable.

| Model | Params | Input | Task | Source |
|---|---|---|---|---|
| Prithvi-EO-2.0 | 300M | HLS (S1+S2) | Flood segmentation | IBM/NASA |
| Clay Foundation | 70M | S1+S2+DEM | Multi-modal flood mapping | Made With Clay |
| ClimaX | 100M | ERA5 variables | Climate downscaling | Microsoft |
| Pangu-Weather | 256M | ERA5 pressure levels | Weather forecasting | Huawei |

### Enhanced Feature Set (12 features)

When using foundation models (or their GBM fallback), the classifier uses an expanded feature set:

| Feature | Source | Description |
|---|---|---|
| `pre_sar` | Sentinel-1 | Pre-flood backscatter |
| `post_sar` | Sentinel-1 | Post-flood backscatter |
| `sar_diff` | Derived | Pre - Post difference |
| `sar_ratio` | Derived | Pre / Post ratio |
| `sar_cv` | Derived | Coefficient of variation |
| `elevation` | SRTM | DEM elevation |
| `slope` | SRTM | Terrain slope |
| `jrc_occ` | JRC GSW | Surface water occurrence |
| `jrc_season` | JRC GSW | Surface water seasonality |
| `jrc_transitions` | JRC GSW | Water class transitions |
| `ndvi_proxy` | Derived | SAR vegetation damage proxy |
| `terrain_roughness` | SRTM | Local elevation std dev |

---

## Data Sources

| Dataset | GEE Asset ID | Resolution | Purpose |
|---|---|:---:|---|
| Sentinel-1 GRD | `COPERNICUS/S1_GRD` | 10 m | SAR change detection |
| Sentinel-2 SR | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Spectral indices and true color |
| ESA WorldCover v200 | `ESA/WorldCover/v200` | 10 m | Land cover and crop mask |
| SRTM DEM | `USGS/SRTMGL1_003` | 30 m | Slope, terrain, HAND |
| CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | ~5.5 km | Rainfall and return periods |
| ERA5-Land Daily | `ECMWF/ERA5_LAND/DAILY_AGGR` | ~11 km | Temperature, runoff, ET, soil moisture |
| NOAA GFS | `NOAA/GFS0P25` | ~25 km | 7-16 day weather forecasts |
| NASA NEX-GDDP-CMIP6 | `NASA/GDDP-CMIP6` | ~25 km | Climate projections (2015-2100) |
| JRC Surface Water | `JRC/GSW1_4/GlobalSurfaceWater` | 30 m | Water occurrence and seasonality |
| WorldPop | `WorldPop/GP/100m/pop_age_sex_cons_unadj` | 100 m | Population exposure |
| Open Buildings | `GOOGLE/Research/open-buildings/v3/polygons` | Vector | Building impact |
| NASA SMAP | `NASA/SMAP/SPL3SMP_E/005` | 9 km | Soil moisture |
| HydroSHEDS | `WWF/HydroSHEDS/*` | ~90 m / Vector | Watershed, streams, HAND, discharge |

---

## Project Structure

```text
flood-predictor/
|-- app.py                  # Streamlit entry point (7 tabs)
|-- requirements.txt
|-- Dockerfile
|-- tabs/                   # Streamlit tab renderers
|   |-- tab_mca.py          #   RISK tab
|   |-- tab_sar.py          #   SAR tab (detection/comparison/progression)
|   |-- tab_ml.py           #   ML tab (classifiers/analytics/tools)
|   |-- tab_multiyear.py    #   CLIMATE > Multi-year
|   |-- tab_drought.py      #   CLIMATE > Drought
|   |-- tab_projections.py  #   CLIMATE > Projections (ERA5/CMIP6/future risk/ensemble)
|   |-- tab_indices.py      #   INDICES tab
|   |-- tab_hydrology.py    #   HYDROLOGY tab (watershed/streams/terrain/HAND)
|   `-- tab_forecast.py     #   FORECAST tab (weather/flood/discharge/AI models)
|-- gee_functions/          # Earth Engine geospatial logic
|   |-- core.py             #   GEE initialization, AOI stats
|   |-- mca.py              #   Multi-Criteria Analysis
|   |-- sar.py              #   Sentinel-1 flood detection
|   |-- chirps.py           #   CHIRPS rainfall and return periods
|   |-- era5.py             #   ERA5-Land climate data + ML features
|   |-- cmip6.py            #   CMIP6 projections + future risk stacks
|   |-- gfs_forecast.py     #   NOAA GFS weather forecasts
|   |-- glofas.py           #   River discharge estimation + return periods
|   |-- watershed.py        #   HydroSHEDS basins, streams, HAND
|   |-- layers.py           #   Sentinel-2, JRC, RGB composites
|   |-- indices.py          #   7 spectral indices registry
|   |-- drought.py          #   SPI + NDVI anomaly
|   |-- population.py       #   WorldPop displacement estimates
|   |-- crop.py             #   Crop loss assessment
|   |-- buildings.py        #   Building damage from SAR coherence
|   |-- infrastructure.py   #   OSM hospitals, schools, roads
|   |-- soil_moisture.py    #   NASA SMAP soil moisture
|   |-- water_quality.py    #   Water body classification
|   |-- urban_vulnerability.py  # Urban sprawl detection
|   |-- sar_timeseries.py   #   Multi-temporal SAR stacks
|   `-- multiyear.py        #   JRC historical flood frequency
|-- ml_models/              # ML training/inference modules
|   |-- flood_risk_model.py #   Random Forest (base + ERA5 features + future risk)
|   |-- sar_classifier.py   #   Gradient Boosting SAR classifier
|   |-- xgb_classifier.py   #   XGBoost variant
|   |-- lgbm_classifier.py  #   LightGBM variant
|   |-- ensemble_stacker.py #   Stacking ensemble
|   |-- flood_forecaster.py #   LSTM / GBM flood probability forecaster
|   |-- prithvi_flood.py    #   Prithvi-100M SAR classification
|   |-- foundation_models.py #  Unified foundation model interface (Prithvi-EO-2/Clay/ClimaX/Pangu)
|   |-- data_extraction.py  #   GEE pixel sampling for training
|   |-- explainability.py   #   SHAP feature attribution
|   |-- anomaly_detector.py #   Isolation Forest anomaly detection
|   `-- automl_tuner.py     #   Optuna hyperparameter tuning
|-- training/               # Offline training scripts
|-- api/                    # FastAPI app and routes
|-- ui_components/          # Styling, legends, reports
|-- utils/                  # Caching, logging, alerts
|-- tests/                  # Unit/integration tests
`-- models/                 # Serialized .joblib / .pt models
```

---

## Training Models

Pre-trained `.joblib` files are expected in `models/`. To retrain:

```bash
# Traditional ML classifiers
python training/train_flood_risk.py
python training/train_sar_classifier.py
python training/train_xgb_classifier.py
python training/train_lgbm_classifier.py
python training/tune_hyperparams.py
```

The LSTM flood forecaster and foundation model classifiers train on-the-fly when first used via the Streamlit UI.

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

**Core:**

```
streamlit, earthengine-api, folium, streamlit-folium, pandas, numpy, requests
```

**ML:**

```
scikit-learn, xgboost, lightgbm, optuna, shap, joblib, matplotlib
```

**Backend:**

```
fastapi, uvicorn, pydantic
```

**Visualization/Reports:**

```
fpdf2, pydeck
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
