"""Tab 3: Dual-View SAR Comparison."""

import streamlit as st
import folium
from folium.plugins import DualMap
import streamlit.components.v1 as components

from gee_functions.sar import get_all_sar_data
from gee_functions.layers import get_s2_rgb_tiles


def render_dual_tab(aoi_json, params):
    """Render the dual-view comparison tab."""
    f_start = params['f_start']
    f_end = params['f_end']
    p_start = params['p_start']
    p_end = params['p_end']
    f_threshold = params['f_threshold']
    polarization = params['polarization']
    apply_speckle = params['apply_speckle']
    aoi = params['aoi']
    map_center = params['map_center']

    st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">SYNCHRONIZED PRE / POST SAR BACKSCATTER COMPARISON</div>', unsafe_allow_html=True)
    with st.spinner("Building dual-view SAR comparison..."):
        sar_d = get_all_sar_data(aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
    if sar_d is None:
        st.error("SAR analysis failed — no Sentinel-1 data found for the selected dates/AOI. Try adjusting dates or AOI.")
        return
    st.markdown('<div class="dual-label-row"><div class="dual-label">◀ PRE-FLOOD SAR</div><div class="dual-label">POST-FLOOD SAR ▶</div></div>', unsafe_allow_html=True)
    dmap = DualMap(location=map_center, zoom_start=11, tiles=None, layout='horizontal')
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap.m1)
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap.m2)
    folium.TileLayer(tiles=sar_d['pre_url'], attr='GEE', name=f'Pre-flood {polarization}').add_to(dmap.m1)
    folium.TileLayer(tiles=sar_d['post_url'], attr='GEE', name=f'Post-flood {polarization}').add_to(dmap.m2)
    folium.TileLayer(tiles=sar_d['flood_url'], attr='GEE', name='Flood Mask', opacity=0.6).add_to(dmap.m2)
    folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(dmap.m1)
    folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(dmap.m2)
    components.html(dmap._repr_html_(), height=580, scrolling=False)
    d3c1, d3c2, d3c3 = st.columns(3)
    d3c1.metric("Pre-flood Period", f"{p_start} → {p_end}")
    d3c2.metric("Post-flood Period", f"{f_start} → {f_end}")
    d3c3.metric("Detected Flood", f"{sar_d['area_ha']} Ha")

    st.markdown('<hr style="border-color:rgba(0,255,255,0.1);margin:28px 0 20px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">SENTINEL-2 TRUE COLOR · PRE vs POST</div>', unsafe_allow_html=True)
    with st.spinner("Loading Sentinel-2 true-color imagery..."):
        s2_rgb = get_s2_rgb_tiles(aoi_json, str(p_start), str(p_end), str(f_start), str(f_end))
    if s2_rgb:
        st.markdown('<div class="dual-label-row"><div class="dual-label">◀ PRE-FLOOD TRUE COLOR</div><div class="dual-label">POST-FLOOD TRUE COLOR ▶</div></div>', unsafe_allow_html=True)
        dmap_s2 = DualMap(location=map_center, zoom_start=11, tiles=None, layout='horizontal')
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap_s2.m1)
        folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", attr='CartoDB', name='Basemap').add_to(dmap_s2.m2)
        folium.TileLayer(tiles=s2_rgb['pre_url'], attr='GEE·S2', name='Pre-flood S2').add_to(dmap_s2.m1)
        folium.TileLayer(tiles=s2_rgb['post_url'], attr='GEE·S2', name='Post-flood S2').add_to(dmap_s2.m2)
        folium.TileLayer(tiles=sar_d['flood_url'], attr='GEE', name='Flood Mask', opacity=0.5).add_to(dmap_s2.m2)
        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(dmap_s2.m1)
        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(dmap_s2.m2)
        components.html(dmap_s2._repr_html_(), height=520, scrolling=False)
    else:
        st.info("Sentinel-2 true-color unavailable — insufficient cloud-free scenes.")

    # ── 3D TERRAIN VISUALIZATION ───────────────────
    with st.expander("3D TERRAIN FLOOD VIEW  [PyDeck]", expanded=False):
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">SRTM DEM · PYDECK COLUMNLAYER · INTERACTIVE 3D</div>', unsafe_allow_html=True)
        if st.button("RENDER 3D TERRAIN", key="deck3d_btn", use_container_width=True):
            with st.spinner("Extracting DEM grid from GEE & building 3D visualization..."):
                try:
                    from ui_components.deck_viz import create_3d_terrain_view, extract_dem_grid
                    dem_data = extract_dem_grid(aoi_json, scale=200)
                    if dem_data:
                        deck = create_3d_terrain_view(aoi_json, dem_data=dem_data, map_center=map_center)
                        if deck:
                            st.pydeck_chart(deck, height=500)
                        else:
                            st.warning("PyDeck not available. Install with: pip install pydeck")
                    else:
                        st.warning("Could not extract DEM data for 3D visualization.")
                except ImportError:
                    st.error("pydeck is required for 3D visualization. Run: pip install pydeck")
                except Exception as e:
                    st.error(f"3D terrain rendering failed: {e}")
        else:
            st.info("Click to render an interactive 3D terrain view with DEM elevation.")
