"""Tab 8: Spectral Indices Download — NDVI, NDWI, MNDWI, NDBI, SAVI, EVI, BSI."""

import streamlit as st
import folium
import pandas as pd
from folium.plugins import Fullscreen, MiniMap
from streamlit_folium import folium_static

from gee_functions.indices import INDEX_REGISTRY, get_index_tile
from ui_components.legends import get_index_legend
from ui_components.reports import generate_index_pdf_bytes


def render_indices_tab(aoi_json, params):
    """Render the Spectral Indices Download tab."""
    aoi = params['aoi']
    map_center = params['map_center']
    p_start = params['p_start']
    f_end = params['f_end']

    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;'
        'letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:8px;">'
        'SENTINEL-2 SR  ·  SPECTRAL INDICES  ·  10 m  ·  GEOTIFF &amp; PDF EXPORT</div>',
        unsafe_allow_html=True,
    )

    # ── Date range selector ───────────────────────────
    hdr1, hdr2 = st.columns(2)
    with hdr1:
        idx_start = st.date_input('Imagery Start Date', value=p_start, key='idx_start')
    with hdr2:
        idx_end = st.date_input('Imagery End Date', value=f_end, key='idx_end')

    date_start = str(idx_start)
    date_end = str(idx_end)

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Sub-tabs: one per index ───────────────────────
    index_keys = list(INDEX_REGISTRY.keys())
    sub_tabs = st.tabs([f'  {k}  ' for k in index_keys])

    for tab_widget, index_key in zip(sub_tabs, index_keys):
        with tab_widget:
            _render_single_index(index_key, aoi_json, aoi, map_center, date_start, date_end)


def _render_single_index(index_key, aoi_json, aoi, map_center, date_start, date_end):
    """Render a single index panel: map + downloads + info."""
    meta = INDEX_REGISTRY[index_key]

    st.markdown(
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        f'color:rgba(0,255,255,0.5);letter-spacing:2px;margin-bottom:8px;">'
        f'{index_key} = {meta["formula"]}  ·  {meta["source"]}</div>',
        unsafe_allow_html=True,
    )

    if st.button(f'COMPUTE {index_key}', key=f'compute_{index_key}', use_container_width=True):
        st.session_state[f'{index_key}_computed'] = True

    if not st.session_state.get(f'{index_key}_computed'):
        st.info(f'Click **COMPUTE {index_key}** to load the {meta["label"]} from Sentinel-2 imagery ({date_start} to {date_end}).')
        _render_info_expander(index_key, meta)
        return

    with st.spinner(f'Computing {index_key} from Sentinel-2...'):
        result = get_index_tile(aoi_json, index_key, date_start, date_end)

    if result is None:
        st.error(f'No cloud-free Sentinel-2 scenes found for {date_start} to {date_end}. Try expanding the date range.')
        return

    # ── Metrics ───────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric(f'Mean {index_key}', f'{result["mean_value"]:.4f}')
    m2.metric('Scenes Composited', result['n_scenes'])
    m3.metric('Scale', '10 m')

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Layout: controls | map ────────────────────────
    col_ctrl, col_map = st.columns([1, 3])

    with col_ctrl:
        mean_v = result['mean_value']
        class_label = _classify(mean_v, meta['classes'])
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-label">AOI MEAN CLASS</div>'
            f'<div class="metric-value" style="font-size:1.1rem;">{class_label}</div>'
            f'<div class="metric-sub">{index_key} = {mean_v:.4f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<br>', unsafe_allow_html=True)

        # GeoTIFF download
        try:
            st.link_button(
                f'DOWNLOAD {index_key} GEOTIFF',
                result['download_url'],
                use_container_width=True,
            )
        except Exception:
            st.warning('GeoTIFF download unavailable — AOI may be too large.')

        st.markdown('<br>', unsafe_allow_html=True)

        # PDF download
        aoi_coords = _get_aoi_coords(aoi)
        pdf_bytes = generate_index_pdf_bytes(
            index_key=index_key,
            index_data=result,
            aoi_coords=aoi_coords,
            date_start=date_start,
            date_end=date_end,
        )
        if pdf_bytes:
            st.download_button(
                label=f'DOWNLOAD {index_key} PDF MAP',
                data=pdf_bytes,
                file_name=f'HydroRisk_{index_key}_Map.pdf',
                mime='application/pdf',
                use_container_width=True,
                key=f'pdf_btn_{index_key}',
            )
        else:
            st.caption('PDF export unavailable')

    with col_map:
        m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB dark_matter')
        folium.GeoJson(
            aoi.getInfo(), name='AOI Boundary',
            style_function=lambda _: {
                'fillColor': 'none', 'color': '#00FFFF',
                'weight': 2, 'dashArray': '6 4',
            },
        ).add_to(m)
        folium.TileLayer(
            tiles=result['tile_url'],
            attr=f'GEE · Sentinel-2 · {index_key}',
            name=f'{index_key} Classified',
            opacity=0.85,
        ).add_to(m)
        Fullscreen(position='topright', force_separate_button=True).add_to(m)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright',
                toggle_display=True, zoom_level_offset=-6).add_to(m)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        m.get_root().html.add_child(
            folium.Element(get_index_legend(m.get_name(), index_key))
        )
        folium_static(m, height=520)

    # ── Info section ──────────────────────────────────
    _render_info_expander(index_key, meta)


def _render_info_expander(index_key, meta):
    """Show methodology and classification basis for an index."""
    with st.expander(f'INFO & METHODOLOGY — {index_key}', expanded=False):
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            f'color:rgba(0,255,255,0.4);letter-spacing:2px;margin-bottom:10px;">'
            f'CLASSIFICATION BASIS · SENTINEL-2 SR · COPERNICUS</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="tech-panel">'
            f'<h4>{meta["label"]}</h4>'
            f'<p><strong>Formula:</strong> <code>{meta["formula"]}</code></p>'
            f'<p><strong>Data Source:</strong> {meta["source"]}</p>'
            f'<hr class="grid-line">'
            f'<p>{meta["info"]}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('**Classification Thresholds:**')
        st.dataframe(
            pd.DataFrame({
                'Class': [c[3] for c in meta['classes']],
                'Min Value': [c[0] for c in meta['classes']],
                'Max Value': [c[1] for c in meta['classes']],
            }),
            use_container_width=True,
            hide_index=True,
        )


def _classify(value, classes):
    """Return the class label for a given mean index value."""
    for (lo, hi, _color, label) in classes:
        if lo <= value < hi:
            return label
    return 'Out of Range'


def _get_aoi_coords(aoi):
    """Extract [min_lon, min_lat, max_lon, max_lat] from an ee.Geometry."""
    try:
        info = aoi.bounds().getInfo()
        coords = info['coordinates'][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return [min(lons), min(lats), max(lons), max(lats)]
    except Exception:
        return 'AOI'
