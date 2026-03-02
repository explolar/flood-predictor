import streamlit as st

def inject_styles():
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
