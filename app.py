import streamlit as st
import ee
import folium
import json
import streamlit.components.v1 as components
import datetime

# ==========================================
# 1. STYLING
# ==========================================
st.set_page_config(page_title="Bihar Risk Atlas | 30m", layout="wide", page_icon="🌍")

st.markdown("""
    <style>
    /* Dark Theme & Typography */
    .stApp { background: radial-gradient(circle at top right, #0d1b2a, #1b263b, #000000); color: #e0e1dd; }
    h1, h2, h3 { color: #00FFFF !important; font-family: 'Courier New', monospace; text-shadow: 0 0 10px rgba(0,255,255,0.5); }
    
    /* Neon Sidebar Styling */
    [data-testid="stSidebar"] { background-color: rgba(13, 27, 42, 0.95); backdrop-filter: blur(15px); border-right: 2px solid #00FFFF; }
    
    /* Glassmorphism Metric Card */
    .metric-card {
        background: rgba(27, 38, 59, 0.6);
        border: 1px solid #00FFFF;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0, 255, 255, 0.2);
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* Technical methodology block */
    .tech-glass {
        background: rgba(255, 255, 255, 0.05);
        border-left: 5px solid #00FFFF;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        font-size: 0.95rem;
    }
    
    /* Neon Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #00FFFF, #008080);
        color: black !important;
        border: none;
        font-weight: bold;
        border-radius: 25px;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover { box-shadow: 0 0 25px #00FFFF; transform: scale(1.03); }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2.INITIALIZATION
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
        st.success("🛰️ Satellite Connection: STABLE")
    except Exception as e:
        st.error(f"❌ Handshake Failed: {e}")

initialize_ee()

# ==========================================
# 3. INTERACTIVE SIDEBAR & PARAMETERS
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png", width=90)
    st.title("Risk Control")
    st.markdown("---")
    
    input_method = st.radio("Boundary Mode", ("Bounding Box", "Upload GeoJSON"), label_visibility="collapsed")
    aoi = None
    map_center = [25.61, 85.12]

    if input_method == "Bounding Box":
        c1, c2 = st.columns(2)
        with c1: min_lon = st.number_input("Min Lon", value=84.90, format="%.4f")
        with c1: min_lat = st.number_input("Min Lat", value=25.50, format="%.4f")
        with c2: max_lon = st.number_input("Max Lon", value=85.30, format="%.4f")
        with c2: max_lat = st.number_input("Max Lat", value=25.80, format="%.4f")
        if st.button("🚀 INITIATE AOI"):
            aoi = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
            map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    else:
        uploaded_file = st.file_uploader("Upload District GeoJSON", type=["geojson", "json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            coords = data["features"][0]["geometry"]["coordinates"]
            aoi = ee.Geometry.Polygon(coords)
            map_center = [coords[0][0][1], coords[0][0][0]]

    st.markdown("---")
    st.markdown("### 📡 SAR Engine Settings")
    p_start = st.date_input("Pre-Flood", datetime.date(2024, 5, 1))
    f_start = st.date_input("Post-Flood", datetime.date(2024, 8, 1))
    f_threshold = st.slider("Sensitivity (dB)", 1.0, 5.0, 1.25)
    
    st.markdown("---")
    st.caption("Developed by Ankit Kumar | M.Tech Scholar")
    st.caption("Land and Water Resources Engineering | IIT Kharagpur")

# ==========================================
# 4. MAIN INTERFACE & TECHNICAL BLOCK
# ==========================================
st.title("🛰️ Bihar Hydro-Climatic Risk Atlas")

with st.expander("🛠️ TECHNICAL METHODOLOGY & LOGIC", expanded=True):
    st.markdown(f"""
    <div class="tech-glass">
        <b>Architecture:</b> Multi-Criteria Analysis (MCA) & Sentinel-1 SAR Change Detection.<br>
        <b>Terrain Guard:</b> SRTM 30m Slope Mask (<code>Slope < 8°</code>) applied to eliminate <b>Radar Shadows</b> in <b>Manali/Naggar</b>.<br>
        <b>SAR Pipeline:</b> Refined log-ratio backscatter difference with 60m focal smoothing.<br>
        <b>Scale:</b> 30m Native | 50m Dashboard optimized.
    </div>
    """, unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Phase 1: Susceptibility (MCA)", "🛰️ Phase 2: Active Inundation (SAR)"])

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
    
    slope_mask = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)).lt(8)
    flooded = pre.subtract(post).gt(threshold).updateMask(slope_mask)
    return flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded)

# ==========================================
# 6. DASHBOARD RENDER
# ==========================================
if aoi is not None:
    with tab1:
        risk = calculate_flood_risk(aoi)
        m1 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
        folium.TileLayer(tiles=risk.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format, attr='GEE', name='Risk Score').add_to(m1)
        folium_static(m1, height=600)

    with tab2:
        with st.spinner('📡 Scanning Microwave Backscatter...'):
            flood = calculate_sar_flood(aoi, f_start, f_threshold)
            stats = flood.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=50, maxPixels=1e9)
            area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"""<div class="metric-card"><h1>{area_ha} Ha</h1><p style='color:#00FFFF;'>INUNDATED EXTENT</p></div>""", unsafe_allow_html=True)
                st.markdown("### 📥 EXPORTS")
                d_url = flood.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("💾 DOWNLOAD GEO-TIFF", d_url, use_container_width=True)
            
            with col2:
                m2 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=flood.getMapId({'palette':['#00FFFF']})['tile_fetcher'].url_format, attr='GEE', name='Active Flood').add_to(m2)
                folium_static(m2, height=500)
else:
    st.info("👈 Use the neon sidebar to define your study area boundaries.")