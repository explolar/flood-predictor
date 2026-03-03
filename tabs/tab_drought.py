"""Tab 7: Drought Monitoring."""

import json
import streamlit as st
import folium
from streamlit_folium import folium_static

from gee_functions.drought import get_spi_index, get_ndvi_anomaly


def render_drought_tab(aoi_json, params):
    """Render the drought monitoring tab."""
    aoi = params['aoi']
    map_center = params['map_center']

    st.markdown('<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(144,202,249,0.4);margin-bottom:8px;">DROUGHT MONITORING · SPI · NDVI ANOMALY</div>', unsafe_allow_html=True)

    drought_year = st.selectbox("Target Year", list(range(2024, 2004, -1)), index=0, key="drought_year")

    # ── SPI INDEX ──────────────────────────────────
    with st.expander("STANDARDIZED PRECIPITATION INDEX (SPI)", expanded=True):
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">CHIRPS · 20-YEAR BASELINE · ANNUAL SPI</div>', unsafe_allow_html=True)
        if st.button("COMPUTE SPI", key="spi_btn", use_container_width=True):
            with st.spinner(f"Computing SPI for {drought_year}..."):
                try:
                    spi = get_spi_index(aoi_json, target_year=drought_year)
                    if spi:
                        spi_color = '#d73027' if spi['spi_value'] < -1 else '#1a9850' if spi['spi_value'] > 1 else '#ffffbf'
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("SPI Value", f"{spi['spi_value']:.2f}")
                        sc2.metric("Category", spi['category'])
                        sc3.metric("Baseline", f"{spi['baseline_years']} years")
                        st.markdown(f'<div style="display:inline-flex;align-items:center;gap:8px;background:rgba(144,202,249,0.04);border:1px solid {spi_color};border-radius:8px;padding:8px 16px;margin:8px 0;"><div style="width:10px;height:10px;background:{spi_color};border-radius:50%;"></div><div style="font-family:\'Inter\',sans-serif;font-size:0.9rem;font-weight:700;color:{spi_color};letter-spacing:2px;">{spi["category"].upper()}</div></div>', unsafe_allow_html=True)

                        spi_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=spi['tile_url'], attr='GEE·CHIRPS', name='SPI Index', opacity=0.8).add_to(spi_map)
                        folium.GeoJson(json.loads(aoi_json), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(spi_map)
                        folium.LayerControl(position='topright', collapsed=False).add_to(spi_map)
                        folium_static(spi_map, height=400)
                    else:
                        st.warning("SPI computation returned no results.")
                except Exception as e:
                    st.error(f"SPI computation failed: {e}")
        else:
            st.info("Click to compute the Standardized Precipitation Index for the selected year.")

    # ── NDVI ANOMALY ───────────────────────────────
    with st.expander("NDVI VEGETATION ANOMALY  [MODIS]", expanded=False):
        st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">MODIS MOD13A2 · 20-YEAR CLIMATOLOGY · VEGETATION HEALTH</div>', unsafe_allow_html=True)
        if st.button("COMPUTE NDVI ANOMALY", key="ndvi_anom_btn", use_container_width=True):
            with st.spinner(f"Computing NDVI anomaly for {drought_year}..."):
                try:
                    ndvi = get_ndvi_anomaly(aoi_json, target_year=drought_year)
                    if ndvi:
                        nc1, nc2 = st.columns(2)
                        nc1.metric("NDVI Anomaly", f"{ndvi['anomaly_value']:.4f}")
                        nc2.metric("Interpretation", ndvi['interpretation'][:40])

                        ndvi_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=ndvi['tile_url'], attr='GEE·MODIS', name='NDVI Anomaly', opacity=0.8).add_to(ndvi_map)
                        folium.GeoJson(json.loads(aoi_json), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(ndvi_map)
                        folium.LayerControl(position='topright', collapsed=False).add_to(ndvi_map)
                        folium_static(ndvi_map, height=400)
                    else:
                        st.warning("NDVI anomaly returned no results.")
                except Exception as e:
                    st.error(f"NDVI anomaly computation failed: {e}")
        else:
            st.info("Click to compare current vegetation against 20-year MODIS climatology.")
