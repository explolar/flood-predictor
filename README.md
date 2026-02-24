# HydroRisk Atlas
### Flood Risk Intelligence Platform · IIT Kharagpur

A satellite-powered flood risk assessment dashboard built with **Google Earth Engine**, **Sentinel-1 SAR**, and **Streamlit**. Designed for rapid geospatial flood analysis at 30m resolution using multi-source Earth observation data.

---

## Features

### Phase 1 — MCA Susceptibility Mapping
- Multi-Criteria Analysis combining LULC, slope, and rainfall into a 1–5 hazard rank
- Interactive weight sliders (LULC / Slope / Rainfall %)
- AOI terrain statistics (area, elevation range, mean slope)
- Optional overlays: JRC Flood Frequency, Sentinel-2 True Color, HydroSHEDS Watershed

### Phase 2 — SAR Inundation Detection
- Sentinel-1 change detection between user-defined pre/post flood windows
- VH / VV polarization toggle
- Lee speckle filter (focal mean 3×3)
- Adjustable backscatter threshold (0.5–6.0 dB)
- Six map views: Flood Mask, Severity Zones, Pre-SAR, Post-SAR, Change Intensity, NDVI Damage
- OSM infrastructure overlay (hospitals, schools, fire stations, police)
- Population exposure estimate (WorldPop 2020 · 100m)
- CHIRPS daily rainfall time series chart
- Gumbel flood return period analysis (2 / 5 / 10 / 25 / 50 / 100-year)

### Dual-View (Tab 3)
- Synchronized side-by-side pre/post SAR comparison using Folium DualMap
- Flood mask overlay on post-flood panel

### Flood Progression (Tab 4)
- Month-by-month monsoon progression (Jun–Oct) for any year 2019–2024
- CHIRPS monthly rainfall bar chart with season totals
- Per-month SAR flood mask relative to dry-season reference (Jan–Mar)

### Additional
- Place name search with auto-AOI (Nominatim geocoder)
- Coordinate click picker on the MCA map
- GeoJSON AOI upload
- Export: plain-text technical report, PDF report (fpdf2)
- All GEE tile computations cached (`@st.cache_data`) for instant tab switching

---

## Data Sources

| Dataset | Provider | Use |
|---------|----------|-----|
| Sentinel-1 GRD | ESA / Copernicus | SAR backscatter, flood detection |
| ESA WorldCover v200 | ESA | LULC classification |
| SRTM DEM 30m | USGS | Slope, terrain masking |
| CHIRPS Daily | UCSB-CHG | Rainfall time series, return period |
| JRC Global Surface Water | EC JRC | Flood frequency, permanent water mask |
| WorldPop 100m | WorldPop | Population exposure |
| Sentinel-2 SR | ESA / Copernicus | NDVI damage, true color |
| HydroSHEDS Basins L8 | WWF | Watershed delineation |
| OpenStreetMap | OSM / Overpass API | Infrastructure risk |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/flood-predictor.git
cd flood-predictor

# Install dependencies
pip install streamlit earthengine-api folium streamlit-folium pandas requests geopy fpdf2
```

### Google Earth Engine Authentication

```bash
earthengine authenticate
```

Then update the `project_id` variable in `app.py` with your GEE Cloud Project ID:

```python
project_id = 'your-gee-project-id'
```

---

## Usage

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

**Workflow:**
1. Search a place name or enter bounding box coordinates in the sidebar
2. Click **INITIALIZE AOI** to set the study area
3. Adjust MCA weights, SAR date windows, polarization, and threshold
4. Explore the four analysis tabs

---

## Dependencies

```
streamlit
earthengine-api
folium
streamlit-folium
pandas
requests
geopy          # optional — place name search
fpdf2          # optional — PDF report export
```

---

## Project Structure

```
flood-predictor/
├── app.py          # Main application (single-file Streamlit app)
└── README.md
```

---

## Screenshots

> Add screenshots of the MCA map, SAR dual-view, and progression tab here.

---

## Author

**Ankit Kumar**
Indian Institute of Technology Kharagpur

---

## License

MIT License — free to use and modify with attribution.
