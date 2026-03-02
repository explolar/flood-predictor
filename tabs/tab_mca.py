"""Tab 1: MCA Susceptibility Map."""

import streamlit as st
import folium
from folium.plugins import Fullscreen, MiniMap
from streamlit_folium import st_folium

from gee_functions.core import get_aoi_stats
from gee_functions.mca import calculate_flood_risk, get_mca_tile
from gee_functions.layers import get_jrc_freq_tile, get_s2_rgb_tile
from gee_functions.watershed import get_watershed_geojson
from ui_components.legends import get_mca_legend


def render_mca_tab(aoi_json, params):
    """Render the MCA susceptibility tab."""
    w_lulc = params['w_lulc']
    w_slope = params['w_slope']
    w_rain = params['w_rain']
    aoi = params['aoi']
    map_center = params['map_center']

    with st.expander("AOI TERRAIN STATISTICS", expanded=True):
        with st.spinner("Computing terrain stats..."):
            stats = get_aoi_stats(aoi_json)
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
            risk_img = calculate_flood_risk(aoi, w_lulc, w_slope, w_rain)
            mca_url = risk_img.getDownloadUrl({'scale': 30, 'crs': 'EPSG:4326', 'format': 'GeoTIFF'})
            st.link_button("DOWNLOAD MCA GEOTIFF", mca_url, use_container_width=True)
        except Exception:
            st.warning("Area too large for direct download.")

    with c2:
        with st.spinner("Rendering MCA risk map..."):
            mca_tile = get_mca_tile(aoi_json, w_lulc, w_slope, w_rain)
        m1 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
        folium.GeoJson(aoi.getInfo(), name='AOI Boundary',
            style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(m1)
        if "Flood Frequency (JRC)" in extra_layers:
            with st.spinner("Loading JRC flood frequency..."):
                jrc_tile = get_jrc_freq_tile(aoi_json)
            folium.TileLayer(tiles=jrc_tile, attr='GEE·JRC', name='Flood Frequency', opacity=0.7).add_to(m1)
        if "Sentinel-2 True Color" in extra_layers:
            with st.spinner("Loading Sentinel-2 RGB..."):
                s2_tile = get_s2_rgb_tile(aoi_json)
            if s2_tile:
                folium.TileLayer(tiles=s2_tile, attr='GEE·ESA', name='Sentinel-2 RGB', opacity=0.8).add_to(m1)
            else:
                st.warning("Sentinel-2 true color unavailable — no cloud-free scenes for 2024.")
        if "Watershed (HydroSHEDS)" in extra_layers:
            with st.spinner("Loading watershed boundaries..."):
                ws_geojson = get_watershed_geojson(aoi_json)
            if ws_geojson:
                folium.GeoJson(ws_geojson, name='Watershed Boundary',
                    style_function=lambda _: {'fillColor': 'rgba(255,200,0,0.05)', 'color': '#FFD700', 'weight': 1.5, 'dashArray': '4 3'}).add_to(m1)
        folium.TileLayer(tiles=mca_tile, attr='GEE', name='Risk Score').add_to(m1)
        Fullscreen(position='topright', force_separate_button=True).add_to(m1)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m1)
        folium.LayerControl(position='topright', collapsed=False).add_to(m1)
        m1.get_root().html.add_child(folium.Element(get_mca_legend(m1.get_name())))
        map_data = st_folium(m1, height=560, use_container_width=True, key="tab1_map", returned_objects=["last_clicked"])
        if map_data and map_data.get('last_clicked'):
            lc = map_data['last_clicked']
            st.session_state.clicked_coord = (round(lc['lat'], 5), round(lc['lng'], 5))

    # ── URBAN FLOOD VULNERABILITY ──────────────────
    with st.expander("URBAN FLOOD VULNERABILITY INDEX  [UFVI]", expanded=False):
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">IMPERVIOUSNESS · ELEVATION · SLOPE · POPULATION · DRAINAGE PROXY</div>', unsafe_allow_html=True)
        if st.button("COMPUTE UFVI", key="ufvi_btn", use_container_width=True):
            with st.spinner("Computing Urban Flood Vulnerability Index..."):
                try:
                    from gee_functions.urban_vulnerability import get_urban_vulnerability_index
                    ufvi = get_urban_vulnerability_index(aoi_json)
                    if ufvi:
                        uc1, uc2, uc3 = st.columns(3)
                        uc1.metric("Mean UFVI", f"{ufvi['mean_ufvi']:.1f} / 100")
                        uc2.metric("Urban Coverage", f"{ufvi['urban_pct']:.1f} %")
                        uc3.metric("Components", "4 weighted layers")
                        import folium as fol
                        from streamlit_folium import folium_static as fs
                        ufvi_map = fol.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        fol.TileLayer(tiles=ufvi['tile_url'], attr='GEE·UFVI', name='UFVI', opacity=0.8).add_to(ufvi_map)
                        fol.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(ufvi_map)
                        fol.LayerControl(position='topright', collapsed=False).add_to(ufvi_map)
                        fs(ufvi_map, height=400)
                    else:
                        st.warning("UFVI computation returned no results.")
                except Exception as e:
                    st.error(f"UFVI computation failed: {e}")
        else:
            st.info("Click to compute the Urban Flood Vulnerability Index combining imperviousness, elevation, slope, and population.")
