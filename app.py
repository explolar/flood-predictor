import streamlit as st
import ee
import json
import datetime
import requests

from utils.logging_config import setup_logging
setup_logging()

# ── Module imports ─────────────────────────────────────
from ui_components.styles import inject_styles
from ui_components.reports import generate_report, generate_pdf_bytes
from ui_components.constants import CROP_PRICES

from gee_functions.core import _init_ee_core, initialize_ee

from tabs import (
    render_mca_tab,
    render_sar_tab,
    render_ml_tab,
    render_multiyear_tab,
    render_drought_tab,
    render_indices_tab,
)

# ==========================================
# 1. PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="HydroRisk Atlas | IIT Kgp", layout="wide", page_icon="🛰️")
inject_styles()

# ==========================================
# 2. SIDEBAR
# ==========================================
try:
    _init_ee_core()
except Exception:
    pass

with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand">
            <img src="https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png" width="60">
            <div class="brand-title">HYDRORISK</div>
            <div class="brand-sub">IIT Kharagpur · GEE</div>
        </div>
    """, unsafe_allow_html=True)

    if 'aoi' not in st.session_state:          st.session_state.aoi = None
    if 'map_center' not in st.session_state:   st.session_state.map_center = [25.61, 85.12]
    if 'clicked_coord' not in st.session_state: st.session_state.clicked_coord = None
    if 'rp_data' not in st.session_state:      st.session_state.rp_data = None

    st.markdown('<div class="section-tag">Location Search</div>', unsafe_allow_html=True)
    place_query = st.text_input("Place", placeholder="e.g. Patna, Bihar", label_visibility="collapsed")
    if st.button("SEARCH & SET AOI", use_container_width=True):
        if not place_query.strip():
            st.warning("Type a place name first.")
        else:
            try:
                with st.spinner("Searching..."):
                    resp = requests.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": place_query.strip(), "format": "json", "limit": 1},
                        headers={"User-Agent": "HydroRiskAtlas/1.0"},
                        timeout=10,
                    )
                    results = resp.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
                    d   = 0.25
                    st.session_state.aoi = ee.Geometry.BBox(lon-d, lat-d, lon+d, lat+d)
                    st.session_state._aoi_changed = True
                    st.session_state.map_center = [lat, lon]
                    st.success(f"✓ {results[0]['display_name'][:60]}")
                else:
                    st.warning(f'"{place_query}" not found. Try a more specific name.')
            except Exception as ex:
                st.error(f"Search failed: {ex}")

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">AOI Boundary</div>', unsafe_allow_html=True)
    input_method = st.radio("Boundary Mode", ("Bounding Box", "Upload GeoJSON"), label_visibility="collapsed")

    if input_method == "Bounding Box":
        c1, c2 = st.columns(2)
        with c1:
            min_lon = st.number_input("Min Lon", value=84.90, format="%.4f")
            min_lat = st.number_input("Min Lat", value=25.50, format="%.4f")
        with c2:
            max_lon = st.number_input("Max Lon", value=85.30, format="%.4f")
            max_lat = st.number_input("Max Lat", value=25.80, format="%.4f")
        if st.button("INITIALIZE AOI", use_container_width=True):
            st.session_state.aoi = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
            st.session_state._aoi_changed = True
            st.session_state.map_center = [(min_lat+max_lat)/2, (min_lon+max_lon)/2]
    else:
        uploaded_file = st.file_uploader("Upload District GeoJSON", type=["geojson","json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            coords = data["features"][0]["geometry"]["coordinates"]
            st.session_state.aoi = ee.Geometry.Polygon(coords)
            st.session_state._aoi_changed = True
            st.session_state.map_center = [coords[0][0][1], coords[0][0][0]]

    if st.session_state.aoi:
        st.markdown('<div class="status-pill" style="margin-top:8px;font-size:0.65rem;"><span class="status-dot"></span>AOI ACTIVE</div>', unsafe_allow_html=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">MCA Weights</div>', unsafe_allow_html=True)
    w_lulc  = st.slider("LULC %",  10, 80, 40, step=5)
    w_slope = st.slider("Slope %", 10, 80, 30, step=5)
    w_rain  = max(0, 100 - w_lulc - w_slope)
    st.markdown(f"""
        <div class="weight-row">LULC <span>{w_lulc}%</span></div>
        <div class="weight-row">Slope <span>{w_slope}%</span></div>
        <div class="weight-row">Rainfall <span>{w_rain}%</span></div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">SAR Engine Windows</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)
    with colA:
        p_start = st.date_input("Pre Start",  datetime.date(2024, 5, 1))
        f_start = st.date_input("Post Start", datetime.date(2024, 8, 1))
    with colB:
        p_end   = st.date_input("Pre End",    datetime.date(2024, 5, 30))
        f_end   = st.date_input("Post End",   datetime.date(2024, 8, 30))

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">SAR Polarisation</div>', unsafe_allow_html=True)
    polarization = st.radio("Polarisation", ("VH", "VV"), horizontal=True, label_visibility="collapsed")

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Backscatter Threshold</div>', unsafe_allow_html=True)
    f_threshold = st.slider("Sensitivity (dB)", 0.5, 6.0, 3.0, step=0.25, label_visibility="collapsed")
    st.markdown(f'<div style="text-align:center;font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#64B5F6;margin-top:-8px;">{f_threshold} dB · {polarization}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Pre-processing</div>', unsafe_allow_html=True)
    apply_speckle = st.checkbox("Apply Speckle Filter (Lee 3×3)", value=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Flood Progression</div>', unsafe_allow_html=True)
    prog_year = st.selectbox("Year", [2019, 2020, 2021, 2022, 2023, 2024], index=5, label_visibility="collapsed")

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Crop Loss Assessment</div>', unsafe_allow_html=True)
    crop_type = st.selectbox("Crop Type", list(CROP_PRICES.keys()), label_visibility="collapsed")
    default_price = CROP_PRICES[crop_type]
    crop_price = st.number_input("Price (₹/ha)", min_value=0, value=default_price, step=5000, label_visibility="visible")

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Imagery Date Range</div>', unsafe_allow_html=True)
    colI1, colI2 = st.columns(2)
    with colI1:
        img_start = st.date_input("Start", datetime.date(2024, 1, 1), key="img_start")
    with colI2:
        img_end = st.date_input("End", datetime.date(2024, 12, 31), key="img_end")
    cloud_thresh = st.slider("Max Cloud Cover %", 10, 100, 60, step=5, key="cloud_thresh")
    st.markdown(f'<div style="text-align:center;font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#64B5F6;margin-top:-8px;">Scenes ≤ {cloud_thresh}% cloud</div>', unsafe_allow_html=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    if st.session_state.aoi:
        report = generate_report(
            [min_lon, min_lat, max_lon, max_lat] if input_method == "Bounding Box" else "GeoJSON Uploaded",
            {"lulc": w_lulc, "slope": w_slope, "rain": w_rain},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end,
             "threshold": f_threshold, "polarization": polarization, "speckle": apply_speckle},
            {"area_ha": st.session_state.get('area_ha', 0),
             "pop_exposed": st.session_state.get('pop_exposed', 'N/A')}
        )
        st.download_button("EXPORT TECH REPORT (.txt)", report, file_name="HydroRisk_Atlas_Report.txt", use_container_width=True)

        pdf_bytes = generate_pdf_bytes(
            [min_lon, min_lat, max_lon, max_lat] if input_method == "Bounding Box" else "GeoJSON",
            {"lulc": w_lulc, "slope": w_slope, "rain": w_rain},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end,
             "threshold": f_threshold, "polarization": polarization, "speckle": apply_speckle},
            {"area_ha": st.session_state.get('area_ha', 0),
             "pop_exposed": st.session_state.get('pop_exposed', 'N/A')},
            rp_data=st.session_state.get('rp_data')
        )
        if pdf_bytes:
            st.download_button("EXPORT PDF REPORT (.pdf)", pdf_bytes, file_name="HydroRisk_Atlas_Report.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.caption("Install fpdf2 for PDF export")

# ==========================================
# 3. MAIN RENDER
# ==========================================
st.markdown("""
    <div class="page-header">
        <h1>HYDRORISK ATLAS</h1>
        <div class="subtitle">Sentinel-1 SAR · Sentinel-2 SR · CHIRPS · SRTM DEM · 10–30 m</div>
    </div>
""", unsafe_allow_html=True)

initialize_ee()

with st.expander("METHODOLOGY", expanded=False):
    st.markdown(f"""
    <div class="tech-panel">
        <p><strong>Risk (MCA):</strong> LULC {w_lulc}% + Slope {w_slope}% + Rainfall {w_rain}% → 1–5 hazard rank at 30 m</p>
        <p><strong>SAR Detection:</strong> Sentinel-1 {polarization} change-detection, {f_threshold} dB threshold, slope mask &lt;8°{', speckle filtered' if apply_speckle else ''}</p>
        <p><strong>Indices:</strong> 7 spectral indices from Sentinel-2 SR composite (10 m)</p>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    " RISK ", " SAR ", " ML ", " CLIMATE ", " INDICES "
])

if st.session_state.aoi:
    # Cache the serialized AOI to avoid a blocking .getInfo() on every rerender
    if 'aoi_json' not in st.session_state or st.session_state.get('_aoi_changed', False):
        st.session_state.aoi_json = json.dumps(st.session_state.aoi.getInfo())
        st.session_state._aoi_changed = False
    _aoi_json = st.session_state.aoi_json

    # Bundle all sidebar params for tab functions
    params = {
        'w_lulc': w_lulc, 'w_slope': w_slope, 'w_rain': w_rain,
        'f_start': f_start, 'f_end': f_end, 'p_start': p_start, 'p_end': p_end,
        'f_threshold': f_threshold, 'polarization': polarization,
        'apply_speckle': apply_speckle, 'prog_year': prog_year,
        'crop_type': crop_type, 'crop_price': crop_price,
        'img_start': img_start, 'img_end': img_end, 'cloud_thresh': cloud_thresh,
        'aoi': st.session_state.aoi, 'map_center': st.session_state.map_center,
    }

    with tab1:
        render_mca_tab(_aoi_json, params)
    with tab2:
        render_sar_tab(_aoi_json, params)
    with tab3:
        render_ml_tab(_aoi_json, params)
    with tab4:
        # Climate tab: multi-year + drought as sub-tabs
        climate_t1, climate_t2 = st.tabs(["  MULTI-YEAR  ", "  DROUGHT  "])
        with climate_t1:
            render_multiyear_tab(_aoi_json, params)
        with climate_t2:
            render_drought_tab(_aoi_json, params)
    with tab5:
        render_indices_tab(_aoi_json, params)

else:
    st.markdown("""
        <div style="text-align:center; padding:50px 20px;">
            <div style="font-size:2.4rem; margin-bottom:12px;">🛰️</div>
            <div style="font-family:'Inter',sans-serif; font-size:1.1rem; letter-spacing:2px; color:#90CAF9; margin-bottom:8px;">NO STUDY AREA DEFINED</div>
            <div style="font-size:0.8rem; color:#546E7A; font-family:'Inter',sans-serif;">
                Use the sidebar to search a location or define a bounding box, then click <strong style="color:#64B5F6;">INITIALIZE AOI</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
