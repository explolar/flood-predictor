"""Tab 6: Multi-Year Comparison Dashboard."""

import streamlit as st
import folium
import pandas as pd
from streamlit_folium import folium_static

from gee_functions.multiyear import get_multiyear_flood_comparison


def render_multiyear_tab(aoi_json, params):
    """Render the multi-year comparison tab."""
    polarization = params['polarization']
    f_threshold = params['f_threshold']
    apply_speckle = params['apply_speckle']
    aoi = params['aoi']
    map_center = params['map_center']

    st.markdown('<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">MULTI-YEAR MONSOON FLOOD COMPARISON · SAR-BASED</div>', unsafe_allow_html=True)

    years_available = list(range(2017, 2025))
    selected_years = st.multiselect(
        "Select years to compare", years_available,
        default=[2020, 2021, 2022, 2023, 2024], key="multiyear_select"
    )

    if st.button("RUN MULTI-YEAR COMPARISON", key="multiyear_btn", use_container_width=True):
        if len(selected_years) < 2:
            st.warning("Select at least 2 years to compare.")
        else:
            with st.spinner(f"Computing flood extent for {len(selected_years)} monsoon seasons..."):
                result = get_multiyear_flood_comparison(
                    aoi_json, years=sorted(selected_years),
                    polarization=polarization, threshold=f_threshold,
                    speckle=apply_speckle
                )

            if result and result['data'] is not None:
                df = result['data']
                valid = df.dropna(subset=['flood_area_ha'])

                # Summary metrics
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Years Analyzed", result['years_analyzed'])
                if not valid.empty:
                    mc2.metric("Peak Flood Year", str(int(valid.loc[valid['flood_area_ha'].idxmax(), 'year'])))
                    mc3.metric("Trend", result['trend'] or 'N/A')

                # Bar chart of flood areas
                if not valid.empty:
                    chart_df = valid.set_index('year')[['flood_area_ha']]
                    chart_df.columns = ['Flood Area (ha)']
                    st.bar_chart(chart_df, color="#FF6B6B", height=250)

                # Side-by-side maps (show first 2 years)
                tile_urls = result['tile_urls']
                years_with_tiles = [y for y in sorted(selected_years) if y in tile_urls]

                if len(years_with_tiles) >= 2:
                    st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:14px 0 6px;">FLOOD EXTENT MAPS</div>', unsafe_allow_html=True)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        yr = years_with_tiles[0]
                        st.markdown(f'<div style="text-align:center;color:#00FFFF;font-size:0.8rem;letter-spacing:2px;">{yr}</div>', unsafe_allow_html=True)
                        m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=tile_urls[yr], attr='GEE', name=f'Flood {yr}', opacity=0.85).add_to(m)
                        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(m)
                        folium_static(m, height=350)
                    with col_b:
                        yr = years_with_tiles[-1]
                        st.markdown(f'<div style="text-align:center;color:#00FFFF;font-size:0.8rem;letter-spacing:2px;">{yr}</div>', unsafe_allow_html=True)
                        m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=tile_urls[yr], attr='GEE', name=f'Flood {yr}', opacity=0.85).add_to(m)
                        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(m)
                        folium_static(m, height=350)

                # Data table
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("Multi-year comparison returned no results.")
    else:
        st.info("Select years and click RUN to compare monsoon flood extent across multiple years.")
