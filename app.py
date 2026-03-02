import streamlit as st
import ee
import folium
from folium.plugins import Fullscreen, MiniMap, DualMap
import json
import streamlit.components.v1 as components
import datetime
import pandas as pd
from streamlit_folium import folium_static, st_folium
import requests

# ── Module imports ─────────────────────────────────────
from ui_components.styles import inject_styles
from ui_components.legends import get_mca_legend, get_sar_legend
from ui_components.reports import generate_report, generate_pdf_bytes
from ui_components.constants import CROP_PRICES

from gee_functions.core import _init_ee_core, initialize_ee, get_aoi_stats
from gee_functions.mca import calculate_flood_risk, get_mca_tile
from gee_functions.sar import (
    get_all_sar_data, get_flood_depth_tile,
    get_month_sar_tile, get_recession_data,
)
from gee_functions.chirps import get_chirps_series, get_return_period, get_progression_stats
from gee_functions.layers import (
    get_ndvi_tile, get_jrc_freq_tile, get_s2_rgb_tile,
    get_s2_rgb_tiles, get_jrc_flood_history,
)
from gee_functions.infrastructure import get_osm_infrastructure, get_osm_roads, get_dam_data
from gee_functions.crop import get_crop_loss_data
from gee_functions.watershed import get_watershed_geojson

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
            <img src="https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png" width="72"
                 style="filter:drop-shadow(0 0 10px rgba(0,255,255,0.3))">
            <div class="brand-title">RISK ATLAS</div>
            <div class="brand-sub">IIT Kharagpur · GEE 30m</div>
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
            st.session_state.map_center = [(min_lat+max_lat)/2, (min_lon+max_lon)/2]
    else:
        uploaded_file = st.file_uploader("Upload District GeoJSON", type=["geojson","json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            coords = data["features"][0]["geometry"]["coordinates"]
            st.session_state.aoi = ee.Geometry.Polygon(coords)
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
    st.markdown(f'<div style="text-align:center;font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#00FFFF;margin-top:-8px;">{f_threshold} dB · {polarization}</div>', unsafe_allow_html=True)

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
        <h1>HYDRO-CLIMATIC RISK ATLAS</h1>
        <div class="subtitle">SENTINEL-1 SAR · ESA WORLDCOVER · CHIRPS RAINFALL · SRTM DEM · 30m RESOLUTION</div>
    </div>
""", unsafe_allow_html=True)

initialize_ee()

with st.expander("ANALYTICAL METHODOLOGY", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="tech-panel">
            <h4>PHASE 1 — MCA SUSCEPTIBILITY</h4>
            <p>Multi-Criteria Analysis combining three weighted layers at native 30m resolution.</p><br>
            <span class="weight-badge">LULC {w_lulc}%</span>
            <span class="weight-badge">SLOPE {w_slope}%</span>
            <span class="weight-badge">RAINFALL {w_rain}%</span>
            <hr class="grid-line">
            <p>Each layer reclassified to a <code>1–5</code> hazard rank. Final score = weighted sum, rounded to integer class.</p>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="tech-panel">
            <h4>PHASE 2 — SAR INUNDATION DETECTION</h4>
            <p>Change-detection on Sentinel-1 <code>{polarization}</code> backscatter between pre-flood and post-flood windows.</p><br>
            <span class="weight-badge">{polarization} POLARISATION</span>
            <span class="weight-badge">SLOPE MASK &lt;8°</span>
            <span class="weight-badge">{'SPECKLE FILTERED' if apply_speckle else 'RAW SAR'}</span>
            <hr class="grid-line">
            <p>Terrain Guard excludes <code>slope &gt; 8°</code> to eliminate radar shadows. Threshold: <code>{f_threshold} dB</code>.</p>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  PHASE 1 · MCA  ", "  PHASE 2 · SAR  ", "  DUAL-VIEW  ",
    "  PROGRESSION  ", "  ML INTELLIGENCE  "
])

if st.session_state.aoi:
    _aoi_json = json.dumps(st.session_state.aoi.getInfo())

    # ════════════════════════════════════════
    # TAB 1 — MCA SUSCEPTIBILITY
    # ════════════════════════════════════════
    with tab1:
        with st.expander("AOI TERRAIN STATISTICS", expanded=True):
            with st.spinner("Computing terrain stats..."):
                stats = get_aoi_stats(_aoi_json)
            st.markdown(f"""<div class="stats-row">
                <div class="stat-chip"><b>{stats['area_km2']} km²</b>AOI Area</div>
                <div class="stat-chip"><b>{stats['elev_min']} m</b>Min Elevation</div>
                <div class="stat-chip"><b>{stats['elev_max']} m</b>Max Elevation</div>
                <div class="stat-chip"><b>{stats['elev_mean']} m</b>Mean Elevation</div>
                <div class="stat-chip"><b>{stats['slope_mean']}°</b>Mean Slope</div>
            </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("""<div class="metric-card"><div class="metric-label">MODEL STATUS</div>
                <div class="metric-value">MCA</div><div class="metric-sub">Multi-Criteria Analysis · Active</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""<div class="metric-card"><div class="metric-label">RESOLUTION</div>
                <div class="metric-value">30m</div><div class="metric-sub">Native GEE pixel scale</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            extra_layers = st.multiselect("Extra Layers", ["Flood Frequency (JRC)", "Sentinel-2 True Color", "Watershed (HydroSHEDS)"], default=[], label_visibility="visible")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.clicked_coord:
                clat, clon = st.session_state.clicked_coord
                st.markdown(f'<div class="coord-pill">📍 {clat}°N, {clon}°E</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                risk_img = calculate_flood_risk(st.session_state.aoi, w_lulc, w_slope, w_rain)
                mca_url  = risk_img.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("DOWNLOAD MCA GEOTIFF", mca_url, use_container_width=True)
            except Exception:
                st.warning("Area too large for direct download.")

        with c2:
            with st.spinner("Rendering MCA risk map..."):
                mca_tile = get_mca_tile(_aoi_json, w_lulc, w_slope, w_rain)
            m1 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.GeoJson(st.session_state.aoi.getInfo(), name='AOI Boundary',
                style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(m1)
            if "Flood Frequency (JRC)" in extra_layers:
                with st.spinner("Loading JRC flood frequency..."):
                    jrc_tile = get_jrc_freq_tile(_aoi_json)
                folium.TileLayer(tiles=jrc_tile, attr='GEE·JRC', name='Flood Frequency', opacity=0.7).add_to(m1)
            if "Sentinel-2 True Color" in extra_layers:
                with st.spinner("Loading Sentinel-2 RGB..."):
                    s2_tile = get_s2_rgb_tile(_aoi_json)
                if s2_tile:
                    folium.TileLayer(tiles=s2_tile, attr='GEE·ESA', name='Sentinel-2 RGB', opacity=0.8).add_to(m1)
                else:
                    st.warning("Sentinel-2 true color unavailable — no cloud-free scenes for 2024.")
            if "Watershed (HydroSHEDS)" in extra_layers:
                with st.spinner("Loading watershed boundaries..."):
                    ws_geojson = get_watershed_geojson(_aoi_json)
                if ws_geojson:
                    folium.GeoJson(ws_geojson, name='Watershed Boundary',
                        style_function=lambda _: {'fillColor':'rgba(255,200,0,0.05)','color':'#FFD700','weight':1.5,'dashArray':'4 3'}).add_to(m1)
            folium.TileLayer(tiles=mca_tile, attr='GEE', name='Risk Score').add_to(m1)
            Fullscreen(position='topright', force_separate_button=True).add_to(m1)
            MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m1)
            folium.LayerControl(position='topright', collapsed=False).add_to(m1)
            m1.get_root().html.add_child(folium.Element(get_mca_legend(m1.get_name())))
            map_data = st_folium(m1, height=560, use_container_width=True, key="tab1_map", returned_objects=["last_clicked"])
            if map_data and map_data.get('last_clicked'):
                lc = map_data['last_clicked']
                st.session_state.clicked_coord = (round(lc['lat'], 5), round(lc['lng'], 5))

    # ════════════════════════════════════════
    # TAB 2 — SAR INUNDATION
    # ════════════════════════════════════════
    with tab2:
        with st.spinner(f'Querying Sentinel-1 {polarization} SAR archive...'):
            sar = get_all_sar_data(_aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
        st.session_state.area_ha = sar['area_ha']
        st.session_state.pop_exposed = f"{sar['pop_exposed']:,}"

        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"""<div class="metric-card"><div class="metric-label">INUNDATED AREA</div>
                <div class="metric-value">{sar['area_ha']}</div><div class="metric-sub">Hectares · post-event SAR</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""<div class="metric-card"><div class="metric-label">POPULATION EXPOSED</div>
                <div class="metric-value" style="font-size:1.8rem;">{sar['pop_exposed']:,}</div><div class="metric-sub">WorldPop 2020 · 100m</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""<div class="metric-card"><div class="metric-label">THRESHOLD · POLAR.</div>
                <div class="metric-value" style="font-size:1.6rem;">{f_threshold} dB</div><div class="metric-sub">{polarization} · {'Speckle filtered' if apply_speckle else 'Raw'}</div></div>""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            sar_view = st.radio("Map Layer", ("Flood Mask", "Severity Zones", "Flood Depth", "Pre-flood SAR", "Post-flood SAR", "Change Intensity", "NDVI Damage"), label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            show_infra = st.checkbox("Show Infrastructure (OSM)", value=False)
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button("DOWNLOAD FLOOD MASK", "#", use_container_width=True)

        with col2:
            m2 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.GeoJson(st.session_state.aoi.getInfo(), name='AOI Boundary',
                style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(m2)
            folium.TileLayer(tiles=sar['water_url'], attr='GEE', name='Permanent Water').add_to(m2)
            depth_data = None
            if sar_view == "Severity Zones":
                folium.TileLayer(tiles=sar['severity_url'], attr='GEE', name='Flood Severity').add_to(m2)
            elif sar_view == "Pre-flood SAR":
                folium.TileLayer(tiles=sar['pre_url'], attr='GEE', name=f'Pre-flood {polarization} (dB)').add_to(m2)
            elif sar_view == "Post-flood SAR":
                folium.TileLayer(tiles=sar['post_url'], attr='GEE', name=f'Post-flood {polarization} (dB)').add_to(m2)
            elif sar_view == "Change Intensity":
                folium.TileLayer(tiles=sar['diff_url'], attr='GEE', name='Backscatter Δ (dB)').add_to(m2)
            elif sar_view == "Flood Depth":
                with st.spinner("Estimating flood depth..."):
                    depth_data = get_flood_depth_tile(_aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
                if depth_data:
                    folium.TileLayer(tiles=depth_data['tile_url'], attr='GEE·SRTM', name='Flood Depth (m)').add_to(m2)
            elif sar_view == "NDVI Damage":
                with st.spinner("Computing NDVI damage..."):
                    ndvi_tile = get_ndvi_tile(_aoi_json, str(p_start), str(p_end), str(f_start), str(f_end))
                if ndvi_tile:
                    folium.TileLayer(tiles=ndvi_tile, attr='GEE·ESA', name='NDVI Damage (pre−post)').add_to(m2)
                else:
                    st.warning("NDVI Damage unavailable — no cloud-free Sentinel-2 scenes for the selected dates.")
            else:
                folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Active Flood').add_to(m2)
            if show_infra:
                with st.spinner("Fetching OSM infrastructure..."):
                    infra_data = get_osm_infrastructure(_aoi_json)
                icon_map = {'hospital': ('red','🏥'), 'school': ('blue','🏫'), 'fire_station': ('orange','🚒'), 'police': ('purple','🚓')}
                for feat in infra_data:
                    color, icon_emoji = icon_map.get(feat['type'], ('gray','📍'))
                    folium.CircleMarker(location=[feat['lat'], feat['lon']], radius=7, color=color, fill=True, fill_color=color, fill_opacity=0.7, tooltip=f"{icon_emoji} {feat['name']} ({feat['type']})").add_to(m2)
                if infra_data:
                    st.markdown(f"""<div class="infra-legend">
                        <span class="infra-chip"><span style="color:red">●</span>Hospital ({sum(1 for f in infra_data if f['type']=='hospital')})</span>
                        <span class="infra-chip"><span style="color:blue">●</span>School ({sum(1 for f in infra_data if f['type']=='school')})</span>
                        <span class="infra-chip"><span style="color:orange">●</span>Fire Stn ({sum(1 for f in infra_data if f['type']=='fire_station')})</span>
                        <span class="infra-chip"><span style="color:purple">●</span>Police ({sum(1 for f in infra_data if f['type']=='police')})</span>
                    </div>""", unsafe_allow_html=True)
            Fullscreen(position='topright', force_separate_button=True).add_to(m2)
            MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m2)
            folium.LayerControl(position='topright', collapsed=False).add_to(m2)
            m2.get_root().html.add_child(folium.Element(get_sar_legend(m2.get_name())))
            folium_static(m2, height=560)
            if sar_view == "Flood Depth" and depth_data:
                volume_Mm3 = round(sar['area_ha'] * 10000 * depth_data['mean_depth'] / 1e6, 3)
                dm1, dm2_col, dm3, dm4 = st.columns(4)
                dm1.metric("Mean Flood Depth", f"{depth_data['mean_depth']} m")
                dm2_col.metric("Max Flood Depth", f"{depth_data['max_depth']} m")
                dm3.metric("Flood Volume", f"{volume_Mm3} M m³")
                dm4.metric("Depth Scale", "0 – 4 m")
                if depth_data.get('histogram'):
                    hist = depth_data['histogram']
                    st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:10px 0 4px;">FLOOD DEPTH DISTRIBUTION · PIXEL COUNT PER DEPTH BAND</div>', unsafe_allow_html=True)
                    hist_df = pd.DataFrame({'Depth Band (m)': list(hist.keys()), 'Pixels': list(hist.values())}).set_index('Depth Band (m)')
                    st.bar_chart(hist_df, color="#fd8d3c", height=180)

        with st.expander("CHIRPS RAINFALL TIME SERIES", expanded=False):
            with st.spinner("Fetching CHIRPS daily rainfall..."):
                rain_df = get_chirps_series(_aoi_json, str(p_start), str(f_end))
            if rain_df is not None and not rain_df.empty:
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:rgba(0,255,255,0.5);letter-spacing:2px;margin-bottom:8px;">MEAN DAILY RAINFALL (mm) · AOI AVERAGE</div>', unsafe_allow_html=True)
                st.area_chart(rain_df, color="#00FFFF", height=200)
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Total Rainfall", f"{rain_df['rainfall_mm'].sum():.1f} mm")
                col_r2.metric("Peak Daily", f"{rain_df['rainfall_mm'].max():.1f} mm")
                col_r3.metric("Rainy Days", f"{(rain_df['rainfall_mm'] > 1).sum()}")
            else:
                st.info("No CHIRPS data available for the selected date range.")

        with st.expander("FLOOD RETURN PERIOD ANALYSIS  [Gumbel Distribution]", expanded=False):
            with st.spinner("Computing 24-year monsoon rainfall statistics..."):
                rp_data = get_return_period(_aoi_json)
            st.session_state.rp_data = rp_data
            if rp_data:
                col_rp1, col_rp2, col_rp3 = st.columns(3)
                col_rp1.metric("Mean Monsoon Rain", f"{rp_data['mean']:.0f} mm")
                col_rp2.metric("Std Deviation", f"± {rp_data['std']:.0f} mm")
                col_rp3.metric("Max Observed", f"{rp_data['max_obs']:.0f} mm")
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:12px 0 6px;">RETURN PERIOD TABLE · MONSOON TOTAL (Jun–Oct)</div>', unsafe_allow_html=True)
                max_rp = max(rp_data['return_periods'].values())
                rows_html = ''
                for T, val in rp_data['return_periods'].items():
                    bar_w = int(80 * val / max_rp)
                    rows_html += f'<tr><td>{T}-yr</td><td class="rp-val">{val:.0f} mm</td><td><span class="rp-bar" style="width:{bar_w}px;"></span></td></tr>'
                st.markdown(f'<table class="rp-table"><tr><th>RETURN PERIOD</th><th>RAINFALL</th><th>RELATIVE</th></tr>{rows_html}</table>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.7rem;color:#3a5060;font-family:JetBrains Mono,monospace;margin-top:10px;">Based on {rp_data["n_years"]} years CHIRPS · Gumbel extreme value distribution</div>', unsafe_allow_html=True)
            else:
                st.warning("Return period calculation failed. Check GEE connectivity.")

        with st.expander("CROP LOSS ASSESSMENT  [NDVI × WorldCover Cropland]", expanded=False):
            with st.spinner("Analysing cropland damage..."):
                crop_data = get_crop_loss_data(_aoi_json, str(p_start), str(p_end), str(f_start), str(f_end), crop_price)
            if crop_data:
                cl1, cl2, cl3, cl4 = st.columns(4)
                cl1.metric("Total Cropland", f"{crop_data['total_crop_ha']:,.0f} ha")
                cl2.metric("Damaged Area", f"{crop_data['damaged_ha']:,.0f} ha")
                cl3.metric("Damage %", f"{crop_data['damage_pct']:.1f} %")
                cl4.metric("Est. Crop Loss", f"₹ {crop_data['loss_estimate']:,}")
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:10px 0 4px;">NDVI DAMAGE ON CROPLAND · GREEN = HEALTHY · RED = DAMAGED</div>', unsafe_allow_html=True)
                crop_map = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=crop_data['tile_url'], attr='GEE·S2·ESA', name='Crop NDVI Damage').add_to(crop_map)
                folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(crop_map)
                folium_static(crop_map, height=400)
                st.markdown(f'<div style="font-size:0.7rem;color:#3a5060;font-family:JetBrains Mono,monospace;margin-top:8px;">Crop: {crop_type} · Price: ₹{crop_price:,}/ha · NDVI drop threshold: 0.10 · Source: Sentinel-2 SR + ESA WorldCover</div>', unsafe_allow_html=True)
            else:
                st.warning("Crop loss analysis unavailable. No Sentinel-2 data or no cropland in AOI.")

        with st.expander("JRC HISTORICAL FLOOD FREQUENCY  [1984 – 2021]", expanded=False):
            with st.spinner("Fetching 38-year JRC Monthly Water History..."):
                jrc_hist = get_jrc_flood_history(_aoi_json)
            if jrc_hist:
                jrc_df = pd.DataFrame({'Year': list(jrc_hist.keys()), 'Flood Months': list(jrc_hist.values())}).set_index('Year')
                total_flood_months = sum(jrc_hist.values())
                peak_yr = max(jrc_hist, key=jrc_hist.get)
                avg_months = round(total_flood_months / len(jrc_hist), 1)
                jh1, jh2, jh3 = st.columns(3)
                jh1.metric("Peak Flood Year", str(peak_yr))
                jh2.metric("Avg Flood Months/yr", f"{avg_months} mo")
                jh3.metric("Total Flood Months", f"{total_flood_months}")
                st.bar_chart(jrc_df, color="#2E86C1", height=220)
            else:
                st.warning("JRC flood history unavailable for this AOI.")

        with st.expander("ROAD NETWORK IMPACT  [OSM · Evacuation Routes]", expanded=False):
            with st.spinner("Fetching road network from OSM..."):
                road_data = get_osm_roads(_aoi_json)
            if road_data and road_data['roads']:
                hw_colors = {'motorway': '#e74c3c', 'trunk': '#e67e22', 'primary': '#f1c40f', 'secondary': '#2ecc71', 'tertiary': '#3498db', 'road': '#95a5a6'}
                evac_count = sum(1 for r in road_data['roads'] if r['evacuation'])
                rn1, rn2, rn3 = st.columns(3)
                total_km = sum(road_data['km_by_type'].values())
                rn1.metric("Total Road Length", f"{total_km:.1f} km")
                rn2.metric("Road Types", f"{len(road_data['km_by_type'])}")
                rn3.metric("Evacuation Routes", f"{evac_count} segments")
                road_map = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Flood Mask', opacity=0.55).add_to(road_map)
                for road in road_data['roads']:
                    color = '#00FF88' if road['evacuation'] else hw_colors.get(road['highway'], '#95a5a6')
                    weight = 4 if road['evacuation'] else 2
                    folium.PolyLine(locations=[[c[1], c[0]] for c in road['coords']], color=color, weight=weight, opacity=0.85, tooltip=f"{road['highway'].title()} · {road['name'] or 'unnamed'} · {road['length_km']} km").add_to(road_map)
                folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(road_map)
                folium_static(road_map, height=420)
                km_df = pd.DataFrame(list(road_data['km_by_type'].items()), columns=['Highway Type', 'Length (km)']).sort_values('Length (km)', ascending=False).set_index('Highway Type')
                st.dataframe(km_df, use_container_width=True)
            else:
                st.warning("No road data available for this AOI.")

        with st.expander("DAMS & RESERVOIRS UPSTREAM  [GRanD v1.3 · 150 km radius]", expanded=False):
            with st.spinner("Querying GRanD dam database..."):
                dam_list = get_dam_data(_aoi_json)
            if dam_list:
                dam_map = folium.Map(location=st.session_state.map_center, zoom_start=8, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Flood Mask', opacity=0.5).add_to(dam_map)
                folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(dam_map)
                for dam in dam_list:
                    cap = dam['capacity_mcm']
                    radius = max(6, min(22, int(cap ** 0.35))) if cap > 0 else 7
                    folium.CircleMarker(location=[dam['lat'], dam['lon']], radius=radius, color='#00BFFF', fill=True, fill_color='#00BFFF', fill_opacity=0.6,
                        tooltip=f"🏞 {dam['name']} · {dam['river']}<br>Capacity: {int(cap):,} MCM · Use: {dam['main_use']} · Built: {dam['year']}").add_to(dam_map)
                folium_static(dam_map, height=420)
                da1, da2, da3 = st.columns(3)
                da1.metric("Dams Found", f"{len(dam_list)}")
                da2.metric("Total Capacity", f"{sum(d['capacity_mcm'] for d in dam_list):,.0f} MCM")
                da3.metric("Largest Dam", dam_list[0]['name'] if dam_list else "—")
                dam_df = pd.DataFrame([{'Name': d['name'], 'River': d['river'], 'Capacity (MCM)': int(d['capacity_mcm']), 'Use': d['main_use'], 'Built': d['year']} for d in dam_list])
                st.dataframe(dam_df, use_container_width=True, hide_index=True)
            else:
                st.info("No dams found within 150 km of this AOI.")

        with st.expander("FLOOD RECESSION TRACKER  [SAR · +12 / +24 / +36 days]", expanded=False):
            with st.spinner("Computing post-event SAR flood extent (4 × 12-day windows)..."):
                recession = get_recession_data(_aoi_json, str(f_end), str(p_start), str(p_end), polarization, f_threshold, apply_speckle)
            if recession:
                valid = [r for r in recession if r['Flood Area (ha)'] is not None]
                if valid:
                    rec_df = pd.DataFrame(valid).set_index('Phase')
                    peak = rec_df['Flood Area (ha)'].max()
                    final = rec_df['Flood Area (ha)'].iloc[-1]
                    receded_pct = round(100 * (peak - final) / peak, 1) if peak > 0 else 0
                    rv1, rv2, rv3 = st.columns(3)
                    rv1.metric("Peak Flood Area", f"{peak:,.0f} ha")
                    rv2.metric("Latest Extent", f"{final:,.0f} ha")
                    rv3.metric("Area Receded", f"{receded_pct} %")
                    st.line_chart(rec_df, color="#FF6B6B", height=200)
                else:
                    st.info("No SAR imagery found in post-event windows.")
            else:
                st.warning("Recession analysis failed. Check GEE connectivity.")

    # ════════════════════════════════════════
    # TAB 3 — DUAL-VIEW
    # ════════════════════════════════════════
    with tab3:
        st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">SYNCHRONIZED PRE / POST SAR BACKSCATTER COMPARISON</div>', unsafe_allow_html=True)
        with st.spinner("Building dual-view SAR comparison..."):
            sar_d = get_all_sar_data(_aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
        st.markdown('<div class="dual-label-row"><div class="dual-label">◀ PRE-FLOOD SAR</div><div class="dual-label">POST-FLOOD SAR ▶</div></div>', unsafe_allow_html=True)
        dmap = DualMap(location=st.session_state.map_center, zoom_start=11, tiles=None, layout='horizontal')
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap.m1)
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap.m2)
        folium.TileLayer(tiles=sar_d['pre_url'], attr='GEE', name=f'Pre-flood {polarization}').add_to(dmap.m1)
        folium.TileLayer(tiles=sar_d['post_url'], attr='GEE', name=f'Post-flood {polarization}').add_to(dmap.m2)
        folium.TileLayer(tiles=sar_d['flood_url'], attr='GEE', name='Flood Mask', opacity=0.6).add_to(dmap.m2)
        folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(dmap.m1)
        folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(dmap.m2)
        components.html(dmap._repr_html_(), height=580, scrolling=False)
        d3c1, d3c2, d3c3 = st.columns(3)
        d3c1.metric("Pre-flood Period", f"{p_start} → {p_end}")
        d3c2.metric("Post-flood Period", f"{f_start} → {f_end}")
        d3c3.metric("Detected Flood", f"{sar_d['area_ha']} Ha")

        st.markdown('<hr style="border-color:rgba(0,255,255,0.1);margin:28px 0 20px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">SENTINEL-2 TRUE COLOR · PRE vs POST</div>', unsafe_allow_html=True)
        with st.spinner("Loading Sentinel-2 true-color imagery..."):
            s2_rgb = get_s2_rgb_tiles(_aoi_json, str(p_start), str(p_end), str(f_start), str(f_end))
        if s2_rgb:
            st.markdown('<div class="dual-label-row"><div class="dual-label">◀ PRE-FLOOD TRUE COLOR</div><div class="dual-label">POST-FLOOD TRUE COLOR ▶</div></div>', unsafe_allow_html=True)
            dmap_s2 = DualMap(location=st.session_state.map_center, zoom_start=11, tiles=None, layout='horizontal')
            folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap_s2.m1)
            folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap_s2.m2)
            folium.TileLayer(tiles=s2_rgb['pre_url'], attr='GEE·S2', name='Pre-flood S2').add_to(dmap_s2.m1)
            folium.TileLayer(tiles=s2_rgb['post_url'], attr='GEE·S2', name='Post-flood S2').add_to(dmap_s2.m2)
            folium.TileLayer(tiles=sar_d['flood_url'], attr='GEE', name='Flood Mask', opacity=0.5).add_to(dmap_s2.m2)
            folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(dmap_s2.m1)
            folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(dmap_s2.m2)
            components.html(dmap_s2._repr_html_(), height=520, scrolling=False)
        else:
            st.info("Sentinel-2 true-color unavailable — insufficient cloud-free scenes.")

    # ════════════════════════════════════════
    # TAB 4 — FLOOD PROGRESSION
    # ════════════════════════════════════════
    with tab4:
        st.markdown(f'<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">MONSOON FLOOD PROGRESSION · {prog_year}</div>', unsafe_allow_html=True)
        with st.spinner(f"Fetching {prog_year} CHIRPS monthly rainfall..."):
            prog_df = get_progression_stats(_aoi_json, prog_year)
        if prog_df is not None and not prog_df.empty:
            t4c1, t4c2 = st.columns([1, 2])
            with t4c1:
                chart_df = prog_df.set_index('Month')[['Rain (mm)']]
                st.bar_chart(chart_df, color="#FF6B6B", height=250)
                total_rain = prog_df['Rain (mm)'].sum()
                peak_month = prog_df.loc[prog_df['Rain (mm)'].idxmax(), 'Month']
                st.markdown(f'<div class="stats-row"><div class="stat-chip"><b>{total_rain:.0f} mm</b>Season Total</div><div class="stat-chip"><b>{peak_month}</b>Peak Month</div></div>', unsafe_allow_html=True)
            with t4c2:
                month_names = {'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10}
                prog_month = st.radio("Select month for SAR flood map", list(month_names.keys()), horizontal=True)
                prog_month_num = month_names[prog_month]
                with st.spinner(f"Computing SAR flood mask · {prog_month} {prog_year}..."):
                    prog_tile = get_month_sar_tile(_aoi_json, prog_year, prog_month_num, polarization, f_threshold, apply_speckle)
                m4 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(m4)
                folium.TileLayer(tiles=sar_d['water_url'], attr='GEE', name='Permanent Water').add_to(m4)
                if prog_tile:
                    folium.TileLayer(tiles=prog_tile, attr='GEE', name=f'Flood · {prog_month} {prog_year}', opacity=0.85).add_to(m4)
                Fullscreen(position='topright').add_to(m4)
                folium.LayerControl(position='topright', collapsed=False).add_to(m4)
                folium_static(m4, height=420)
            chips_html = ''.join(f'<span class="prog-month-chip">{row["Month"]} · {row["Rain (mm)"]} mm</span>' for _, row in prog_df.iterrows())
            st.markdown(f'<div>{chips_html}</div>', unsafe_allow_html=True)
        else:
            st.warning(f"Could not fetch CHIRPS data for {prog_year}.")

    # ════════════════════════════════════════
    # TAB 5 — ML INTELLIGENCE
    # ════════════════════════════════════════
    with tab5:
        st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">MACHINE LEARNING MODELS · FLOOD RISK · RAINFALL FORECAST · SAR CLASSIFICATION</div>', unsafe_allow_html=True)

        from ml_models.flood_risk_model import FloodRiskPredictor
        from ml_models.rainfall_forecast import RainfallForecaster
        from ml_models.sar_classifier import SARFloodClassifier

        # ── MODEL 1: FLOOD RISK PREDICTION ────────────
        with st.expander("MODEL 1 — FLOOD RISK PREDICTION  [Random Forest]", expanded=True):
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">GEE-SAMPLED FEATURES · SCIKIT-LEARN RF · 5-CLASS RISK</div>', unsafe_allow_html=True)
            if st.button("RUN ML RISK PREDICTION", key="ml_risk_btn", use_container_width=True):
                with st.spinner("Extracting features from GEE & running Random Forest..."):
                    try:
                        predictor = FloodRiskPredictor()
                        result = predictor.predict_for_aoi(_aoi_json)
                        if result and result.get('tile_url'):
                            mr1, mr2, mr3, mr4 = st.columns(4)
                            mr1.metric("Model", "Random Forest")
                            mr2.metric("Features", f"{len(predictor.feature_names)}")
                            mr3.metric("Samples", f"{result.get('n_samples', 'N/A')}")
                            mr4.metric("OOB Score", f"{result.get('oob_score', 'N/A')}")
                            ml_risk_map = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                            folium.TileLayer(tiles=result['tile_url'], attr='GEE·ML', name='ML Risk Prediction').add_to(ml_risk_map)
                            folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(ml_risk_map)
                            folium.LayerControl(position='topright', collapsed=False).add_to(ml_risk_map)
                            ml_risk_map.get_root().html.add_child(folium.Element(get_mca_legend(ml_risk_map.get_name())))
                            folium_static(ml_risk_map, height=450)
                            if result.get('feature_importance'):
                                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:14px 0 6px;">FEATURE IMPORTANCE</div>', unsafe_allow_html=True)
                                imp_df = pd.DataFrame(list(result['feature_importance'].items()), columns=['Feature', 'Importance']).sort_values('Importance', ascending=False).set_index('Feature')
                                st.bar_chart(imp_df, color="#00FFFF", height=200)
                        else:
                            st.warning("ML Risk prediction returned no results.")
                    except Exception as e:
                        st.error(f"ML Risk prediction failed: {e}")
            else:
                st.info("Click the button above to run the ML flood risk prediction model on the current AOI.")

        # ── MODEL 2: RAINFALL FORECAST ────────────────
        with st.expander("MODEL 2 — RAINFALL FORECAST  [Prophet]", expanded=False):
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">CHIRPS DATA · PROPHET · TIME-SERIES FORECASTING</div>', unsafe_allow_html=True)
            forecast_horizon = st.slider("Forecast horizon (days)", 7, 30, 14, key="forecast_horizon")
            if st.button("RUN RAINFALL FORECAST", key="ml_rain_btn", use_container_width=True):
                with st.spinner("Fetching CHIRPS data & fitting Prophet model..."):
                    try:
                        rain_data = get_chirps_series(_aoi_json, str(p_start), str(f_end))
                        if rain_data is not None and len(rain_data) >= 30:
                            forecaster = RainfallForecaster()
                            fc_result = forecaster.fit_and_forecast(rain_data, forecast_horizon)
                            fc1, fc2, fc3 = st.columns(3)
                            fc1.metric("Cumulative Forecast", f"{fc_result['cumulative_mm']} mm")
                            fc2.metric("Peak Daily Forecast", f"{fc_result['daily_peak_mm']} mm")
                            fc3.metric("90% CI Range", f"{fc_result['uncertainty_range'][0]}–{fc_result['uncertainty_range'][1]} mm")
                            fc_df = fc_result['forecast_df'].copy()
                            fc_df['ds'] = pd.to_datetime(fc_df['ds'])
                            fc_chart = fc_df.set_index('ds')[['yhat', 'yhat_lower', 'yhat_upper']]
                            fc_chart.columns = ['Forecast', 'Lower CI', 'Upper CI']
                            st.line_chart(fc_chart, height=250)
                            if st.session_state.rp_data:
                                flood_prob = forecaster.estimate_flood_probability(fc_result, st.session_state.rp_data)
                                risk_colors = {'LOW': '#1a9850', 'MODERATE': '#ffffbf', 'HIGH': '#fc8d59', 'VERY HIGH': '#d73027', 'EXTREME': '#67001f', 'UNKNOWN': '#666666'}
                                rl = flood_prob['risk_level']
                                rc = risk_colors.get(rl, '#666666')
                                st.markdown(f'<div style="display:inline-flex;align-items:center;gap:10px;background:rgba(0,255,255,0.04);border:1px solid {rc};border-radius:8px;padding:10px 18px;margin-top:10px;"><div style="width:12px;height:12px;background:{rc};border-radius:50%;"></div><div style="font-family:\'Rajdhani\',sans-serif;font-size:1rem;font-weight:700;color:{rc};letter-spacing:2px;">FLOOD RISK: {rl}</div><div style="font-family:\'JetBrains Mono\',monospace;font-size:0.72rem;color:#5a7a8a;">{flood_prob.get("return_period", "")}</div></div>', unsafe_allow_html=True)
                        else:
                            st.warning("Need at least 30 days of CHIRPS data.")
                    except ImportError:
                        st.error("Prophet is not installed. Run: pip install prophet")
                    except Exception as e:
                        st.error(f"Rainfall forecast failed: {e}")
            else:
                st.info("Click the button above to run the Prophet rainfall forecast.")

        # ── MODEL 3: SAR FLOOD CLASSIFICATION ─────────
        with st.expander("MODEL 3 — SAR FLOOD CLASSIFICATION  [Gradient Boosting]", expanded=False):
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">MULTI-FEATURE SAR · GRADIENT BOOSTED TREES · PIXEL-WISE</div>', unsafe_allow_html=True)
            show_probability = st.checkbox("Show probability heat map", key="ml_sar_prob")
            if st.button("RUN ML FLOOD CLASSIFICATION", key="ml_sar_btn", use_container_width=True):
                with st.spinner("Extracting SAR features & running Gradient Boosting..."):
                    try:
                        classifier = SARFloodClassifier()
                        result = classifier.classify_for_aoi(_aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle, return_probability=show_probability)
                        if result and result.get('tile_url'):
                            ms1, ms2, ms3, ms4 = st.columns(4)
                            ms1.metric("Model", "Gradient Boosting")
                            ms2.metric("ML Flood Area", f"{result.get('ml_area_ha', 0)} ha")
                            ms3.metric("Threshold Area", f"{result.get('threshold_area_ha', 0)} ha")
                            diff_ha = result.get('ml_area_ha', 0) - result.get('threshold_area_ha', 0)
                            ms4.metric("Difference", f"{diff_ha:+.1f} ha")
                            ml_sar_map = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                            folium.TileLayer(tiles=result['tile_url'], attr='GEE·ML', name='ML Flood Classification').add_to(ml_sar_map)
                            folium.GeoJson(st.session_state.aoi.getInfo(), style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}).add_to(ml_sar_map)
                            folium.LayerControl(position='topright', collapsed=False).add_to(ml_sar_map)
                            folium_static(ml_sar_map, height=450)
                            if result.get('feature_importance'):
                                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:14px 0 6px;">FEATURE IMPORTANCE</div>', unsafe_allow_html=True)
                                imp_df = pd.DataFrame(list(result['feature_importance'].items()), columns=['Feature', 'Importance']).sort_values('Importance', ascending=False).set_index('Feature')
                                st.bar_chart(imp_df, color="#FF6B6B", height=200)
                        else:
                            st.warning("ML SAR classification returned no results.")
                    except Exception as e:
                        st.error(f"ML SAR classification failed: {e}")
            else:
                st.info("Click the button above to run the ML-based SAR flood classification.")

        # ── MODEL DIAGNOSTICS ─────────────────────────
        with st.expander("MODEL DIAGNOSTICS", expanded=False):
            import os
            diag_data = []
            for name, path in [("Flood Risk RF", "models/flood_risk_rf.joblib"), ("SAR Classifier GB", "models/sar_classifier_gb.joblib")]:
                exists = os.path.exists(path)
                size = f"{os.path.getsize(path) / 1024:.1f} KB" if exists else "—"
                diag_data.append({"Model": name, "Status": "Trained" if exists else "Trains on-the-fly", "File": path, "Size": size})
            diag_data.append({"Model": "Rainfall Prophet", "Status": "Fits per-AOI at runtime", "File": "N/A", "Size": "—"})
            st.dataframe(pd.DataFrame(diag_data), use_container_width=True, hide_index=True)
            st.markdown("""<div class="tech-panel"><h4>TRAINING NOTES</h4>
                <p>Models 1 & 3 can be pre-trained via <code>training/</code> scripts. Without pre-trained models, they train on-the-fly using the current AOI (slower but no setup needed).</p>
                <p>Model 2 (Prophet) always fits at runtime since rainfall patterns are location-specific.</p></div>""", unsafe_allow_html=True)

else:
    st.markdown("""
        <div style="text-align:center; padding:60px 20px; animation: fadeUp 0.6s ease;">
            <div style="font-size:3rem; margin-bottom:16px; filter:drop-shadow(0 0 20px rgba(0,255,255,0.4));">🛰️</div>
            <div style="font-family:'Rajdhani',sans-serif; font-size:1.3rem; letter-spacing:3px; color:rgba(0,255,255,0.6); margin-bottom:10px;">NO STUDY AREA DEFINED</div>
            <div style="font-size:0.8rem; color:#3a5060; font-family:'Space Grotesk',sans-serif; letter-spacing:1px;">
                Use the sidebar to search a location or define a bounding box, then click <strong style="color:rgba(0,255,255,0.4);">INITIALIZE AOI</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
