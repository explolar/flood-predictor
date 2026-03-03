import streamlit as st

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    /* ── BASE ─────────────────────────────────────────── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent !important; }
    .stDeployButton { display: none !important; }
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        color: #64B5F6 !important;
    }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0a1628; }
    ::-webkit-scrollbar-thumb { background: rgba(100,181,246,0.3); border-radius: 2px; }

    .stApp {
        background: #0a1628;
        color: #c9d5e0;
    }

    /* ── ANIMATIONS (minimal) ────────────────────────── */
    @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

    /* ── TYPOGRAPHY ───────────────────────────────────── */
    h1 {
        font-family: 'Inter', sans-serif !important;
        font-size: 1.8rem !important; font-weight: 700 !important;
        letter-spacing: 1px !important;
        color: #E3F2FD !important;
        -webkit-text-fill-color: #E3F2FD !important;
    }
    h2, h3 { font-family: 'Inter', sans-serif !important; color: #90CAF9 !important; }
    h4 { font-family: 'Inter', sans-serif !important; color: #B0BEC5 !important; font-weight: 600 !important; }
    p, li { color: #90A4AE !important; line-height: 1.6 !important; }
    code {
        background: rgba(100,181,246,0.1) !important; color: #64B5F6 !important;
        padding: 2px 6px !important; border-radius: 3px !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.82em !important;
    }

    /* ── SIDEBAR ──────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: #0d1b2a !important;
        border-right: 1px solid rgba(100,181,246,0.1) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
    .sidebar-brand {
        text-align: center; padding: 4px 0 16px 0;
        border-bottom: 1px solid rgba(100,181,246,0.1); margin-bottom: 16px;
    }
    .sidebar-brand .brand-title {
        font-family: 'Inter', sans-serif; font-size: 1rem; font-weight: 700;
        letter-spacing: 2px; color: #E3F2FD; margin: 8px 0 2px 0;
    }
    .sidebar-brand .brand-sub {
        font-size: 0.6rem; letter-spacing: 2px; color: rgba(144,202,249,0.4);
        text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
    }
    .section-tag {
        font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 700;
        letter-spacing: 2px; color: rgba(100,181,246,0.5); text-transform: uppercase;
        margin: 18px 0 6px 2px; display: flex; align-items: center; gap: 8px;
    }
    .section-tag::after {
        content: ''; flex: 1; height: 1px;
        background: linear-gradient(90deg, rgba(100,181,246,0.15), transparent);
    }
    .sidebar-hr {
        border: none; height: 1px; margin: 14px 0;
        background: rgba(100,181,246,0.08);
    }
    .weight-row {
        display:flex; justify-content:space-between; align-items:center;
        background:rgba(100,181,246,0.04); border:1px solid rgba(100,181,246,0.1);
        border-radius:6px; padding:5px 10px; margin:3px 0;
        font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#c9d5e0;
    }
    .weight-row span { color:#64B5F6; font-weight:700; }

    /* ── INPUTS ───────────────────────────────────────── */
    .stNumberInput input, .stTextInput input {
        background: rgba(100,181,246,0.04) !important; color: #c9d5e0 !important;
        border: 1px solid rgba(100,181,246,0.15) !important; border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 0.84rem !important;
    }
    .stNumberInput input:focus, .stTextInput input:focus {
        border-color: #64B5F6 !important;
        box-shadow: 0 0 0 1px rgba(100,181,246,0.2) !important;
    }
    .stNumberInput label, .stTextInput label, .stDateInput label,
    .stSlider label, .stFileUploader label, .stRadio label span {
        font-size: 0.78rem !important; color: #607D8B !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-baseweb="input"] { border-radius: 6px !important; }
    [data-testid="stDateInput"] input {
        background: rgba(100,181,246,0.04) !important; border: 1px solid rgba(100,181,246,0.15) !important;
        color: #c9d5e0 !important; border-radius: 6px !important; font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── SLIDER ───────────────────────────────────────── */
    [data-baseweb="slider"] [role="slider"] {
        background: #64B5F6 !important; border: 2px solid #0a1628 !important;
        box-shadow: 0 0 0 2px #64B5F6 !important;
        width: 14px !important; height: 14px !important;
    }
    [data-baseweb="slider"] [data-testid="stSliderTrackFill"] { background: #64B5F6 !important; }

    /* ── RADIO ────────────────────────────────────────── */
    [data-baseweb="radio"] [data-checked="true"] div {
        background: #64B5F6 !important; border-color: #64B5F6 !important;
    }

    /* ── FILE UPLOADER ────────────────────────────────── */
    [data-testid="stFileUploader"] section {
        background: rgba(100,181,246,0.02) !important;
        border: 1px dashed rgba(100,181,246,0.2) !important; border-radius: 8px !important;
    }

    /* ── BUTTONS ──────────────────────────────────────── */
    .stButton > button {
        background: transparent !important; color: #64B5F6 !important;
        border: 1px solid rgba(100,181,246,0.4) !important;
        font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
        font-size: 0.85rem !important; letter-spacing: 1px !important;
        border-radius: 6px !important; padding: 0.45rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: rgba(100,181,246,0.08) !important; border-color: #64B5F6 !important;
    }
    [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {
        background: rgba(100,181,246,0.05) !important; color: #64B5F6 !important;
        border: 1px solid rgba(100,181,246,0.3) !important;
        font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
        letter-spacing: 1px !important; border-radius: 6px !important; font-size: 0.82rem !important;
        text-decoration: none !important;
    }
    [data-testid="stDownloadButton"] button:hover, [data-testid="stLinkButton"] a:hover {
        background: rgba(100,181,246,0.1) !important; border-color: #64B5F6 !important;
    }

    /* ── TABS ─────────────────────────────────────────── */
    [data-testid="stTabs"] [role="tablist"] {
        background: transparent !important; gap: 0 !important;
        border-bottom: 1px solid rgba(100,181,246,0.1) !important; padding-bottom: 0 !important;
        overflow-x: auto !important; flex-wrap: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
    }
    [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none !important; }
    [data-testid="stTabs"] button[role="tab"] {
        font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
        font-size: 0.85rem !important; letter-spacing: 1px !important;
        color: rgba(144,202,249,0.4) !important; border: none !important;
        background: transparent !important; padding: 0.5rem 1.4rem !important;
        border-bottom: 2px solid transparent !important; transition: all 0.2s !important;
        margin-bottom: -1px !important; white-space: nowrap !important; flex-shrink: 0 !important;
    }
    [data-testid="stTabs"] button[role="tab"]:hover { color: rgba(144,202,249,0.7) !important; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #E3F2FD !important; border-bottom: 2px solid #64B5F6 !important;
    }
    [data-testid="stTabs"] [role="tabpanel"] { padding-top: 1rem !important; }

    /* ── EXPANDER ─────────────────────────────────────── */
    [data-testid="stExpander"] {
        background: rgba(13,27,42,0.6) !important;
        border: 1px solid rgba(100,181,246,0.08) !important; border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
        font-size: 0.82rem !important; letter-spacing: 1px !important;
        color: rgba(144,202,249,0.6) !important; padding: 10px 14px !important;
    }
    [data-testid="stExpander"] summary:hover { color: #90CAF9 !important; }

    /* ── ALERTS ───────────────────────────────────────── */
    [data-testid="stAlert"] {
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important; font-size: 0.84rem !important;
    }

    /* ── SPINNER ──────────────────────────────────────── */
    [data-testid="stSpinner"] p { color: #64B5F6 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 0.8rem !important; }

    /* ── CUSTOM COMPONENTS ────────────────────────────── */
    .page-header { padding: 4px 0 16px 0; animation: fadeUp 0.4s ease; border-bottom: 1px solid rgba(100,181,246,0.08); margin-bottom: 16px; }
    .page-header .subtitle { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; letter-spacing: 1.5px; color: rgba(144,202,249,0.4); margin-top: 4px; }
    .status-pill { display: inline-flex; align-items: center; gap: 6px; background: rgba(76,175,80,0.08); border: 1px solid rgba(76,175,80,0.3); border-radius: 16px; padding: 3px 12px; font-size: 0.68rem; font-family: 'JetBrains Mono', monospace; color: #66BB6A; }
    .status-dot { width:6px; height:6px; background:#66BB6A; border-radius:50%; }
    .metric-card {
        background: rgba(100,181,246,0.03);
        border: 1px solid rgba(100,181,246,0.12); border-radius: 10px;
        padding: 18px 16px; text-align: center;
        animation: fadeUp 0.3s ease;
    }
    .metric-card:hover { border-color: rgba(100,181,246,0.25); }
    .metric-card .metric-value { font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 700; color: #E3F2FD; line-height: 1.1; margin: 0; }
    .metric-card .metric-label { font-size: 0.62rem; letter-spacing: 2px; color: rgba(144,202,249,0.5); font-family: 'JetBrains Mono', monospace; text-transform: uppercase; margin-top: 6px; }
    .metric-card .metric-sub { font-size: 0.7rem; color: #546E7A; margin-top: 4px; }
    .tech-panel { background: rgba(100,181,246,0.02); border: 1px solid rgba(100,181,246,0.08); border-left: 3px solid rgba(100,181,246,0.4); border-radius: 0 6px 6px 0; padding: 12px 16px; margin-bottom: 10px; }
    .tech-panel h4 { color: #90CAF9 !important; font-size: 0.85rem !important; letter-spacing: 1px !important; margin: 0 0 4px 0 !important; }
    .tech-panel p { color: #78909C !important; margin: 4px 0 !important; font-size: 0.82rem !important; }
    .stats-row { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
    .stat-chip { background:rgba(100,181,246,0.04); border:1px solid rgba(100,181,246,0.1); border-radius:6px; padding:6px 10px; font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:#c9d5e0; }
    .stat-chip b { color:#64B5F6; display:block; font-size:1rem; margin-bottom:2px; }
    .grid-line { height: 1px; margin: 10px 0; background: rgba(100,181,246,0.08); border: none; }

    /* ── RETURN PERIOD TABLE ──────────────────────────── */
    .rp-table { width:100%; border-collapse:collapse; font-family:'JetBrains Mono',monospace; font-size:0.75rem; margin-top:8px; }
    .rp-table th { color:rgba(144,202,249,0.5); letter-spacing:1.5px; font-size:0.62rem; padding:5px 8px; border-bottom:1px solid rgba(100,181,246,0.1); text-align:left; }
    .rp-table td { color:#c9d5e0; padding:5px 8px; border-bottom:1px solid rgba(100,181,246,0.05); }
    .rp-table tr:hover td { background:rgba(100,181,246,0.03); }
    .rp-table .rp-val { color:#64B5F6; font-weight:700; }
    .rp-bar { height:4px; background:#64B5F6; border-radius:2px; display:inline-block; vertical-align:middle; margin-left:4px; }

    /* ── DUAL MAP PANEL LABELS ────────────────────────── */
    .dual-label-row { display:flex; gap:0; margin-bottom:4px; }
    .dual-label { flex:1; text-align:center; font-family:'Inter',sans-serif; font-weight:600;
        font-size:0.78rem; letter-spacing:1.5px; color:rgba(144,202,249,0.6);
        background:rgba(100,181,246,0.04); border:1px solid rgba(100,181,246,0.1); padding:5px; }
    .dual-label:first-child { border-radius:6px 0 0 6px; }
    .dual-label:last-child  { border-radius:0 6px 6px 0; border-left:none; }

    /* ── PROGRESSION ──────────────────────────────────── */
    .prog-month-chip { display:inline-block; background:rgba(239,83,80,0.08); border:1px solid rgba(239,83,80,0.2);
        border-radius:6px; padding:3px 8px; font-family:'JetBrains Mono',monospace;
        font-size:0.7rem; color:#EF5350; margin:2px; }
    .infra-legend { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; font-family:'JetBrains Mono',monospace; font-size:0.7rem; }
    .infra-chip { background:rgba(100,181,246,0.04); border:1px solid rgba(100,181,246,0.1);
        border-radius:4px; padding:2px 6px; color:#c9d5e0; }
    .infra-chip span { margin-right:4px; }
    .coord-pill { display:inline-flex; align-items:center; gap:6px; background:rgba(255,183,77,0.07);
        border:1px solid rgba(255,183,77,0.2); border-radius:16px; padding:3px 10px;
        font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#FFB74D; margin-top:6px; }

    /* ── MOBILE RESPONSIVENESS ────────────────────────── */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 260px !important;
            max-width: 280px !important;
        }
        [data-testid="stAppViewBlockContainer"] {
            padding-left: 10px !important;
            padding-right: 10px !important;
            padding-top: 6px !important;
        }
        h1 { font-size: 1.2rem !important; }
        .page-header { padding: 2px 0 8px 0 !important; margin-bottom: 8px !important; }
        .page-header .subtitle { font-size: 0.52rem !important; }
        [data-testid="stTabs"] button[role="tab"] {
            font-size: 0.7rem !important;
            padding: 0.35rem 0.6rem !important;
        }
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        [data-testid="stHorizontalBlock"] > div { width: 100% !important; flex: none !important; }
        .metric-card { padding: 12px 10px !important; }
        .metric-card .metric-value { font-size: 1.6rem !important; }
        .metric-card .metric-label { font-size: 0.55rem !important; }
        .stats-row { gap: 4px !important; }
        .stat-chip { padding: 4px 6px !important; font-size: 0.62rem !important; }
        .dual-label { font-size: 0.62rem !important; padding: 3px !important; }
        .tech-panel { padding: 8px 10px !important; }
        [data-baseweb="slider"] { padding: 6px 0 !important; }
        [data-baseweb="slider"] [role="slider"] { width: 20px !important; height: 20px !important; }
        iframe { max-height: 350px !important; }
    }

    @media (max-width: 480px) {
        h1 { font-size: 1rem !important; }
        .page-header .subtitle { font-size: 0.45rem !important; }
        [data-testid="stTabs"] button[role="tab"] {
            font-size: 0.6rem !important;
            padding: 0.3rem 0.4rem !important;
        }
        .metric-card .metric-value { font-size: 1.3rem !important; }
        [data-testid="stAppViewBlockContainer"] {
            padding-left: 6px !important;
            padding-right: 6px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
