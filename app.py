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
# 2. LEGEND HELPERS
# ==========================================
def get_mca_legend():
    return '''
    <div style="position: fixed; bottom: 30px; left: 30px; width: 140px; background-color: rgba(13,27,42,0.9); 
    border: 1px solid #00FFFF; color: white; z-index:9999; font-size:11px; padding: 10px; border-radius: 10px;">
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
    border: 1px solid #00FFFF; color: white; z-index:9999; font-size:11px; padding: 10px; border-radius: 10px;">
    <b style="color:#00FFFF">SAR Indicators</b><br>
    <i class="fa fa-square" style="color:#00FFFF"></i> Active Flood<br>
    <i class="fa fa-square" style="color:#00008B"></i> Permanent Water<br>
    <hr style="margin:5px 0; border-color:#30363D">
    <small><i>Terrain Guard: Active</i></small>
    </div>
    '''

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
# 4. SIDEBAR & GLOBAL AOI
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
    st.markdown("### 📡 SAR Engine Settings")
    f_start = st.date_input("Post-Flood Analysis Start", datetime.date(2024, 8, 1))
    f_threshold = st.slider("Sensitivity (dB)", 1.0, 5.0, 1.25)
    
    st.markdown("---")
    st.caption("Developed by Ankit Kumar | IIT Kharagpur")

# ==========================================
# 5. CORE ANALYTICAL PIPELINES
# ==========================================
def calculate_flood_risk(aoi_geom):
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope_r = ee.Terrain.slope(dem).where(ee.Terrain.slope(dem).lte(2), 5).where(ee.Terrain.slope(dem).gt(20), 1)
    lulc_r = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom).remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    return lulc_r.multiply(0.40).add(slope_r.multiply(0.60)).clip(aoi_geom).round()

def calculate_sar_flood(aoi_geom, start_date, threshold):
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(aoi_geom).filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')).select('VH')
    pre = s1.filterDate('2024-05-01', '2024-05-30').median().clip(aoi_geom)
    post = s1.filterDate(str(start_date), str(start_date + datetime.timedelta(days=30))).median().clip(aoi_geom)
    
    # Terrain Guard: Vital for mountain areas like Naggar/Manali
    slope_mask = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)).lt(8)
    permanent_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom)
    
    flooded = pre.subtract(post).gt(threshold).updateMask(slope_mask).where(permanent_water, 0)
    return flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded), permanent_water.updateMask(permanent_water)

# ==========================================
# 6. DASHBOARD MAIN RENDER
# ==========================================
st.title("🛰️ Global Hydro-Climatic Risk Atlas")

with st.expander("🛠️ TECHNICAL METHODOLOGY & LOGIC", expanded=True):
    st.markdown("""
    <div class="tech-glass">
        <b>Terrain Guard:</b> SRTM 30m Slope Mask (<code>Slope < 8°</code>) eliminates <b>Radar Shadows</b> in <b>Manali/Naggar</b>.<br>
        <b>SAR Pipeline:</b> Refined log-ratio backscatter difference with focal smoothing.<br>
        <b>Dashboard Resolution:</b> 30m Native | 50m Area Stats Optimized.
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Phase 1: Susceptibility (MCA)", "🛰️ Phase 2: Active Inundation (SAR)"])

if st.session_state.aoi is not None:
    with tab1:
        risk = calculate_flood_risk(st.session_state.aoi)
        m1 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
        folium.TileLayer(tiles=risk.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format, attr='GEE', name='Risk Score').add_to(m1)
        m1.get_root().html.add_child(folium.Element(get_mca_legend()))
        folium_static(m1, height=600)

    with tab2:
        with st.spinner('📡 Scanning Global Microwave Backscatter...'):
            flood, water = calculate_sar_flood(st.session_state.aoi, f_start, f_threshold)
            stats = flood.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=st.session_state.aoi, scale=50, maxPixels=1e9)
            area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0

            col1, col2 = st.columns([1, 2.5])
            with col1:
                st.markdown(f"""<div class="metric-card"><h1>{area_ha} Ha</h1><p style='color:#00FFFF;'>INUNDATED AREA</p></div>""", unsafe_allow_html=True)
                st.markdown("### 📥 Technical Exports")
                try: # Smart Download Fallback for 50MB limit
                    d_url = flood.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                except:
                    d_url = flood.getDownloadUrl({'scale': 100, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                    st.warning("⚠️ High-res exceeds 50MB limit; downloading 100m fallback.")
                st.link_button("💾 DOWNLOAD GEOTIFF", d_url, use_container_width=True)
            
            with col2:
                m2 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=water.getMapId({'palette':['#00008B']})['tile_fetcher'].url_format, attr='GEE', name='Permanent').add_to(m2)
                folium.TileLayer(tiles=flood.getMapId({'palette':['#00FFFF']})['tile_fetcher'].url_format, attr='GEE', name='Active Flood').add_to(m2)
                m2.get_root().html.add_child(folium.Element(get_sar_legend()))
                folium_static(m2, height=550)
else:
    st.info("👈 Use the neon sidebar to define your study area and click 'Initialize AOI'.")