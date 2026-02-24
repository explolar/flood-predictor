import streamlit as st
import ee
import folium
import json
import streamlit.components.v1 as components
import datetime

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(page_title="Hydro-Climatic Risk Atlas | 30m", layout="wide", page_icon="🌍")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stInfo { font-size: 0.9rem; border-left: 5px solid #00FFFF; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d1d1; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INITIALIZE EARTH ENGINE (Cloud Run Ready)
# ==========================================
project_id = 'xward-481405'

def initialize_ee():
    try:
        # Priority 1: Modern path for Cloud Run Identity
        try:
            from ee import compute_engine
            creds = compute_engine.ComputeEngineCredentials()
            ee.Initialize(creds, project=project_id)
        except (ImportError, AttributeError):
            # Priority 2: Standard auto-initialization (often works on GCP)
            ee.Initialize(project=project_id)
        
        # Connection check for your MTP research at IIT Kharagpur
        ee.data.getSTAC() 
        st.success("✅ Connected to Google Earth Engine")
    except Exception as e:
        st.error(f"❌ Initialization Failed: {e}")
        st.info("Ensure earthengine-api is listed in requirements.txt")

initialize_ee()
# ==========================================
# 3. HELPER FUNCTIONS (LEGENDS & UI)
# ==========================================
def get_mca_legend():
    return '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 140px; 
    background-color: rgba(255, 255, 255, 0.9); border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; border-radius: 5px;">
    <b>Risk Index</b><br>
    <i class="fa fa-square" style="color:#d73027"></i> Very High (5)<br>
    <i class="fa fa-square" style="color:#fc8d59"></i> High (4)<br>
    <i class="fa fa-square" style="color:#ffffbf"></i> Moderate (3)<br>
    <i class="fa fa-square" style="color:#91cf60"></i> Low (2)<br>
    <i class="fa fa-square" style="color:#1a9850"></i> Very Low (1)
    </div>
    '''

def get_sar_legend():
    return '''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 160px; height: 100px; 
    background-color: rgba(255, 255, 255, 0.9); border:2px solid grey; z-index:9999; font-size:12px; padding: 10px; border-radius: 5px;">
    <b>SAR Indicators</b><br>
    <i class="fa fa-square" style="color:#00FFFF"></i> Active Flood<br>
    <i class="fa fa-square" style="color:#00008B"></i> Permanent Water<br>
    <small><i>Topography Mask: Active</i></small>
    </div>
    '''

# ==========================================
# 4. SIDEBAR & AOI INITIALIZATION
# ==========================================
st.sidebar.title("⚙️ Project Parameters")

input_method = st.sidebar.radio("Input Method", ("Bounding Box", "Upload GeoJSON"), label_visibility="collapsed")
aoi = None
map_center = [25.61, 85.12] # Default center near Patna/Danapur

if input_method == "Bounding Box":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        min_lon = st.number_input("Min Lon", value=84.90, format="%.4f")
        min_lat = st.number_input("Min Lat", value=25.50, format="%.4f")
    with col2:
        max_lon = st.number_input("Max Lon", value=85.30, format="%.4f")
        max_lat = st.number_input("Max Lat", value=25.80, format="%.4f")
    
    if st.sidebar.button("🚀 Initialize AOI", use_container_width=True):
        aoi = ee.Geometry.BBox(min_lon, min_lat, max_lon, max_lat)
        map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]

elif input_method == "Upload GeoJSON":
    uploaded_file = st.sidebar.file_uploader("Select GeoJSON", type=["geojson", "json"], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            geojson_data = json.load(uploaded_file)
            coords = geojson_data["features"][0]["geometry"]["coordinates"]
            aoi = ee.Geometry.Polygon(coords)
            map_center = [coords[0][0][1], coords[0][0][0]]
            st.sidebar.success("✅ GeoJSON parsed.")
        except Exception:
            st.sidebar.error("⚠️ GeoJSON error.")

st.sidebar.divider()
st.sidebar.markdown("### 🛰️ SAR Parameters")
pre_start = st.sidebar.date_input("Pre-Flood Start", datetime.date(2024, 5, 1))
pre_end = st.sidebar.date_input("Pre-End", datetime.date(2024, 5, 30))
post_start = st.sidebar.date_input("Post-Flood Start", datetime.date(2024, 8, 1))
post_end = st.sidebar.date_input("Post-End", datetime.date(2024, 8, 30))
flood_threshold = st.sidebar.slider("Sensitivity (dB)", 1.0, 5.0, 1.25, 0.05)

st.sidebar.divider()
st.sidebar.markdown("### About the Developer")
st.sidebar.markdown("**Ankit Kumar**")
st.sidebar.caption("M.Tech Scholar, Land and Water Resources Engineering | IIT Kharagpur")

# ==========================================
# 5. CORE ANALYTICAL PIPELINES
# ==========================================

def calculate_flood_risk(aoi_geom):
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom).clamp(0, 40)
    # Slope Reclassification (Higher risk for flatter areas)
    slope_r = slope.where(slope.lte(2), 5).where(slope.gt(2).And(slope.lte(5)), 4).where(slope.gt(5).And(slope.lte(10)), 3).where(slope.gt(10).And(slope.lte(20)), 2).where(slope.gt(20), 1)
    
    lulc = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom)
    lulc_r = lulc.remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    
    rain = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate('2023-01-01', '2024-01-01').sum().clip(aoi_geom)
    rain_r = rain.where(rain.lt(1860), 1).where(rain.gte(1860).And(rain.lt(1880)), 2).where(rain.gte(1880).And(rain.lt(1910)), 3).where(rain.gte(1910).And(rain.lt(1950)), 4).where(rain.gte(1950), 5)
    
    # Weighted MCA
    return lulc_r.multiply(0.40).add(slope_r.multiply(0.30)).add(rain_r.multiply(0.30)).clip(aoi_geom).round()

def calculate_sar_flood(aoi_geom, pre_s, pre_e, post_s, post_e, threshold):
    s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
        .filterBounds(aoi_geom) \
        .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
        .filter(ee.Filter.eq('instrumentMode', 'IW')) \
        .select('VH')
    
    pre_img = s1.filterDate(str(pre_s), str(pre_e)).median().clip(aoi_geom)
    post_img = s1.filterDate(str(post_s), str(post_e)).median().clip(aoi_geom)
    
    # Refined Smoothing to handle Speckle
    pre_f = pre_img.focal_mean(60, 'circle', 'meters')
    post_f = post_img.focal_mean(60, 'circle', 'meters')
    diff = pre_f.subtract(post_f)
    
    # TERRAIN GUARD: Mask steep slopes to prevent Radar Shadowing (critical for mountain areas)
    dem = ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)
    slope = ee.Terrain.slope(dem)
    slope_mask = slope.lt(8) 
    
    # Water Masking using JRC Global Surface Water
    permanent_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom)
    
    # Logical Intersection for Flood detection
    flooded = diff.gt(threshold).updateMask(slope_mask).where(permanent_water, 0)
    final = flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded)
    
    return final, permanent_water.updateMask(permanent_water)

# ==========================================
# 6. DASHBOARD INTERFACE
# ==========================================
tab1, tab2 = st.tabs(["📊 Phase 1: Risk Modeling (MCA)", "🛰️ Phase 2: Active Flood Detection (SAR)"])

if aoi is not None:
    with tab1:
        st.info("**Multi-Criteria Analysis (MCA):** Identifies susceptibility using Slope, Rainfall, and Land Cover (ESA WorldCover).")
        with st.spinner('Calculating Weighted Overlay...'):
            risk_map = calculate_flood_risk(aoi)
            m1 = folium.Map(location=map_center, zoom_start=11)
            folium.TileLayer(
                tiles=risk_map.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format,
                attr='GEE', name='Risk Score', overlay=True
            ).add_to(m1)
            m1.get_root().html.add_child(folium.Element(get_mca_legend()))
            components.html(m1.get_root().render(), height=600)

    with tab2:
        st.info("**SAR Methodology:** Sentinel-1 radar detects smooth water surfaces. Mountain shadows are filtered via Slope Guard.")
        with st.spinner('Analyzing Microwave Backscatter...'):
            try:
                flood, water = calculate_sar_flood(aoi, pre_start, pre_end, post_start, post_end, flood_threshold)
                
                # Impact Metric Calculation
                stats = flood.multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=aoi,
                    scale=30,
                    maxPixels=1e9
                )
                area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0
                
                st.markdown(f"""
                <div class="metric-card">
                    <h4 style='margin:0;'>📊 Impact Summary</h4>
                    <p style='margin:0; font-size: 1.2rem; color: #008080;'>Detected New Inundation: <b>{area_ha} Hectares</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                m2 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.TileLayer(tiles=water.getMapId({'palette':['#00008B']})['tile_fetcher'].url_format, attr='GEE', name='Permanent').add_to(m2)
                folium.TileLayer(tiles=flood.getMapId({'palette':['#00FFFF']})['tile_fetcher'].url_format, attr='GEE', name='Active Flood').add_to(m2)
                m2.get_root().html.add_child(folium.Element(get_sar_legend()))
                components.html(m2.get_root().render(), height=550)
                
                download_url = flood.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.success(f"✅ Analysis Complete. [Download Flood Mask (GeoTIFF)]({download_url})")
            
            except Exception as e:
                st.error(f"⚠️ Analysis Error: {e}. Check AOI or date ranges.")
else:
    st.info("👈 Please define boundaries in the sidebar and click 'Initialize AOI'.")