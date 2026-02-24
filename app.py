import streamlit as st
import ee
import folium
from folium.plugins import Fullscreen, MiniMap, DualMap
import json
import streamlit.components.v1 as components
import datetime
import math
import pandas as pd
from streamlit_folium import folium_static, st_folium
import requests

try:
    from geopy.geocoders import Nominatim
    _GEOPY = True
except ImportError:
    _GEOPY = False

try:
    from fpdf import FPDF
    _FPDF = True
except ImportError:
    _FPDF = False

# ==========================================
# 1. PAGE CONFIG & STYLING
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
    .weight-row {
        display:flex; justify-content:space-between; align-items:center;
        background:rgba(0,255,255,0.04); border:1px solid rgba(0,255,255,0.12);
        border-radius:6px; padding:6px 10px; margin:4px 0;
        font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#c9d5e0;
    }
    .weight-row span { color:#00FFFF; font-weight:700; }

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
        background: rgba(0,255,255,0.07) !important; border-color: #00FFFF !important;
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
    .page-header { padding: 6px 0 20px 0; animation: fadeUp 0.6s ease; border-bottom: 1px solid rgba(0,255,255,0.08); margin-bottom: 20px; }
    .page-header .subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; letter-spacing: 3px; color: rgba(0,255,255,0.4); margin-top: 4px; }
    .status-pill { display: inline-flex; align-items: center; gap: 7px; background: rgba(0,200,80,0.07); border: 1px solid rgba(0,200,80,0.3); border-radius: 20px; padding: 4px 14px 4px 10px; font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: #00c850; }
    .status-dot { width:7px; height:7px; background:#00c850; border-radius:50%; box-shadow:0 0 8px #00c850; animation:pulse 2s ease infinite; }
    .status-pill-err { display: inline-flex; align-items: center; gap: 7px; background: rgba(220,50,50,0.07); border: 1px solid rgba(220,50,50,0.3); border-radius: 20px; padding: 4px 14px 4px 10px; font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; color: #ff4444; }
    .metric-card {
        background: linear-gradient(145deg, rgba(0,255,255,0.04) 0%, rgba(0,40,80,0.3) 100%);
        border: 1px solid rgba(0,255,255,0.18); border-radius: 12px;
        padding: 22px 18px; text-align: center; position: relative; overflow: hidden;
        animation: fadeUp 0.5s ease; transition: border-color 0.3s, box-shadow 0.3s;
    }
    .metric-card:hover { border-color: rgba(0,255,255,0.4); box-shadow: 0 0 30px rgba(0,255,255,0.08); }
    .metric-card::before { content:''; position:absolute; top:0; left:0; right:0; height:1px; background: linear-gradient(90deg, transparent, rgba(0,255,255,0.6), transparent); }
    .metric-card::after  { content:''; position:absolute; bottom:0; left:0; right:0; height:1px; background: linear-gradient(90deg, transparent, rgba(0,100,255,0.3), transparent); }
    .metric-card .metric-value { font-family: 'Rajdhani', sans-serif; font-size: 2.6rem; font-weight: 700; background: linear-gradient(135deg, #00FFFF, #4dc8ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; line-height: 1.1; margin: 0; }
    .metric-card .metric-label { font-size: 0.68rem; letter-spacing: 3px; color: rgba(0,255,255,0.5); font-family: 'JetBrains Mono', monospace; text-transform: uppercase; margin-top: 6px; }
    .metric-card .metric-sub   { font-size: 0.72rem; color: #4a6070; margin-top: 4px; font-family: 'Space Grotesk', sans-serif; }
    .tech-panel { background: rgba(0,255,255,0.02); border: 1px solid rgba(0,255,255,0.1); border-left: 3px solid rgba(0,255,255,0.6); border-radius: 0 8px 8px 0; padding: 16px 18px; margin-bottom: 12px; animation: fadeUp 0.4s ease; }
    .tech-panel h4 { font-family: 'Rajdhani', sans-serif !important; color: #00FFFF !important; font-size: 0.92rem !important; letter-spacing: 2px !important; margin: 0 0 6px 0 !important; font-weight: 600 !important; }
    .tech-panel p  { color: #5a7a8a !important; margin: 0 !important; font-size: 0.85rem !important; }
    .tech-panel .weight-badge { display: inline-block; background: rgba(0,255,255,0.08); border: 1px solid rgba(0,255,255,0.2); color: #00FFFF; border-radius: 4px; padding: 1px 8px; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; margin: 0 2px; }
    .stats-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }
    .stat-chip { background:rgba(0,255,255,0.05); border:1px solid rgba(0,255,255,0.15); border-radius:6px; padding:8px 12px; font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#c9d5e0; }
    .stat-chip b { color:#00FFFF; display:block; font-size:1.1rem; margin-bottom:2px; }
    .grid-line { height: 1px; margin: 14px 0; background: linear-gradient(90deg, transparent, rgba(0,255,255,0.12), transparent); border: none; }

    /* ── RETURN PERIOD TABLE ──────────────────────────── */
    .rp-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:0.78rem; margin-top:10px; }
    .rp-table th { color:rgba(0,255,255,0.5); letter-spacing:2px; font-size:0.65rem; padding:6px 10px; border-bottom:1px solid rgba(0,255,255,0.15); text-align:left; }
    .rp-table td { color:#c9d5e0; padding:7px 10px; border-bottom:1px solid rgba(0,255,255,0.06); }
    .rp-table tr:hover td { background:rgba(0,255,255,0.03); }
    .rp-table .rp-val { color:#00FFFF; font-weight:700; }
    .rp-bar { height:5px; background:linear-gradient(90deg,#00FFFF,#4dc8ff); border-radius:3px; display:inline-block; vertical-align:middle; margin-left:6px; }

    /* ── DUAL MAP PANEL LABELS ────────────────────────── */
    .dual-label-row { display:flex; gap:0; margin-bottom:4px; }
    .dual-label { flex:1; text-align:center; font-family:'Rajdhani',sans-serif; font-weight:600;
        font-size:0.85rem; letter-spacing:3px; color:rgba(0,255,255,0.6);
        background:rgba(0,255,255,0.04); border:1px solid rgba(0,255,255,0.12); padding:6px; }
    .dual-label:first-child { border-radius:6px 0 0 6px; }
    .dual-label:last-child  { border-radius:0 6px 6px 0; border-left:none; }

    /* ── PROGRESSION ──────────────────────────────────── */
    .prog-month-chip { display:inline-block; background:rgba(255,107,107,0.08); border:1px solid rgba(255,107,107,0.25);
        border-radius:6px; padding:4px 10px; font-family:'JetBrains Mono',monospace;
        font-size:0.72rem; color:#FF6B6B; margin:2px; }
    .infra-legend { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0; font-family:'JetBrains Mono',monospace; font-size:0.72rem; }
    .infra-chip { background:rgba(0,255,255,0.04); border:1px solid rgba(0,255,255,0.12);
        border-radius:4px; padding:3px 8px; color:#c9d5e0; }
    .infra-chip span { margin-right:5px; }
    .coord-pill { display:inline-flex; align-items:center; gap:7px; background:rgba(255,200,0,0.07);
        border:1px solid rgba(255,200,0,0.25); border-radius:20px; padding:4px 12px;
        font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#ffc800; margin-top:6px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. VIZ CONSTANTS (module-level)
# ==========================================
SAR_VIZ  = {'min': -25, 'max': 0,   'palette': ['000005','0d1b2a','1b4f72','2e86c1','7fb3d3','d6eaf8','ffffff']}
DIFF_VIZ = {'min': -2,  'max': 8,   'palette': ['1a1a2e','16213e','0f3460','00FFFF','ffffff']}
SEV_VIZ  = {'min': 1,   'max': 3,   'palette': ['ffffbf','fc8d59','d73027']}

# ==========================================
# 3. LEGENDS
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
            div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #00FFFF;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);box-shadow:0 0 20px rgba(0,255,255,0.2);line-height:1.95;min-width:185px;pointer-events:none;';
            div.innerHTML =
                '<div style="color:#00FFFF;font-weight:bold;font-size:12.5px;letter-spacing:1px;border-bottom:1px solid rgba(0,255,255,0.3);padding-bottom:6px;margin-bottom:8px;">&#9672; SAR INDICATORS</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00FFFF;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Active Flood Mask<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#00008B;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Permanent Water<br>' +
                '<hr style="margin:8px 0;border:0;border-top:1px solid rgba(0,255,255,0.2);">' +
                '<div style="color:rgba(0,255,255,0.6);font-size:10.5px;margin-bottom:5px;letter-spacing:1px;">BACKSCATTER SCALE</div>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#000005;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Low &minus;25 dB<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#2e86c1;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Medium<br>' +
                '<span style="display:inline-block;width:12px;height:12px;background:#ffffff;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>High 0 dB<br>' +
                '<hr style="margin:8px 0;border:0;border-top:1px solid rgba(0,255,255,0.2);">' +
                '<span style="color:#888;font-style:italic;font-size:10px;">&#9889; Terrain Guard: slope &lt; 8&#176;</span>';
            return div;
        }};
        legend.addTo({map_name});
    }})();
    </script>
    '''

# ==========================================
# 4. REPORT & PDF
# ==========================================
def generate_report(aoi_coords, mca_weights, sar_params, results):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
==================================================
HYDRO-CLIMATIC RISK ATLAS — TECHNICAL REPORT
Generated : {now}
==================================================
INVESTIGATOR : Ankit Kumar
INSTITUTION  : IIT Kharagpur
--------------------------------------------------
1. STUDY AREA (AOI)    : {aoi_coords}
2. MCA WEIGHTS         : LULC={mca_weights['lulc']}%  Slope={mca_weights['slope']}%  Rain={mca_weights['rain']}%
3. SAR POLARISATION    : {sar_params.get('polarization','VH')}
4. SAR WINDOWS (Pre)   : {sar_params['pre_start']} → {sar_params['pre_end']}
5. SAR WINDOWS (Post)  : {sar_params['f_start']} → {sar_params['f_end']}
6. THRESHOLD           : {sar_params['threshold']} dB
7. SPECKLE FILTER      : {'Lee (focal_mean 3×3)' if sar_params.get('speckle') else 'None'}
8. INUNDATED AREA      : {results['area_ha']} Ha
9. POPULATION EXPOSED  : {results.get('pop_exposed', 'N/A')}
==================================================
"""

def generate_pdf_bytes(aoi_coords, mca_weights, sar_params, results, rp_data=None):
    if not _FPDF:
        return None
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 14, 'HYDRO-CLIMATIC RISK ATLAS', ln=True)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 6, f'IIT Kharagpur  |  {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True)
        pdf.ln(4)
        pdf.set_draw_color(0, 200, 200)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(5)

        def section(title):
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.cell(0, 8, title, ln=True)
            pdf.set_font('Helvetica', '', 10)

        section('1. STUDY AREA')
        pdf.multi_cell(0, 6, f'AOI Coordinates: {aoi_coords}')
        pdf.ln(3)

        section('2. MCA ANALYSIS WEIGHTS')
        pdf.cell(57, 6, f'LULC: {mca_weights["lulc"]}%')
        pdf.cell(57, 6, f'Slope: {mca_weights["slope"]}%')
        pdf.cell(57, 6, f'Rainfall: {mca_weights["rain"]}%', ln=True)
        pdf.ln(3)

        section('3. SAR INUNDATION ANALYSIS')
        rows = [
            ('Polarisation', sar_params.get('polarization','VH')),
            ('Pre-flood window', f'{sar_params["pre_start"]} → {sar_params["pre_end"]}'),
            ('Post-flood window', f'{sar_params["f_start"]} → {sar_params["f_end"]}'),
            ('Change threshold', f'{sar_params["threshold"]} dB'),
            ('Speckle filter', 'Lee focal_mean 3x3' if sar_params.get('speckle') else 'None'),
        ]
        for k, v in rows:
            pdf.cell(65, 6, k + ':')
            pdf.cell(0, 6, str(v), ln=True)
        pdf.ln(3)

        section('4. RESULTS')
        pdf.cell(65, 6, 'Inundated Area:')
        pdf.cell(0, 6, f'{results["area_ha"]} Ha', ln=True)
        pdf.cell(65, 6, 'Population Exposed:')
        pdf.cell(0, 6, str(results.get('pop_exposed', 'N/A')), ln=True)
        pdf.ln(3)

        if rp_data and rp_data.get('return_periods'):
            section('5. FLOOD RETURN PERIODS  [Gumbel Distribution]')
            pdf.cell(65, 6, f'Analysis period: {rp_data.get("n_years",24)} years (2000-2023)', ln=True)
            pdf.cell(65, 6, f'Mean monsoon rain: {rp_data.get("mean",0)} mm')
            pdf.cell(0, 6, f'Std dev: {rp_data.get("std",0)} mm', ln=True)
            pdf.ln(2)
            for T, val in rp_data['return_periods'].items():
                pdf.cell(65, 6, f'  {T}-year return period:')
                pdf.cell(0, 6, f'{val:.0f} mm (monsoon total)', ln=True)
            pdf.ln(3)

        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, 'Generated by HydroRisk Atlas | IIT Kharagpur | Powered by Google Earth Engine', ln=True)
        return bytes(pdf.output())
    except Exception:
        return None

# ==========================================
# 5. EE INITIALIZATION (cached)
# ==========================================
project_id = 'xward-481405'

@st.cache_resource
def _init_ee_core():
    try:
        from ee import compute_engine
        creds = compute_engine.ComputeEngineCredentials()
        ee.Initialize(creds, project=project_id)
    except Exception:
        ee.Initialize(project=project_id)
    ee.Image('USGS/SRTMGL1_003').getInfo()

def initialize_ee():
    try:
        _init_ee_core()
        st.markdown('<div class="status-pill"><span class="status-dot"></span>GEE SATELLITE LINK · STABLE</div>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<div class="status-pill-err"><span style="width:7px;height:7px;background:#ff4444;border-radius:50%;box-shadow:0 0 8px #ff4444;display:inline-block;"></span>LINK FAILED · {str(e)[:60]}</div>', unsafe_allow_html=True)

# ==========================================
# 6. ANALYTICAL FUNCTIONS
# ==========================================
def calculate_flood_risk(aoi_geom, w_lulc=0.40, w_slope=0.30, w_rain=0.30):
    dem    = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope  = ee.Terrain.slope(dem).clip(aoi_geom)
    slope_r = slope.where(slope.lte(2), 5).where(slope.gt(20), 1)
    lulc   = ee.ImageCollection("ESA/WorldCover/v200").mosaic().select('Map').clip(aoi_geom)
    lulc_r = lulc.remap([10,20,30,40,50,60,80,90], [1,2,2,3,5,4,5,5])
    rain   = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate('2023-01-01','2024-01-01').sum().clip(aoi_geom)
    rain_r = rain.where(rain.lt(1860), 1).where(rain.gte(1950), 5)
    return lulc_r.multiply(w_lulc/100).add(slope_r.multiply(w_slope/100)).add(rain_r.multiply(w_rain/100)).clip(aoi_geom).round()

# ── CACHED TILE GETTERS ────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_mca_tile(aoi_json, w_lulc, w_slope, w_rain):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    risk = calculate_flood_risk(aoi_geom, w_lulc, w_slope, w_rain)
    return risk.getMapId({'min':1,'max':5,'palette':['1a9850','91cf60','ffffbf','fc8d59','d73027']})['tile_fetcher'].url_format

@st.cache_data(show_spinner=False, ttl=3600)
def get_all_sar_data(aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """Compute all SAR layers and stats; return serializable dict for caching."""
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi_geom)
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
          .select(polarization))
    pre  = s1.filterDate(str(p_start), str(p_end)).median().clip(aoi_geom)
    post = s1.filterDate(str(f_start), str(f_end)).median().clip(aoi_geom)
    if speckle:
        pre  = pre.focal_mean(radius=1, kernelType='square', units='pixels')
        post = post.focal_mean(radius=1, kernelType='square', units='pixels')
    diff = pre.subtract(post)
    slope_mask = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)).lt(8)
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom)
    flooded = diff.gt(threshold).updateMask(slope_mask).where(water, 0)
    flood   = flooded.focal_mode(40, 'circle', 'meters').updateMask(flooded)
    water_m = water.updateMask(water)

    # Severity zones
    dem = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    ep = dem.reduceRegion(reducer=ee.Reducer.percentile([10,50]), geometry=aoi_geom, scale=100, maxPixels=1e9).getInfo()
    p10 = ep.get('elevation_p10', 50)
    p50 = ep.get('elevation_p50', 100)
    sev = flood.where(flood.And(dem.lte(p10)), 3)
    sev = sev.where(flood.And(dem.gt(p10).And(dem.lte(p50))), 2)
    sev = sev.where(flood.And(dem.gt(p50)), 1)
    severity = sev.updateMask(flood)

    # Stats
    area_val = flood.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=50, maxPixels=1e9
    ).get(polarization).getInfo()
    area_ha = round(area_val / 10000, 2) if area_val else 0

    # Population
    try:
        pop_img = ee.ImageCollection("WorldPop/GP/100m/pop").filter(ee.Filter.eq('year', 2020)).mosaic().clip(aoi_geom)
        pop_val = pop_img.updateMask(flood).reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi_geom, scale=100, maxPixels=1e9).get('population').getInfo()
        pop_exposed = int(round(pop_val)) if pop_val else 0
    except Exception:
        pop_exposed = 0

    return {
        'flood_url':    flood.getMapId({'palette': ['00FFFF']})['tile_fetcher'].url_format,
        'water_url':    water_m.getMapId({'palette': ['00008B']})['tile_fetcher'].url_format,
        'pre_url':      pre.getMapId(SAR_VIZ)['tile_fetcher'].url_format,
        'post_url':     post.getMapId(SAR_VIZ)['tile_fetcher'].url_format,
        'diff_url':     diff.getMapId(DIFF_VIZ)['tile_fetcher'].url_format,
        'severity_url': severity.getMapId(SEV_VIZ)['tile_fetcher'].url_format,
        'area_ha':      area_ha,
        'pop_exposed':  pop_exposed,
    }

@st.cache_data(show_spinner=False, ttl=3600)
def get_ndvi_tile(aoi_json, p_start, p_end, f_start, f_end):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    s2_pre  = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi_geom).filterDate(str(p_start), str(p_end))
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median())
    s2_post = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterBounds(aoi_geom).filterDate(str(f_start), str(f_end))
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median())
    ndvi_pre  = s2_pre.normalizedDifference(['B8','B4']).clip(aoi_geom)
    ndvi_post = s2_post.normalizedDifference(['B8','B4']).clip(aoi_geom)
    ndvi_diff = ndvi_pre.subtract(ndvi_post)
    return ndvi_diff.getMapId({'min':-0.3,'max':0.5,'palette':['1a9850','ffffbf','d73027']})['tile_fetcher'].url_format

@st.cache_data(show_spinner=False, ttl=3600)
def get_jrc_freq_tile(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    freq = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence').clip(aoi_geom)
    return freq.getMapId({'min':0,'max':100,'palette':['ffffff','0000ff']})['tile_fetcher'].url_format

@st.cache_data(show_spinner=False, ttl=3600)
def get_s2_rgb_tile(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
          .filterBounds(aoi_geom).filterDate('2024-01-01','2024-12-31')
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).median().clip(aoi_geom))
    return s2.getMapId({'bands':['B4','B3','B2'],'min':0,'max':3000})['tile_fetcher'].url_format

@st.cache_data(show_spinner=False, ttl=3600)
def get_aoi_stats(aoi_json):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    dem   = ee.Image('USGS/SRTMGL1_003').select('elevation').clip(aoi_geom)
    slope = ee.Terrain.slope(dem).clip(aoi_geom)
    combined = dem.rename('elev').addBands(slope.rename('slope'))
    stats = combined.reduceRegion(
        reducer=ee.Reducer.minMax().combine(ee.Reducer.mean(), '', True),
        geometry=aoi_geom, scale=100, maxPixels=1e9
    ).getInfo()
    area_m2 = aoi_geom.area(maxError=1).getInfo()
    return {
        'elev_min':   round(stats.get('elev_min', 0)),
        'elev_max':   round(stats.get('elev_max', 0)),
        'elev_mean':  round(stats.get('elev_mean', 0)),
        'slope_mean': round(stats.get('slope_mean', 0), 1),
        'area_km2':   round(area_m2 / 1e6, 2)
    }

@st.cache_data(show_spinner=False, ttl=3600)
def get_chirps_series(aoi_json, start_str, end_str):
    aoi_geom = ee.Geometry(json.loads(aoi_json))
    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(start_str, end_str).filterBounds(aoi_geom)
    def extract(img):
        mean = img.reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=5000, maxPixels=1e8)
        return ee.Feature(None, {'date': img.date().format('YYYY-MM-dd'), 'rain': mean.get('precipitation')})
    fc = chirps.map(extract).getInfo()
    records = [{'date': f['properties']['date'], 'rainfall_mm': float(f['properties']['rain'])}
               for f in fc['features'] if f['properties'].get('rain') is not None]
    if not records:
        return None
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').set_index('date')

# ── FEATURE 15: WATERSHED (HydroSHEDS) ────────────────
@st.cache_data(show_spinner=False, ttl=7200)
def get_watershed_geojson(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        hydrobasins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_8")
        ws = hydrobasins.filterBounds(aoi_geom)
        return ws.geometry().getInfo()
    except Exception:
        return None

# ── FEATURE 14: OSM INFRASTRUCTURE ────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_osm_infrastructure(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        bb = aoi_geom.bounds().getInfo()['coordinates'][0]
        lats = [c[1] for c in bb];  lons = [c[0] for c in bb]
        s, n, w, e = min(lats), max(lats), min(lons), max(lons)
        query = f"""[out:json][timeout:20];
(node["amenity"~"hospital|school|fire_station|police"]({s},{w},{n},{e});
 way["amenity"~"hospital|school|fire_station|police"]({s},{w},{n},{e}););
out center 100;"""
        r = requests.post("https://overpass-api.de/api/interpreter", data=query, timeout=25)
        r.raise_for_status()
        elements = r.json().get('elements', [])
        infra = []
        for el in elements:
            lat = el.get('lat') or (el.get('center') or {}).get('lat')
            lon = el.get('lon') or (el.get('center') or {}).get('lon')
            if lat and lon:
                amenity = el.get('tags', {}).get('amenity', 'unknown')
                name    = el.get('tags', {}).get('name', amenity.replace('_',' ').title())
                infra.append({'lat': lat, 'lon': lon, 'type': amenity, 'name': name})
        return infra
    except Exception:
        return []

# ── FEATURE 17: FLOOD RETURN PERIOD (Gumbel) ──────────
@st.cache_data(show_spinner=False, ttl=7200)
def get_return_period(aoi_json):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        years_ee = ee.List.sequence(2000, 2023)
        def annual_monsoon(yr):
            yr = ee.Number(yr).int()
            start = ee.Date.fromYMD(yr, 6, 1)
            end   = ee.Date.fromYMD(yr, 11, 1)
            total = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                     .filterDate(start, end).filterBounds(aoi_geom).sum()
                     .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=10000, maxPixels=1e9))
            return ee.Feature(None, {'year': yr, 'rain': total.get('precipitation')})
        data = ee.FeatureCollection(years_ee.map(annual_monsoon)).getInfo()
        rains = [float(f['properties']['rain']) for f in data['features']
                 if f['properties'].get('rain') is not None]
        if len(rains) < 10:
            return None
        n  = len(rains)
        mu = sum(rains) / n
        std = (sum((x - mu)**2 for x in rains) / n) ** 0.5
        beta = std * (6 ** 0.5) / math.pi
        u    = mu - 0.5772 * beta
        rp   = {}
        max_val = max(rains)
        for T in [2, 5, 10, 25, 50, 100]:
            rp[T] = round(u - beta * math.log(-math.log(1 - 1/T)), 0)
        return {'mean': round(mu, 0), 'std': round(std, 0),
                'return_periods': rp, 'n_years': n,
                'max_obs': round(max_val, 0), 'rains': sorted(rains)}
    except Exception:
        return None

# ── FEATURE 13: FLOOD PROGRESSION STATS ───────────────
@st.cache_data(show_spinner=False, ttl=7200)
def get_progression_stats(aoi_json, year):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        months_ee = ee.List([6, 7, 8, 9, 10])
        def monthly_rain(m):
            m = ee.Number(m).int()
            start = ee.Date.fromYMD(ee.Number(year), m, 1)
            end   = start.advance(1, 'month')
            total = (ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                     .filterDate(start, end).filterBounds(aoi_geom).sum()
                     .reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=5000))
            return ee.Feature(None, {'month': m, 'rain': total.get('precipitation')})
        data = ee.FeatureCollection(months_ee.map(monthly_rain)).getInfo()
        names = {6:'Jun',7:'Jul',8:'Aug',9:'Sep',10:'Oct'}
        records = [{'Month': names[int(f['properties']['month'])],
                    'month_num': int(f['properties']['month']),
                    'Rain (mm)': round(float(f['properties'].get('rain') or 0), 1)}
                   for f in data['features']]
        records.sort(key=lambda x: x['month_num'])
        return pd.DataFrame(records)
    except Exception:
        return None

# ── FEATURE 13: MONTHLY SAR FLOOD TILE ────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def get_month_sar_tile(aoi_json, year, month_num, polarization, threshold, speckle):
    try:
        aoi_geom = ee.Geometry(json.loads(aoi_json))
        s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
              .filterBounds(aoi_geom)
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', polarization))
              .select(polarization))
        pre = s1.filterDate(f'{year}-01-01', f'{year}-03-31').median().clip(aoi_geom)
        days_in = [31,28,31,30,31,30,31,31,30,31,30,31][month_num-1]
        post = s1.filterDate(f'{year}-{month_num:02d}-01', f'{year}-{month_num:02d}-{days_in}').median().clip(aoi_geom)
        if speckle:
            pre  = pre.focal_mean(radius=1, kernelType='square', units='pixels')
            post = post.focal_mean(radius=1, kernelType='square', units='pixels')
        diff = pre.subtract(post)
        slope_mask = ee.Terrain.slope(ee.Image('USGS/SRTMGL1_003').clip(aoi_geom)).lt(8)
        water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('seasonality').gte(10).clip(aoi_geom)
        flooded = diff.gt(threshold).updateMask(slope_mask).where(water, 0)
        flood   = flooded.focal_mode(40,'circle','meters').updateMask(flooded)
        return flood.getMapId({'palette': ['FF6B6B']})['tile_fetcher'].url_format
    except Exception:
        return None

# ==========================================
# 7. SIDEBAR
# ==========================================
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

    # ── FEATURE 4: PLACE NAME SEARCH ───────────────────
    st.markdown('<div class="section-tag">Location Search</div>', unsafe_allow_html=True)
    place_query = st.text_input("Place", placeholder="e.g. Patna, Bihar", label_visibility="collapsed")
    if st.button("SEARCH & SET AOI", use_container_width=True):
        if _GEOPY and place_query.strip():
            try:
                geo = Nominatim(user_agent="hydroriskatlas_v3")
                loc = geo.geocode(place_query.strip(), timeout=10)
                if loc:
                    lat, lon, d = loc.latitude, loc.longitude, 0.25
                    st.session_state.aoi = ee.Geometry.BBox(lon-d, lat-d, lon+d, lat+d)
                    st.session_state.map_center = [lat, lon]
                    st.success(f"AOI set: {loc.address[:50]}")
                else:
                    st.warning("Location not found.")
            except Exception as ex:
                st.error(f"Geocoder error: {ex}")
        elif not _GEOPY:
            st.warning("Install geopy: pip install geopy")

    # ── AOI BOUNDARY ───────────────────────────────────
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

    # ── FEATURE 2: MCA WEIGHT SLIDERS ──────────────────
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

    # ── SAR ENGINE WINDOWS ─────────────────────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">SAR Engine Windows</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)
    with colA:
        p_start = st.date_input("Pre Start",  datetime.date(2024, 5, 1))
        f_start = st.date_input("Post Start", datetime.date(2024, 8, 1))
    with colB:
        p_end   = st.date_input("Pre End",    datetime.date(2024, 5, 30))
        f_end   = st.date_input("Post End",   datetime.date(2024, 8, 30))

    # ── FEATURE 10: VH / VV TOGGLE ─────────────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">SAR Polarisation</div>', unsafe_allow_html=True)
    polarization = st.radio("Polarisation", ("VH", "VV"), horizontal=True, label_visibility="collapsed")

    # ── BACKSCATTER THRESHOLD ──────────────────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Backscatter Threshold</div>', unsafe_allow_html=True)
    f_threshold = st.slider("Sensitivity (dB)", 0.5, 6.0, 1.25, step=0.25, label_visibility="collapsed")
    st.markdown(f'<div style="text-align:center;font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#00FFFF;margin-top:-8px;">{f_threshold} dB · {polarization}</div>', unsafe_allow_html=True)

    # ── FEATURE 19: SPECKLE FILTER ─────────────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Pre-processing</div>', unsafe_allow_html=True)
    apply_speckle = st.checkbox("Apply Speckle Filter (Lee 3×3)", value=True)

    # ── FEATURE 13: FLOOD PROGRESSION YEAR ─────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    st.markdown('<div class="section-tag">Flood Progression</div>', unsafe_allow_html=True)
    prog_year = st.selectbox("Year", [2019, 2020, 2021, 2022, 2023, 2024], index=5, label_visibility="collapsed")

    # ── EXPORT ─────────────────────────────────────────
    st.markdown('<hr class="sidebar-hr">', unsafe_allow_html=True)
    if st.session_state.aoi:
        report = generate_report(
            [min_lon, min_lat, max_lon, max_lat] if input_method == "Bounding Box" else "GeoJSON Uploaded",
            {"lulc": w_lulc, "slope": w_slope, "rain": w_rain},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end,
             "threshold": f_threshold, "polarization": polarization, "speckle": apply_speckle},
            {"area_ha":    st.session_state.get('area_ha', 0),
             "pop_exposed": st.session_state.get('pop_exposed', 'N/A')}
        )
        st.download_button("EXPORT TECH REPORT (.txt)", report,
                           file_name="HydroRisk_Atlas_Report.txt", use_container_width=True)

        # ── FEATURE 16: PDF REPORT ──────────────────────
        pdf_bytes = generate_pdf_bytes(
            [min_lon, min_lat, max_lon, max_lat] if input_method == "Bounding Box" else "GeoJSON",
            {"lulc": w_lulc, "slope": w_slope, "rain": w_rain},
            {"pre_start": p_start, "pre_end": p_end, "f_start": f_start, "f_end": f_end,
             "threshold": f_threshold, "polarization": polarization, "speckle": apply_speckle},
            {"area_ha":    st.session_state.get('area_ha', 0),
             "pop_exposed": st.session_state.get('pop_exposed', 'N/A')},
            rp_data=st.session_state.get('rp_data')
        )
        if pdf_bytes:
            st.download_button("EXPORT PDF REPORT (.pdf)", pdf_bytes,
                               file_name="HydroRisk_Atlas_Report.pdf",
                               mime="application/pdf", use_container_width=True)
        else:
            st.caption("Install fpdf2 for PDF export")

# ==========================================
# 8. MAIN RENDER
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
            <p>Multi-Criteria Analysis combining three weighted layers at native 30m resolution.</p>
            <br>
            <span class="weight-badge">LULC {w_lulc}%</span>
            <span class="weight-badge">SLOPE {w_slope}%</span>
            <span class="weight-badge">RAINFALL {w_rain}%</span>
            <hr class="grid-line">
            <p>Each layer reclassified to a <code>1–5</code> hazard rank. Final score = weighted sum, rounded to integer class.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="tech-panel">
            <h4>PHASE 2 — SAR INUNDATION DETECTION</h4>
            <p>Change-detection on Sentinel-1 <code>{polarization}</code> backscatter between pre-flood and post-flood windows.</p>
            <br>
            <span class="weight-badge">{polarization} POLARISATION</span>
            <span class="weight-badge">SLOPE MASK &lt;8°</span>
            <span class="weight-badge">{'SPECKLE FILTERED' if apply_speckle else 'RAW SAR'}</span>
            <hr class="grid-line">
            <p>Terrain Guard excludes <code>slope &gt; 8°</code> to eliminate radar shadows. Threshold: <code>{f_threshold} dB</code>.</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2, tab3, tab4 = st.tabs([
    "  PHASE 1 · MCA  ",
    "  PHASE 2 · SAR  ",
    "  DUAL-VIEW  ",
    "  PROGRESSION  "
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
            st.markdown(f"""
                <div class="stats-row">
                    <div class="stat-chip"><b>{stats['area_km2']} km²</b>AOI Area</div>
                    <div class="stat-chip"><b>{stats['elev_min']} m</b>Min Elevation</div>
                    <div class="stat-chip"><b>{stats['elev_max']} m</b>Max Elevation</div>
                    <div class="stat-chip"><b>{stats['elev_mean']} m</b>Mean Elevation</div>
                    <div class="stat-chip"><b>{stats['slope_mean']}°</b>Mean Slope</div>
                </div>
            """, unsafe_allow_html=True)

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

            # ── FEATURE 3 + 8 + 15: EXTRA LAYERS ──────────
            extra_layers = st.multiselect(
                "Extra Layers",
                ["Flood Frequency (JRC)", "Sentinel-2 True Color", "Watershed (HydroSHEDS)"],
                default=[], label_visibility="visible"
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # ── FEATURE 20: CLICK PICKER INFO ──────────────
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
            folium.GeoJson(
                st.session_state.aoi.getInfo(), name='AOI Boundary',
                style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
            ).add_to(m1)

            if "Flood Frequency (JRC)" in extra_layers:
                with st.spinner("Loading JRC flood frequency..."):
                    jrc_tile = get_jrc_freq_tile(_aoi_json)
                folium.TileLayer(tiles=jrc_tile, attr='GEE·JRC', name='Flood Frequency', opacity=0.7).add_to(m1)

            if "Sentinel-2 True Color" in extra_layers:
                with st.spinner("Loading Sentinel-2 RGB..."):
                    s2_tile = get_s2_rgb_tile(_aoi_json)
                folium.TileLayer(tiles=s2_tile, attr='GEE·ESA', name='Sentinel-2 RGB', opacity=0.8).add_to(m1)

            # ── FEATURE 15: WATERSHED ───────────────────────
            if "Watershed (HydroSHEDS)" in extra_layers:
                with st.spinner("Loading watershed boundaries..."):
                    ws_geojson = get_watershed_geojson(_aoi_json)
                if ws_geojson:
                    folium.GeoJson(
                        ws_geojson, name='Watershed Boundary',
                        style_function=lambda _: {'fillColor':'rgba(255,200,0,0.05)','color':'#FFD700','weight':1.5,'dashArray':'4 3'}
                    ).add_to(m1)

            folium.TileLayer(tiles=mca_tile, attr='GEE', name='Risk Score').add_to(m1)
            Fullscreen(position='topright', force_separate_button=True).add_to(m1)
            MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m1)
            folium.LayerControl(position='topright', collapsed=False).add_to(m1)
            m1.get_root().html.add_child(folium.Element(get_mca_legend(m1.get_name())))

            # ── FEATURE 20: CLICK PICKER (st_folium) ───────
            map_data = st_folium(m1, height=560, use_container_width=True, key="tab1_map", returned_objects=["last_clicked"])
            if map_data and map_data.get('last_clicked'):
                lc = map_data['last_clicked']
                st.session_state.clicked_coord = (round(lc['lat'], 5), round(lc['lng'], 5))

    # ════════════════════════════════════════
    # TAB 2 — SAR INUNDATION
    # ════════════════════════════════════════
    with tab2:
        with st.spinner(f'Querying Sentinel-1 {polarization} SAR archive...'):
            sar = get_all_sar_data(
                _aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
                f_threshold, polarization, apply_speckle
            )

        st.session_state.area_ha    = sar['area_ha']
        st.session_state.pop_exposed = f"{sar['pop_exposed']:,}"

        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">INUNDATED AREA</div>
                    <div class="metric-value">{sar['area_ha']}</div>
                    <div class="metric-sub">Hectares · post-event SAR</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">POPULATION EXPOSED</div>
                    <div class="metric-value" style="font-size:1.8rem;">{sar['pop_exposed']:,}</div>
                    <div class="metric-sub">WorldPop 2020 · 100m</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">THRESHOLD · POLAR.</div>
                    <div class="metric-value" style="font-size:1.6rem;">{f_threshold} dB</div>
                    <div class="metric-sub">{polarization} · {'Speckle filtered' if apply_speckle else 'Raw'}</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            sar_view = st.radio("Map Layer",
                ("Flood Mask", "Severity Zones", "Pre-flood SAR", "Post-flood SAR",
                 "Change Intensity", "NDVI Damage"),
                label_visibility="collapsed"
            )
            st.markdown("<br>", unsafe_allow_html=True)

            # ── FEATURE 14: OSM INFRASTRUCTURE TOGGLE ──────
            show_infra = st.checkbox("Show Infrastructure (OSM)", value=False)
            st.markdown("<br>", unsafe_allow_html=True)

            try:
                sar_url = ee.Image(1).selfMask().getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
            except Exception:
                sar_url = None
            st.link_button("DOWNLOAD FLOOD MASK", "#", use_container_width=True)

        with col2:
            m2 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.GeoJson(
                st.session_state.aoi.getInfo(), name='AOI Boundary',
                style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
            ).add_to(m2)
            folium.TileLayer(tiles=sar['water_url'], attr='GEE', name='Permanent Water').add_to(m2)

            if sar_view == "Severity Zones":
                folium.TileLayer(tiles=sar['severity_url'], attr='GEE', name='Flood Severity').add_to(m2)
            elif sar_view == "Pre-flood SAR":
                folium.TileLayer(tiles=sar['pre_url'], attr='GEE', name=f'Pre-flood {polarization} (dB)').add_to(m2)
            elif sar_view == "Post-flood SAR":
                folium.TileLayer(tiles=sar['post_url'], attr='GEE', name=f'Post-flood {polarization} (dB)').add_to(m2)
            elif sar_view == "Change Intensity":
                folium.TileLayer(tiles=sar['diff_url'], attr='GEE', name='Backscatter Δ (dB)').add_to(m2)
            elif sar_view == "NDVI Damage":
                with st.spinner("Computing NDVI damage..."):
                    ndvi_tile = get_ndvi_tile(_aoi_json, str(p_start), str(p_end), str(f_start), str(f_end))
                folium.TileLayer(tiles=ndvi_tile, attr='GEE·ESA', name='NDVI Damage (pre−post)').add_to(m2)
            else:
                folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Active Flood').add_to(m2)

            # ── FEATURE 14: OSM INFRASTRUCTURE MARKERS ─────
            if show_infra:
                with st.spinner("Fetching OSM infrastructure..."):
                    infra_data = get_osm_infrastructure(_aoi_json)
                icon_map = {
                    'hospital':     ('red',    '🏥'),
                    'school':       ('blue',   '🏫'),
                    'fire_station': ('orange', '🚒'),
                    'police':       ('purple', '🚓'),
                }
                for feat in infra_data:
                    color, icon_emoji = icon_map.get(feat['type'], ('gray', '📍'))
                    folium.CircleMarker(
                        location=[feat['lat'], feat['lon']], radius=7,
                        color=color, fill=True, fill_color=color, fill_opacity=0.7,
                        tooltip=f"{icon_emoji} {feat['name']} ({feat['type']})"
                    ).add_to(m2)
                if infra_data:
                    st.markdown(f"""
                        <div class="infra-legend">
                            <span class="infra-chip"><span style="color:red">●</span>Hospital ({sum(1 for f in infra_data if f['type']=='hospital')})</span>
                            <span class="infra-chip"><span style="color:blue">●</span>School ({sum(1 for f in infra_data if f['type']=='school')})</span>
                            <span class="infra-chip"><span style="color:orange">●</span>Fire Stn ({sum(1 for f in infra_data if f['type']=='fire_station')})</span>
                            <span class="infra-chip"><span style="color:purple">●</span>Police ({sum(1 for f in infra_data if f['type']=='police')})</span>
                        </div>
                    """, unsafe_allow_html=True)

            Fullscreen(position='topright', force_separate_button=True).add_to(m2)
            MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m2)
            folium.LayerControl(position='topright', collapsed=False).add_to(m2)
            m2.get_root().html.add_child(folium.Element(get_sar_legend(m2.get_name())))
            folium_static(m2, height=560)

        # ── FEATURE 5: CHIRPS RAINFALL CHART ────────────
        with st.expander("CHIRPS RAINFALL TIME SERIES", expanded=False):
            with st.spinner("Fetching CHIRPS daily rainfall..."):
                rain_df = get_chirps_series(_aoi_json, str(p_start), str(f_end))
            if rain_df is not None and not rain_df.empty:
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:rgba(0,255,255,0.5);letter-spacing:2px;margin-bottom:8px;">MEAN DAILY RAINFALL (mm) · AOI AVERAGE</div>', unsafe_allow_html=True)
                st.area_chart(rain_df, color="#00FFFF", height=200)
                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Total Rainfall", f"{rain_df['rainfall_mm'].sum():.1f} mm")
                col_r2.metric("Peak Daily",     f"{rain_df['rainfall_mm'].max():.1f} mm")
                col_r3.metric("Rainy Days",     f"{(rain_df['rainfall_mm'] > 1).sum()}")
            else:
                st.info("No CHIRPS data available for the selected date range.")

        # ── FEATURE 17: FLOOD RETURN PERIOD ─────────────
        with st.expander("FLOOD RETURN PERIOD ANALYSIS  [Gumbel Distribution]", expanded=False):
            with st.spinner("Computing 24-year monsoon rainfall statistics..."):
                rp_data = get_return_period(_aoi_json)
            st.session_state.rp_data = rp_data
            if rp_data:
                col_rp1, col_rp2, col_rp3 = st.columns(3)
                col_rp1.metric("Mean Monsoon Rain", f"{rp_data['mean']:.0f} mm")
                col_rp2.metric("Std Deviation",     f"± {rp_data['std']:.0f} mm")
                col_rp3.metric("Max Observed",      f"{rp_data['max_obs']:.0f} mm")
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:12px 0 6px;">RETURN PERIOD TABLE · MONSOON TOTAL (Jun–Oct)</div>', unsafe_allow_html=True)
                max_rp = max(rp_data['return_periods'].values())
                rows_html = ''
                for T, val in rp_data['return_periods'].items():
                    bar_w = int(80 * val / max_rp)
                    rows_html += f'''<tr>
                        <td>{T}-yr</td>
                        <td class="rp-val">{val:.0f} mm</td>
                        <td><span class="rp-bar" style="width:{bar_w}px;"></span></td>
                    </tr>'''
                st.markdown(f"""
                    <table class="rp-table">
                        <tr><th>RETURN PERIOD</th><th>RAINFALL</th><th>RELATIVE</th></tr>
                        {rows_html}
                    </table>
                """, unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:0.7rem;color:#3a5060;font-family:JetBrains Mono,monospace;margin-top:10px;">Based on {rp_data["n_years"]} years CHIRPS · Gumbel extreme value distribution</div>', unsafe_allow_html=True)
            else:
                st.warning("Return period calculation failed. Check GEE connectivity.")

    # ════════════════════════════════════════
    # TAB 3 — DUAL-VIEW (FEATURE 18)
    # ════════════════════════════════════════
    with tab3:
        st.markdown("""
            <div style="font-family:'Rajdhani',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">
                SYNCHRONIZED PRE / POST SAR BACKSCATTER COMPARISON · SCROLL TO ZOOM · PAN TO EXPLORE
            </div>
        """, unsafe_allow_html=True)

        with st.spinner("Building dual-view SAR comparison..."):
            sar_d = get_all_sar_data(
                _aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
                f_threshold, polarization, apply_speckle
            )

        st.markdown("""
            <div class="dual-label-row">
                <div class="dual-label">◀ PRE-FLOOD SAR</div>
                <div class="dual-label">POST-FLOOD SAR ▶</div>
            </div>
        """, unsafe_allow_html=True)

        dmap = DualMap(location=st.session_state.map_center, zoom_start=11,
                       tiles=None, layout='horizontal')
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                         attr='CartoDB', name='Basemap').add_to(dmap.m1)
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                         attr='CartoDB', name='Basemap').add_to(dmap.m2)

        folium.TileLayer(tiles=sar_d['pre_url'],   attr='GEE', name=f'Pre-flood {polarization}').add_to(dmap.m1)
        folium.TileLayer(tiles=sar_d['post_url'],  attr='GEE', name=f'Post-flood {polarization}').add_to(dmap.m2)
        folium.TileLayer(tiles=sar_d['flood_url'], attr='GEE', name='Flood Mask', opacity=0.6).add_to(dmap.m2)

        folium.GeoJson(
            st.session_state.aoi.getInfo(),
            style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
        ).add_to(dmap.m1)
        folium.GeoJson(
            st.session_state.aoi.getInfo(),
            style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
        ).add_to(dmap.m2)

        components.html(dmap._repr_html_(), height=580, scrolling=False)

        d3c1, d3c2, d3c3 = st.columns(3)
        d3c1.metric("Pre-flood Period",  f"{p_start} → {p_end}")
        d3c2.metric("Post-flood Period", f"{f_start} → {f_end}")
        d3c3.metric("Detected Flood",    f"{sar_d['area_ha']} Ha")

    # ════════════════════════════════════════
    # TAB 4 — FLOOD PROGRESSION (FEATURE 13)
    # ════════════════════════════════════════
    with tab4:
        st.markdown(f"""
            <div style="font-family:'Rajdhani',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">
                MONSOON FLOOD PROGRESSION · {prog_year} · SENTINEL-1 CHANGE DETECTION vs DRY-SEASON REFERENCE (JAN–MAR)
            </div>
        """, unsafe_allow_html=True)

        with st.spinner(f"Fetching {prog_year} CHIRPS monthly rainfall..."):
            prog_df = get_progression_stats(_aoi_json, prog_year)

        if prog_df is not None and not prog_df.empty:
            t4c1, t4c2 = st.columns([1, 2])
            with t4c1:
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.5);letter-spacing:2px;margin-bottom:8px;">MONTHLY RAINFALL · AOI MEAN</div>', unsafe_allow_html=True)
                chart_df = prog_df.set_index('Month')[['Rain (mm)']]
                st.bar_chart(chart_df, color="#FF6B6B", height=250)

                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.5);letter-spacing:2px;margin:14px 0 6px;">MONSOON STATS</div>', unsafe_allow_html=True)
                total_rain = prog_df['Rain (mm)'].sum()
                peak_month = prog_df.loc[prog_df['Rain (mm)'].idxmax(), 'Month']
                st.markdown(f"""
                    <div class="stats-row">
                        <div class="stat-chip"><b>{total_rain:.0f} mm</b>Season Total</div>
                        <div class="stat-chip"><b>{peak_month}</b>Peak Month</div>
                    </div>
                """, unsafe_allow_html=True)

            with t4c2:
                month_names = {'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10}
                prog_month  = st.radio("Select month for SAR flood map",
                                       list(month_names.keys()), horizontal=True)
                prog_month_num = month_names[prog_month]

                with st.spinner(f"Computing SAR flood mask · {prog_month} {prog_year}..."):
                    prog_tile = get_month_sar_tile(
                        _aoi_json, prog_year, prog_month_num,
                        polarization, f_threshold, apply_speckle
                    )

                m4 = folium.Map(location=st.session_state.map_center, zoom_start=11, tiles="CartoDB dark_matter")
                folium.GeoJson(
                    st.session_state.aoi.getInfo(),
                    style_function=lambda _: {'fillColor':'none','color':'#00FFFF','weight':2,'dashArray':'6 4'}
                ).add_to(m4)
                folium.TileLayer(tiles=sar_d['water_url'], attr='GEE', name='Permanent Water').add_to(m4)

                if prog_tile:
                    folium.TileLayer(
                        tiles=prog_tile, attr='GEE',
                        name=f'Flood · {prog_month} {prog_year}', opacity=0.85
                    ).add_to(m4)

                Fullscreen(position='topright').add_to(m4)
                folium.LayerControl(position='topright', collapsed=False).add_to(m4)

                # Progression legend
                prog_legend_js = f'''
                <script>
                (function() {{
                    var legend = L.control({{position: 'bottomleft'}});
                    legend.onAdd = function() {{
                        var div = document.createElement('div');
                        div.style.cssText = 'background:rgba(13,27,42,0.93);border:1.5px solid #FF6B6B;color:#e0e1dd;font-size:11.5px;padding:12px 15px;border-radius:10px;backdrop-filter:blur(8px);line-height:2;pointer-events:none;';
                        div.innerHTML = '<div style="color:#FF6B6B;font-weight:bold;font-size:12px;border-bottom:1px solid rgba(255,107,107,0.3);padding-bottom:4px;margin-bottom:6px;">&#9672; PROGRESSION · {prog_month} {prog_year}</div>' +
                            '<span style="display:inline-block;width:12px;height:12px;background:#FF6B6B;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Detected Inundation<br>' +
                            '<span style="display:inline-block;width:12px;height:12px;background:#00008B;border-radius:2px;margin-right:7px;vertical-align:middle;"></span>Permanent Water<br>' +
                            '<span style="color:#555;font-size:10px;">Ref: Jan–Mar {prog_year} · {polarization}</span>';
                        return div;
                    }};
                    legend.addTo({m4.get_name()});
                }})();
                </script>'''
                m4.get_root().html.add_child(folium.Element(prog_legend_js))
                folium_static(m4, height=420)

            # Monthly chips
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:14px 0 6px;">MONTHLY RAINFALL BREAKDOWN</div>', unsafe_allow_html=True)
            chips_html = ''
            for _, row in prog_df.iterrows():
                chips_html += f'<span class="prog-month-chip">{row["Month"]} · {row["Rain (mm)"]} mm</span>'
            st.markdown(f'<div>{chips_html}</div>', unsafe_allow_html=True)

        else:
            st.warning(f"Could not fetch CHIRPS data for {prog_year}.")

else:
    st.markdown("""
        <div style="text-align:center; padding:60px 20px; animation: fadeUp 0.6s ease;">
            <div style="font-size:3rem; margin-bottom:16px; filter:drop-shadow(0 0 20px rgba(0,255,255,0.4));">🛰️</div>
            <div style="font-family:'Rajdhani',sans-serif; font-size:1.3rem; letter-spacing:3px; color:rgba(0,255,255,0.6); margin-bottom:10px;">
                NO STUDY AREA DEFINED
            </div>
            <div style="font-size:0.8rem; color:#3a5060; font-family:'Space Grotesk',sans-serif; letter-spacing:1px;">
                Use the sidebar to search a location or define a bounding box, then click
                <strong style="color:rgba(0,255,255,0.4);">INITIALIZE AOI</strong>
            </div>
        </div>
    """, unsafe_allow_html=True)
