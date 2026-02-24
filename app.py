import streamlit as st
import ee
import folium
import json
import streamlit.components.v1 as components
import datetime
from streamlit_folium import folium_static

# ==========================================
# 1. CYBER-DARK UI & CUSTOM STYLING
# ==========================================
st.set_page_config(page_title="Global Risk Atlas | 30m", layout="wide", page_icon="🌍")

st.markdown("""
    <style>
    /* Dark Theme & Neon Typography */
    .stApp { background: radial-gradient(circle at top right, #0d1b2a, #1b263b, #000000); color: #e0e1dd; }
    h1, h2, h3 { color: #00FFFF !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0,255,255,0.5); }
    
    /* Glassmorphism Components */
    [data-testid="stSidebar"] { background-color: rgba(13, 27, 42, 0.95); backdrop-filter: blur(15px); border-right: 2px solid #00FFFF; }
    .metric-card {
        background: rgba(27, 38, 59, 0.6); border: 1px solid #00FFFF; border-radius: 15px;
        padding: 20px; box-shadow: 0 4px 20px rgba(0, 255, 255, 0.2); text-align: center;
    }
    .tech-glass {
        background: rgba(255, 255, 255, 0.05); border-left: 5px solid #00FFFF;
        padding: 20px; border-radius: 8px; margin-bottom: 25px; font-size: 0.95rem;
    }
    
    /* Neon Action Button */
    .stButton>button {
        background: linear-gradient(45deg, #00FFFF, #008080); color: black !important;
        border: none; font-weight: bold; border-radius: 25px; transition: all 0.3s ease;
    }
    .stButton>button:hover { box-shadow: 0 0 25px #00FFFF; transform: scale(1.03); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. HAZARD RANKING LEGENDS & TOOLS
# ==========================================
def get_mca_legend():
    return '''
    <div style="position: fixed; bottom: 30px; left: 30px; width: 140px; background-color: rgba(13,27,42,0.9); 
    border: 1px solid #00FFFF; color: white; z-index:9999; font-size:11px; padding: 10px; border-radius: 10px; backdrop-filter: blur(5px);">
    <b style="color:#00FFFF">Risk Index</b><br>
    <i class="fa fa-square" style="color:#d73027"></i> Very High (5)<br>
    <i class="fa fa-square" style="color:#fc8d59"></i> High (4)<br>
    <i class="fa fa-square" style="color:#ffffbf"></i> Moderate (3)<br>
    <i class="fa fa-square" style="color:#91cf60"></i> Low (2)<br>
    <i class="fa fa-square" style="color:#1a9850"></i> Very Low (1)
    </div>
    '''

def get_sar_legend():
    return '''
    <div style="position: fixed; bottom: 30px; left: 30px; width: 150px; background-color: rgba(13,27,42,0.9); 
    border: 1px solid #00FFFF; color: white; z-index:9999; font-size:11px; padding: 10px; border-radius: 10px; backdrop-filter: blur(5px);">
    <b style="color:#00FFFF">SAR Indicators</b><br>
    <i class="fa fa-square" style="color:#00FFFF"></i> Active Flood<br>
    <i class="fa fa-square" style="color:#00008B"></i> Permanent Water<br>
    <hr style="margin:5px 0; border-color:#30363D">
    <small><i>Terrain Guard: Active</i></small>
    </div>
    '''

def generate_report(aoi_coords, mca_weights, sar_params, results):
    """Generates a professional text summary for MTP defense."""
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
==================================================
HYDRO-CLIMATIC RISK ATLAS - TECHNICAL REPORT
Generated: {now}
==================================================
INVESTIGATOR: Ankit Kumar
INSTITUTION: IIT Kharagpur
--------------------------------------------------
1. STUDY AREA (AOI): {aoi_coords}
2. MCA WEIGHTS: LULC={mca_weights['lulc']}%, Slope={mca_weights['slope']}%, Rain={mca_weights['rain']}%
3. SAR WINDOWS: Pre({sar_params['pre_start']} to {sar_params['pre_end']}), Post({sar_params['f_start']} to {sar_params['f_end']})
4. INUNDATED AREA: {results['area_ha']} Ha
==================================================
"""

# ==========================================
# 3. INITIALIZATION
# ==========================================
project_id = 'xward-481405'

def initialize_ee():
    try:
        try:
            from ee import compute_engine
            creds = compute_engine.ComputeEngineCredentials()
            ee.Initialize(creds, project=project_id)
        except:
            ee.Initialize(project=project_id)
        ee.Image('USGS/SRTMGL1_003').getInfo()
        st.success("🛰️ Global Satellite Connection: STABLE")
    except Exception as e:
        st.error(f"❌ Handshake Failed: {e}")

initialize_ee()

# ==========================================
# 4. SIDEBAR & AOI
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png", width=90)
    st.title("Global Risk Control")
    st.markdown("---")
    
    input_method = st.radio("Boundary Mode", ("Bounding Box", "Upload GeoJSON"), label_visibility="collapsed")
    if 'aoi' not in st.session_state: st.session_state.aoi = None
    if 'map_center' not in st.session_state: st.session_state.map_center = [25.61, 85.12]

    if input_method == "Bounding Box":
        c1, c2 = st.columns(2)
        with c1: min_lon = st.number_input("Min Lon", value=84.90, format="%.4f")
        with c1: min_lat = st.number_input("Min Lat", value=25.50, format="%.4f")
        with c2: max_lon = st.number_input("Max Lon", value=85.30, format="%.4f")
        with c2: max_lat = st.number_input("Max Lat", value=25.80, format="%.4f")
        if st.button("🚀 INITIALIZE AOI"):
            st.session_state.aoi = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
            st.session_state.map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    else:
        uploaded_file = st.file_uploader("Upload District GeoJSON", type=["geojson", "json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            coords = data["features"][0]["geometry"]["coordinates"]
            st.session_state.aoi = ee.Geometry.Polygon(coords)
            st.session_state.map_center = [coords[0][0][1], coords[0][0][0]]

    st.markdown("---")
    st.markdown("### 📡 SAR Engine Windows")
    colA, colB = st.columns(2)
    with colA:
        p_start = st.date_input("Pre-Start", datetime.date(2024, 5, 1))
        f_start = st.date_input("Post-Start", datetime.date(2024, 8, 1))
    with colB:
        p_end = st.date_input("Pre-End", datetime.date(2024, 5, 30))
        f_end = st.date_input("Post-End", datetime.date(2024, 8, 30))
    
    f_threshold = st.slider("Sensitivity (dB)", 1.0, 5.0, 1.25)
    
    st.markdown("---")
    if st.session_state.aoi:
        report = generate_report(
            [min_lon, min_lat, max_lon, max_lat] if input_method=="Bounding Box" else "GeoJSON Uploaded",
            {"lulc": 40, "slope": 30, "rain": 30},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end, "threshold": f_threshold},
            {"area_ha": st.session_state.get('area_ha', 0)}
        )
        st.download_button("📊 DOWNLOAD TECH REPORT", report, file_name="Risk_Atlas_Report.txt", use_container_width=True)

# ==========================================
# 5. CORE ANALYTICAL PIPELINES
# ==========================================
def calculate_flood_risk(aoi_geom):
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    slope_r = slope.where(slope.lte(2), 5).where(slope.gt(20), 1)
    lulc = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom)
    lulc_r = lulc.remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate('2023-01-01', '2024-01-01').sum().clip(aoi_geom)
    rain_r = rain.where(rain.lt(1860), 1).where(rain.gte(1950), 5)
    return lulc_r.multiply(0.40).add(slope_r.multiply(0.30)).add(rain_r.multiply(0.30)).clip(aoi_geom).round()

def calculate_sar_flood(aoi_geom, start_date, end_date, p_s, p_e, threshold):
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi_geom).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')).select('VH')
    pre = s1.filterDate(str(p_s), str(p_e)).median().clip(aoi_geom)
    post = s1.filterDate(str(start_date), str(end_date)).median().clip(aoi_geom)
    slope_mask = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)).lt(8)
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom)
    flooded = pre.subtract(post).gt(threshold).updateMask(slope_mask).where(water, 0)
    return flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded), water.updateMask(water)

# ==========================================
# 6. DASHBOARD MAIN RENDER
# ==========================================
st.title("🛰️ Global Hydro-Climatic Risk Atlas")

with st.expander("🛠️ TECHNICAL CALCULATION BASIS & LOGIC", expanded=True):
    st.markdown("""
    <div class="tech-glass">
        <h4>Phase 1: MCA Calculation</h4>
        <p><b>Weights:</b> LULC (40%) + Slope (30%) + Rainfall (30%). Hazard ranks (1-5).</p>
        <hr style="border-color:rgba(0,255,255,0.2)">
        <h4>Phase 2: SAR Inundation Logic</h4>
        <p><b>Terrain Guard:</b> Strictly masks areas with <code>Slope > 8°</code> to prevent <b>Radar Shadows</b> in <b>Manali/Naggar</b>.</p>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Phase 1: Susceptibility (MCA)", "🛰️ Phase 2: Active Inundation (SAR)"])

if st.session_state.aoi:
    with tab1:
        risk = calculate_flood_risk(st.session_state.aoi)
        c1, c2 = st.columns([1, 2.5])
        with c1:
            st.markdown('<div class="metric-card"><h3>MCA Active</h3><p>30m Modeling</p></div>', unsafe_allow_html=True)
            try:
                mca_url = risk.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("💾 DOWNLOAD MCA MAP", mca_url, use_container_width=True)
            except: st.warning("Area too large for direct MCA download.")
        with c2:
            m1 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.TileLayer(tiles=risk.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format, attr='GEE', name='Risk Score').add_to(m1)
            m1.get_root().html.add_child(folium.Element(get_mca_legend()))
            folium_static(m1, height=550)

    with tab2:
        with st.spinner('📡 Scanning Global Backscatter...'):
            flood, water = calculate_sar_flood(st.session_state.aoi, f_start, f_end, p_start, p_end, f_threshold)
            stats = flood.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=st.session_state.aoi, scale=50, maxPixels=1e9)
            area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0
            st.session_state.area_ha = area_ha

            col1, col2 = st.columns([1, 2.5])
            with col1:
                st.markdown(f'<div class="metric-card"><h1>{area_ha} Ha</h1><p style="color:#00FFFF;">INUNDATED AREA</p></div>', unsafe_allow_html=True)
                try: sar_url = flood.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                except: sar_url = flood.getDownloadUrl({'scale': 100, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("💾 DOWNLOAD SAR MASK", sar_url, use_container_width=True)
            with col2:
                m2 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=water.getMapId({'palette':['#00008B']})['tile_fetcher'].url_format, attr='GEE', name='Permanent').add_to(m2)
                folium.TileLayer(tiles=flood.getMapId({'palette':['#00FFFF']})['tile_fetcher'].url_format, attr='GEE', name='Active Flood').add_to(m2)
                m2.get_root().html.add_child(folium.Element(get_sar_legend()))
                folium_static(m2, height=550)
else:
    st.info("👈 Use the neon sidebar to define your study area and click 'Initialize AOI'.")