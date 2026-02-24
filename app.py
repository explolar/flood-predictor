import streamlit as st
import ee
import folium
from folium.plugins import Fullscreen, MiniMap
import json
import streamlit.components.v1 as components
import datetime
from streamlit_folium import folium_static

# ==========================================
# 1. CYBER-DARK UI & CUSTOM STYLING
# ==========================================
st.set_page_config(page_title="HydroRisk Atlas | IIT Kgp", layout="wide", page_icon="🛰️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    /* ── BASE ─────────────────────────────────────────── */
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #020c1b; }
    ::-webkit-scrollbar-thumb { background: rgba(0,255,255,0.25); border-radius: 2px; }

    .stApp {
        background: #020c1b;
        background-image:
            radial-gradient(ellipse at 15% 40%, rgba(0,255,255,0.04) 0%, transparent 55%),
            radial-gradient(ellipse at 85% 15%, rgba(0,100,255,0.06) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 100%, rgba(0,30,80,0.5) 0%, transparent 60%);
        color: #c9d5e0;
    }

    /* ── ANIMATIONS ───────────────────────────────────── */
    @keyframes shimmer  { 0%{background-position:0% center} 100%{background-position:200% center} }
    @keyframes fadeUp   { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
    @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:0.4} }
    @keyframes scandown { 0%{top:-10%} 100%{top:110%} }
    @keyframes borderGlow { 0%,100%{box-shadow:0 0 6px rgba(0,255,255,0.3)} 50%{box-shadow:0 0 18px rgba(0,255,255,0.7)} }

    /* ── TYPOGRAPHY ───────────────────────────────────── */
    h1 {
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 2.2rem !important; font-weight: 700 !important;
        letter-spacing: 4px !important; line-height: 1.1 !important;
        background: linear-gradient(120deg, #00FFFF 0%, #4dc8ff 40%, #00FFFF 80%) !important;
        background-size: 200% auto !important;
        -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
        animation: shimmer 4s linear infinite !important;
    }
    h2, h3 { font-family: 'Rajdhani', sans-serif !important; color: #00FFFF !important; letter-spacing: 1.5px !important; }
    h4 { font-family: 'Space Grotesk', sans-serif !important; color: #7eb8cc !important; font-weight: 600 !important; }
    p, li { color: #8ca0b0 !important; line-height: 1.7 !important; }
    code {
        background: rgba(0,255,255,0.08) !important; color: #00FFFF !important;
        padding: 2px 7px !important; border-radius: 4px !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.82em !important;
    }

    /* ── SIDEBAR ──────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(175deg, #020e1f 0%, #030b18 100%) !important;
        border-right: 1px solid rgba(0,255,255,0.12) !important;
        box-shadow: 6px 0 40px rgba(0,0,0,0.5) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }

    .sidebar-brand {
        text-align: center; padding: 4px 0 18px 0;
        border-bottom: 1px solid rgba(0,255,255,0.1); margin-bottom: 18px;
    }
    .sidebar-brand .brand-title {
        font-family: 'Rajdhani', sans-serif; font-size: 1.15rem; font-weight: 700;
        letter-spacing: 3px; color: #00FFFF;
        text-shadow: 0 0 20px rgba(0,255,255,0.5); margin: 8px 0 2px 0;
    }
    .sidebar-brand .brand-sub {
        font-size: 0.6rem; letter-spacing: 2.5px; color: rgba(0,255,255,0.35);
        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
    }
    .section-tag {
        font-family: 'JetBrains Mono', monospace; font-size: 0.62rem; font-weight: 700;
        letter-spacing: 3px; color: rgba(0,255,255,0.4); text-transform: uppercase;
        margin: 20px 0 8px 2px; display: flex; align-items: center; gap: 8px;
    }
    .section-tag::after {
        content: ''; flex: 1; height: 1px;
        background: linear-gradient(90deg, rgba(0,255,255,0.2), transparent);
    }
    .sidebar-hr {
        border: none; height: 1px; margin: 16px 0;
        background: linear-gradient(90deg, transparent, rgba(0,255,255,0.15), transparent);
    }

    /* ── INPUTS ───────────────────────────────────────── */
    .stNumberInput input, .stTextInput input {
        background: rgba(0,255,255,0.03) !important; color: #c9d5e0 !important;
        border: 1px solid rgba(0,255,255,0.18) !important; border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.84rem !important;
        transition: border-color 0.3s, box-shadow 0.3s !important;
    }
    .stNumberInput input:focus, .stTextInput input:focus {
        border-color: #00FFFF !important;
        box-shadow: 0 0 0 1px rgba(0,255,255,0.25), 0 0 12px rgba(0,255,255,0.08) !important;
    }
    .stNumberInput label, .stTextInput label, .stDateInput label,
    .stSlider label, .stFileUploader label, .stRadio label span {
        font-size: 0.78rem !important; color: #5a7a8a !important; letter-spacing: 0.8px !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    [data-baseweb="input"] { border-radius: 6px !important; }
    [data-testid="stDateInput"] input {
        background: rgba(0,255,255,0.03) !important; border: 1px solid rgba(0,255,255,0.18) !important;
        color: #c9d5e0 !important; border-radius: 6px !important; font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── SLIDER ───────────────────────────────────────── */
    [data-baseweb="slider"] [role="slider"] {
        background: #00FFFF !important; border: 2px solid #020c1b !important;
        box-shadow: 0 0 0 2px #00FFFF, 0 0 12px rgba(0,255,255,0.6) !important;
        width: 14px !important; height: 14px !important;
    }
    [data-baseweb="slider"] [data-testid="stSliderTrackFill"] { background: #00FFFF !important; }

    /* ── RADIO ────────────────────────────────────────── */
    [data-baseweb="radio"] [data-checked="true"] div {
        background: #00FFFF !important; border-color: #00FFFF !important;
        box-shadow: 0 0 8px rgba(0,255,255,0.5) !important;
    }

    /* ── FILE UPLOADER ────────────────────────────────── */
    [data-testid="stFileUploader"] section {
        background: rgba(0,255,255,0.02) !important;
        border: 1px dashed rgba(0,255,255,0.25) !important; border-radius: 8px !important;
        transition: border-color 0.3s !important;
    }
    [data-testid="stFileUploader"] section:hover { border-color: rgba(0,255,255,0.5) !important; }

    /* ── BUTTONS ──────────────────────────────────────── */
    .stButton > button {
        background: transparent !important; color: #00FFFF !important;
        border: 1px solid rgba(0,255,255,0.5) !important;
        font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important;
        font-size: 0.88rem !important; letter-spacing: 2px !important;
        border-radius: 6px !important; padding: 0.45rem 1.2rem !important;
        transition: all 0.25s ease !important; position: relative !important; overflow: hidden !important;
    }
    .stButton > button:hover {
        background: rgba(0,255,255,0.07) !important;
        border-color: #00FFFF !important;
        box-shadow: 0 0 20px rgba(0,255,255,0.2), inset 0 0 20px rgba(0,255,255,0.03) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }
    [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {
        background: rgba(0,255,255,0.05) !important; color: #00FFFF !important;
        border: 1px solid rgba(0,255,255,0.35) !important;
        font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important;
        letter-spacing: 1.5px !important; border-radius: 6px !important; font-size: 0.85rem !important;
        text-decoration: none !important; transition: all 0.25s !important;
    }
    [data-testid="stDownloadButton"] button:hover, [data-testid="stLinkButton"] a:hover {
        background: rgba(0,255,255,0.1) !important; border-color: #00FFFF !important;
        box-shadow: 0 0 16px rgba(0,255,255,0.2) !important;
    }

    /* ── TABS ─────────────────────────────────────────── */
    [data-testid="stTabs"] [role="tablist"] {
        background: transparent !important; gap: 0 !important;
        border-bottom: 1px solid rgba(0,255,255,0.1) !important; padding-bottom: 0 !important;
    }
    [data-testid="stTabs"] button[role="tab"] {
        font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important;
        font-size: 0.92rem !important; letter-spacing: 2px !important;
        color: rgba(0,255,255,0.35) !important; border: none !important;
        background: transparent !important; padding: 0.55rem 1.6rem !important;
        border-bottom: 2px solid transparent !important; transition: all 0.3s !important;
        margin-bottom: -1px !important;
    }
    [data-testid="stTabs"] button[role="tab"]:hover { color: rgba(0,255,255,0.7) !important; background: rgba(0,255,255,0.03) !important; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #00FFFF !important; border-bottom: 2px solid #00FFFF !important;
        text-shadow: 0 0 12px rgba(0,255,255,0.6) !important;
    }
    [data-testid="stTabs"] [role="tabpanel"] { padding-top: 1.2rem !important; }

    /* ── EXPANDER ─────────────────────────────────────── */
    [data-testid="stExpander"] {
        background: rgba(0,20,40,0.4) !important;
        border: 1px solid rgba(0,255,255,0.1) !important; border-radius: 10px !important;
        overflow: hidden !important;
    }
    [data-testid="stExpander"] summary {
        font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important;
        font-size: 0.88rem !important; letter-spacing: 2px !important;
        color: rgba(0,255,255,0.6) !important; padding: 12px 16px !important;
    }
    [data-testid="stExpander"] summary:hover { color: #00FFFF !important; background: rgba(0,255,255,0.03) !important; }

    /* ── ALERTS ───────────────────────────────────────── */
    [data-testid="stAlert"] {
        border-radius: 8px !important; backdrop-filter: blur(8px) !important;
        font-family: 'Space Grotesk', sans-serif !important; font-size: 0.84rem !important;
    }
    .stSuccess { background: rgba(0,200,80,0.07) !important; border: 1px solid rgba(0,200,80,0.3) !important; }
    .stError   { background: rgba(220,50,50,0.07) !important; border: 1px solid rgba(220,50,50,0.3) !important; }
    .stInfo    { background: rgba(0,120,220,0.07) !important; border: 1px solid rgba(0,120,220,0.3) !important; }
    .stWarning { background: rgba(220,160,0,0.07) !important; border: 1px solid rgba(220,160,0,0.3) !important; }

    /* ── SPINNER ──────────────────────────────────────── */
    [data-testid="stSpinner"] p { color: #00FFFF !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; }

    /* ── CUSTOM COMPONENTS ────────────────────────────── */
    .page-header {
        padding: 6px 0 20px 0; animation: fadeUp 0.6s ease;
        border-bottom: 1px solid rgba(0,255,255,0.08); margin-bottom: 20px;
    }
    .page-header .subtitle {
        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
        letter-spacing: 3px; color: rgba(0,255,255,0.4); margin-top: 4px;
    }
    .status-pill {
        display: inline-flex; align-items: center; gap: 7px;
        background: rgba(0,200,80,0.07); border: 1px solid rgba(0,200,80,0.3);
        border-radius: 20px; padding: 4px 14px 4px 10px;
        font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: #00c850;
    }
    .status-dot { width:7px; height:7px; background:#00c850; border-radius:50%; box-shadow:0 0 8px #00c850; animation:pulse 2s ease infinite; }
    .status-pill-err {
        display: inline-flex; align-items: center; gap: 7px;
        background: rgba(220,50,50,0.07); border: 1px solid rgba(220,50,50,0.3);
        border-radius: 20px; padding: 4px 14px 4px 10px;
        font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: #ff4444;
    }
    .metric-card {
        background: linear-gradient(145deg, rgba(0,255,255,0.04) 0%, rgba(0,40,80,0.3) 100%);
        border: 1px solid rgba(0,255,255,0.18); border-radius: 12px;
        padding: 22px 18px; text-align: center; position: relative; overflow: hidden;
        animation: fadeUp 0.5s ease;
        transition: border-color 0.3s, box-shadow 0.3s;
    }
    .metric-card:hover { border-color: rgba(0,255,255,0.4); box-shadow: 0 0 30px rgba(0,255,255,0.08); }
    .metric-card::before {
        content:''; position:absolute; top:0; left:0; right:0; height:1px;
        background: linear-gradient(90deg, transparent, rgba(0,255,255,0.6), transparent);
    }
    .metric-card::after {
        content:''; position:absolute; bottom:0; left:0; right:0; height:1px;
        background: linear-gradient(90deg, transparent, rgba(0,100,255,0.3), transparent);
    }
    .metric-card .metric-value {
        font-family: 'Rajdhani', sans-serif; font-size: 2.6rem; font-weight: 700;
        background: linear-gradient(135deg, #00FFFF, #4dc8ff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.1; margin: 0;
    }
    .metric-card .metric-label {
        font-size: 0.68rem; letter-spacing: 3px; color: rgba(0,255,255,0.5);
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase; margin-top: 6px;
    }
    .metric-card .metric-sub {
        font-size: 0.72rem; color: #4a6070; margin-top: 4px; font-family: 'Space Grotesk', sans-serif;
    }
    .tech-panel {
        background: rgba(0,255,255,0.02); border: 1px solid rgba(0,255,255,0.1);
        border-left: 3px solid rgba(0,255,255,0.6); border-radius: 0 8px 8px 0;
        padding: 16px 18px; margin-bottom: 12px; animation: fadeUp 0.4s ease;
    }
    .tech-panel h4 {
        font-family: 'Rajdhani', sans-serif !important; color: #00FFFF !important;
        font-size: 0.92rem !important; letter-spacing: 2px !important; margin: 0 0 6px 0 !important; font-weight: 600 !important;
    }
    .tech-panel p { color: #5a7a8a !important; margin: 0 !important; font-size: 0.85rem !important; }
    .tech-panel .weight-badge {
        display: inline-block; background: rgba(0,255,255,0.08); border: 1px solid rgba(0,255,255,0.2);
        color: #00FFFF; border-radius: 4px; padding: 1px 8px; font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace; margin: 0 2px;
    }
    .grid-line {
        height: 1px; margin: 14px 0;
        background: linear-gradient(90deg, transparent, rgba(0,255,255,0.12), transparent);
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. HAZARD RANKING LEGENDS & TOOLS
# ==========================================
def get_mca_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:1.95;min-width:155px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12.5px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; RISK INDEX</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#d73027;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very High (5)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#fc8d59;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>High (4)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#ffffbf;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Moderate (3)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#91cf60;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Low (2)<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#1a9850;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Very Low (1)';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''

def get_sar_legend(map_name):
    return f'''
    <script>
    (function() {{
        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function() {{
            var div = document.createElement('div');
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:1.95;min-width:165px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12.5px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; SAR INDICATORS</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00FFFF;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Active Flood<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00008B;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Permanent Water<br>' +
                '<hr style="margin:8px 0;border:0;border-top:1px solid rgba(0,255,255,0.2);">' +
                '<span style="color:#888;font-style:italic;font-size:10px;">&#9889; Terrain Guard: Active</span>';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
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
        st.markdown('<div class="status-pill"><span class="status-dot"></span>GEE SATELLITE LINK · STABLE</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="status-pill-err"><span style="width:7px;height:7px;background:#ff4444;border-radius:50%;box-shadow:0 0 8px #ff4444;"></span>LINK FAILED · {str(e)[:60]}</div>', unsafe_allow_html=True)


# ==========================================
# 4. SIDEBAR & AOI
# ==========================================
with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand">
            <img src="https://upload.wikimedia.org/wikipedia/en/1/1c/IIT_Kharagpur_Logo.png" width="72" style="filter:drop-shadow(0 0 10px rgba(0,255,255,0.3))">
            <div class="brand-title">RISK ATLAS</div>
            <div class="brand-sub">IIT Kharagpur · GEE 30m</div>
        </div>
    """, unsafe_allow_html=True)

    if 'aoi' not in st.session_state: st.session_state.aoi = None
    if 'map_center' not in st.session_state: st.session_state.map_center = [25.61, 85.12]

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
            st.session_state.map_center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    else:
        uploaded_file = st.file_uploader("Upload District GeoJSON", type=["geojson", "json"])
        if uploaded_file:
            data = json.load(uploaded_file)
            coords = data["features"][0]["geometry"]["coordinates"]
            st.session_state.aoi = ee.Geometry.Polygon(coords)
            st.session_state.map_center = [coords[0][0][1], coords[0][0][0]]

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">SAR Engine Windows</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)
    with colA:
        p_start = st.date_input("Pre Start", datetime.date(2024, 5, 1))
        f_start = st.date_input("Post Start", datetime.date(2024, 8, 1))
    with colB:
        p_end = st.date_input("Pre End", datetime.date(2024, 5, 30))
        f_end = st.date_input("Post End", datetime.date(2024, 8, 30))

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Backscatter Threshold</div>', unsafe_allow_html=True)
    f_threshold = st.slider("Sensitivity (dB)", 1.0, 5.0, 1.25, label_visibility="collapsed")
    st.markdown(f'<div style="text-align:center;font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#00FFFF;margin-top:-8px;">{f_threshold} dB</div>', unsafe_allow_html=True)

    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    if st.session_state.aoi:
        report = generate_report(
            [min_lon, min_lat, max_lon, max_lat] if input_method=="Bounding Box" else "GeoJSON Uploaded",
            {"lulc": 40, "slope": 30, "rain": 30},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end, "threshold": f_threshold},
            {"area_ha": st.session_state.get('area_ha', 0)}
        )
        st.download_button("EXPORT TECH REPORT", report, file_name="HydroRisk_Atlas_Report.txt", use_container_width=True)

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
# ── PAGE HEADER ────────────────────────────────────────
st.markdown("""
    <div class="page-header">
        <h1>HYDRO-CLIMATIC RISK ATLAS</h1>
        <div class="subtitle">SENTINEL-1 SAR · ESA WORLDCOVER · CHIRPS RAINFALL · SRTM DEM · 30m RESOLUTION</div>
    </div>
""", unsafe_allow_html=True)

initialize_ee()

# ── METHOD PANEL ───────────────────────────────────────
with st.expander("ANALYTICAL METHODOLOGY", expanded=False):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="tech-panel">
            <h4>PHASE 1 — MCA SUSCEPTIBILITY</h4>
            <p>Multi-Criteria Analysis combining three weighted layers at native 30m resolution.</p>
            <br>
            <span class="weight-badge">LULC 40%</span>
            <span class="weight-badge">SLOPE 30%</span>
            <span class="weight-badge">RAINFALL 30%</span>
            <hr class="grid-line">
            <p>Each layer reclassified to a <code>1–5</code> hazard rank. Final score = weighted sum, rounded to integer class.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="tech-panel">
            <h4>PHASE 2 — SAR INUNDATION DETECTION</h4>
            <p>Change-detection on Sentinel-1 VH backscatter between pre-flood and post-flood windows.</p>
            <br>
            <span class="weight-badge">VH POLARISATION</span>
            <span class="weight-badge">SLOPE MASK &lt;8°</span>
            <hr class="grid-line">
            <p>Terrain Guard strictly excludes <code>slope &gt; 8°</code> to eliminate radar shadows in mountainous terrain (Manali/Naggar).</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2 = st.tabs(["  PHASE 1 · SUSCEPTIBILITY MAP (MCA)  ", "  PHASE 2 · ACTIVE INUNDATION (SAR)  "])

if st.session_state.aoi:
    with tab1:
        risk = calculate_flood_risk(st.session_state.aoi)
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-label">MODEL STATUS</div>
                    <div class="metric-value">MCA</div>
                    <div class="metric-sub">Multi-Criteria Analysis · Active</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
                <div class="metric-card">
                    <div class="metric-label">RESOLUTION</div>
                    <div class="metric-value">30m</div>
                    <div class="metric-sub">Native GEE pixel scale</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            try:
                mca_url = risk.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("DOWNLOAD MCA GEOTIFF", mca_url, use_container_width=True)
            except:
                st.warning("Area too large for direct download.")
        with c2:
            m1 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.GeoJson(
                st.session_state.aoi.getInfo(), name='AOI Boundary',
                style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
            ).add_to(m1)
            folium.TileLayer(tiles=risk.getMapId({'min':1,'max':5,'palette':['#1a9850','#91cf60','#ffffbf','#fc8d59','#d73027']})['tile_fetcher'].url_format, attr='GEE', name='Risk Score').add_to(m1)
            Fullscreen(position='topright', force_separate_button=True).add_to(m1)
            MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m1)
            folium.LayerControl(position='topright', collapsed=False).add_to(m1)
            m1.get_root().html.add_child(folium.Element(get_mca_legend(m1.get_name())))
            folium_static(m1, height=560)

    with tab2:
        with st.spinner('Querying Sentinel-1 backscatter archive...'):
            flood, water = calculate_sar_flood(st.session_state.aoi, f_start, f_end, p_start, p_end, f_threshold)
            stats = flood.multiply(ee.Image.pixelArea()).reduceRegion(reducer=ee.Reducer.sum(), geometry=st.session_state.aoi, scale=50, maxPixels=1e9)
            area_ha = round(stats.get('VH').getInfo() / 10000, 2) if stats.get('VH').getInfo() else 0
            st.session_state.area_ha = area_ha

            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">INUNDATED AREA</div>
                        <div class="metric-value">{area_ha}</div>
                        <div class="metric-sub">Hectares · Post-event SAR</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">THRESHOLD</div>
                        <div class="metric-value">{f_threshold}</div>
                        <div class="metric-sub">dB backscatter delta</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                try:
                    sar_url = flood.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                except:
                    sar_url = flood.getDownloadUrl({'scale': 100, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
                st.link_button("DOWNLOAD SAR MASK", sar_url, use_container_width=True)
            with col2:
                m2 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.GeoJson(
                    st.session_state.aoi.getInfo(), name='AOI Boundary',
                    style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
                ).add_to(m2)
                folium.TileLayer(tiles=water.getMapId({'palette':['#00008B']})['tile_fetcher'].url_format, attr='GEE', name='Permanent Water').add_to(m2)
                folium.TileLayer(tiles=flood.getMapId({'palette':['#00FFFF']})['tile_fetcher'].url_format, attr='GEE', name='Active Flood').add_to(m2)
                Fullscreen(position='topright', force_separate_button=True).add_to(m2)
                MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m2)
                folium.LayerControl(position='topright', collapsed=False).add_to(m2)
                m2.get_root().html.add_child(folium.Element(get_sar_legend(m2.get_name())))
                folium_static(m2, height=560)
else:
    st.markdown("""
        <div style="text-align:center; padding:60px 20px; animation: fadeUp 0.6s ease;">
            <div style="font-size:3rem; margin-bottom:16px; filter:drop-shadow(0 0 20px rgba(0,255,255,0.4));">🛰️</div>
            <div style="font-family:'Rajdhani',sans-serif; font-size:1.3rem; letter-spacing:3px; color:rgba(0,255,255,0.6); margin-bottom:10px;">
                NO STUDY AREA DEFINED
            </div>
            <div style="font-size:0.8rem; color:#3a5060; font-family:'Space Grotesk',sans-serif; letter-spacing:1px;">
                Define a bounding box or upload a GeoJSON in the sidebar, then click <strong style="color:rgba(0,255,255,0.4);">INITIALIZE AOI</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)