"""Tab 4: Flood Progression."""

import streamlit as st
import folium
from folium.plugins import Fullscreen
from streamlit_folium import folium_static

from gee_functions.chirps import get_progression_stats
from gee_functions.sar import get_all_sar_data, get_month_sar_tile


def render_progression_tab(aoi_json, params):
    """Render the flood progression tab."""
    prog_year = params['prog_year']
    f_start = params['f_start']
    f_end = params['f_end']
    p_start = params['p_start']
    p_end = params['p_end']
    f_threshold = params['f_threshold']
    polarization = params['polarization']
    apply_speckle = params['apply_speckle']
    aoi = params['aoi']
    map_center = params['map_center']

    st.markdown(f'<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">MONSOON FLOOD PROGRESSION · {prog_year}</div>', unsafe_allow_html=True)
    with st.spinner(f"Fetching {prog_year} CHIRPS monthly rainfall..."):
        prog_df = get_progression_stats(aoi_json, prog_year)

    # Get permanent water URL for base layer
    sar_d = get_all_sar_data(aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)

    if prog_df is not None and not prog_df.empty:
        t4c1, t4c2 = st.columns([1, 2])
        with t4c1:
            chart_df = prog_df.set_index('Month')[['Rain (mm)']]
            st.bar_chart(chart_df, color="#FF6B6B", height=250)
            total_rain = prog_df['Rain (mm)'].sum()
            peak_month = prog_df.loc[prog_df['Rain (mm)'].idxmax(), 'Month']
            st.markdown(f'<div class="stats-row"><div class="stat-chip"><b>{total_rain:.0f} mm</b>Season Total</div><div class="stat-chip"><b>{peak_month}</b>Peak Month</div></div>', unsafe_allow_html=True)
        with t4c2:
            month_names = {'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10}
            prog_month = st.radio("Select month for SAR flood map", list(month_names.keys()), horizontal=True)
            prog_month_num = month_names[prog_month]
            with st.spinner(f"Computing SAR flood mask · {prog_month} {prog_year}..."):
                prog_tile = get_month_sar_tile(aoi_json, prog_year, prog_month_num, polarization, f_threshold, apply_speckle)
            m4 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(m4)
            folium.TileLayer(tiles=sar_d['water_url'], attr='GEE', name='Permanent Water').add_to(m4)
            if prog_tile:
                folium.TileLayer(tiles=prog_tile, attr='GEE', name=f'Flood · {prog_month} {prog_year}', opacity=0.85).add_to(m4)
            Fullscreen(position='topright').add_to(m4)
            folium.LayerControl(position='topright', collapsed=False).add_to(m4)
            folium_static(m4, height=420)
        chips_html = ''.join(f'<span class="prog-month-chip">{row["Month"]} · {row["Rain (mm)"]} mm</span>' for _, row in prog_df.iterrows())
        st.markdown(f'<div>{chips_html}</div>', unsafe_allow_html=True)
        # ── TIMELAPSE ANIMATION ──────────────────────
        with st.expander("FLOOD TIMELAPSE ANIMATION", expanded=False):
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:8px;">LEAFLET.JS ANIMATION · MONTHLY SAR FRAMES · PLAY/PAUSE</div>', unsafe_allow_html=True)
            if st.button("GENERATE TIMELAPSE", key="timelapse_btn", use_container_width=True):
                with st.spinner("Generating monthly SAR flood tiles for animation..."):
                    try:
                        import streamlit.components.v1 as components
                        from ui_components.animation import generate_timelapse_html
                        tile_urls = []
                        labels = []
                        month_map = {6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct'}
                        for m_num, m_name in month_map.items():
                            tile = get_month_sar_tile(aoi_json, prog_year, m_num, polarization, f_threshold, apply_speckle)
                            if tile:
                                tile_urls.append(tile)
                                labels.append(f'{m_name} {prog_year}')
                        if tile_urls:
                            html = generate_timelapse_html(tile_urls, map_center, labels)
                            components.html(html, height=520, scrolling=False)
                        else:
                            st.warning("No SAR tiles available for animation.")
                    except Exception as e:
                        st.error(f"Timelapse generation failed: {e}")
            else:
                st.info("Click to generate a playable flood progression animation.")
    else:
        st.warning(f"Could not fetch CHIRPS data for {prog_year}.")
