"""Tab 6: Hydrology — Watershed Delineation, Stream Network, Terrain Analysis."""

import json
import streamlit as st
import folium
import pandas as pd
from folium.plugins import Fullscreen, MiniMap
from streamlit_folium import folium_static

from gee_functions.watershed import (
    get_all_hydrology_data,
    get_multi_basin_geojson,
    get_drainage_density,
    get_basin_statistics,
)
from ui_components.legends import get_stream_order_legend, get_flow_acc_legend


def render_hydrology_tab(aoi_json, params):
    """Render the HYDROLOGY tab with Watershed / Streams / Terrain sub-tabs."""
    map_center = params['map_center']

    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
        'letter-spacing:2px;color:rgba(144,202,249,0.4);margin-bottom:8px;">'
        'HYDROSHEDS · FLOW ACCUMULATION · STREAM NETWORK · 3 ARC-SEC</div>',
        unsafe_allow_html=True,
    )

    hydro_sub1, hydro_sub2, hydro_sub3 = st.tabs([
        "  WATERSHED  ", "  STREAMS  ", "  TERRAIN  "
    ])
    with hydro_sub1:
        _render_watershed(aoi_json, map_center)
    with hydro_sub2:
        _render_streams(aoi_json, map_center)
    with hydro_sub3:
        _render_terrain(aoi_json, map_center)


# ── Sub-tab 1: Watershed ─────────────────────────────────────

def _render_watershed(aoi_json, map_center):
    """Multi-level basin hierarchy from HydroSHEDS."""
    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.68rem;'
        'letter-spacing:2px;color:rgba(144,202,249,0.35);margin-bottom:8px;">'
        'WWF HYDROSHEDS v1 · BASIN HIERARCHY · LEVELS 6 / 8 / 10</div>',
        unsafe_allow_html=True,
    )

    try:
        with st.spinner('Loading watershed boundaries...'):
            basins = get_multi_basin_geojson(aoi_json)
    except Exception as e:
        st.error(f'Failed to load HydroSHEDS basin data — {e}')
        return

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric('Level 6 (Major)', f'{basins["hybas_6"]["count"]} basins')
    m2.metric('Level 8 (Sub-basin)', f'{basins["hybas_8"]["count"]} basins')
    m3.metric('Level 10 (Micro)', f'{basins["hybas_10"]["count"]} basins')

    st.markdown('<br>', unsafe_allow_html=True)

    # Controls + Map
    col_ctrl, col_map = st.columns([1, 3])

    with col_ctrl:
        basin_level = st.radio(
            'Basin Level',
            ['All Levels', 'Level 6 (Major)', 'Level 8 (Sub-basin)', 'Level 10 (Micro)'],
            key='hydro_basin_level',
        )
        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.72rem;color:rgba(144,202,249,0.5);'
            'font-family:\'Inter\',sans-serif;">'
            '<strong>HydroSHEDS v1</strong><br>'
            'Lehner & Grill (2013). Global river hydrography derived from '
            'spaceborne elevation data. WWF.<br><br>'
            '<strong>Level 6</strong> — major river basins<br>'
            '<strong>Level 8</strong> — sub-basins<br>'
            '<strong>Level 10</strong> — micro-basins'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_map:
        m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB dark_matter')
        folium.GeoJson(
            json.loads(aoi_json), name='AOI Boundary',
            style_function=lambda _: {
                'fillColor': 'none', 'color': '#00FFFF',
                'weight': 2, 'dashArray': '6 4',
            },
        ).add_to(m)

        level_styles = {
            'hybas_6': {'color': '#FFD700', 'weight': 3, 'dashArray': '8 4', 'name': 'Level 6'},
            'hybas_8': {'color': '#FFA500', 'weight': 2, 'dashArray': '6 3', 'name': 'Level 8'},
            'hybas_10': {'color': '#FF6347', 'weight': 1.5, 'dashArray': '4 2', 'name': 'Level 10'},
        }

        show_levels = []
        if basin_level == 'All Levels':
            show_levels = ['hybas_6', 'hybas_8', 'hybas_10']
        elif 'Level 6' in basin_level:
            show_levels = ['hybas_6']
        elif 'Level 8' in basin_level:
            show_levels = ['hybas_8']
        elif 'Level 10' in basin_level:
            show_levels = ['hybas_10']

        for lvl in show_levels:
            gj = basins[lvl].get('geojson')
            if gj:
                style = level_styles[lvl]
                folium.GeoJson(
                    gj, name=f'Watershed {style["name"]}',
                    style_function=lambda _, s=style: {
                        'fillColor': 'rgba(255,200,0,0.03)',
                        'color': s['color'],
                        'weight': s['weight'],
                        'dashArray': s['dashArray'],
                    },
                ).add_to(m)

        Fullscreen(position='topright', force_separate_button=True).add_to(m)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright',
                toggle_display=True, zoom_level_offset=-6).add_to(m)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, height=500)

    # Basin statistics expander
    with st.expander('BASIN STATISTICS (Level 8)', expanded=False):
        if st.button('Load Statistics', key='hydro_stats_btn', use_container_width=True):
            try:
                with st.spinner('Computing per-basin statistics...'):
                    stats = get_basin_statistics(aoi_json)
            except Exception as e:
                st.warning(f'Basin statistics failed — {e}')
                stats = []
            if stats:
                st.dataframe(pd.DataFrame(stats), use_container_width=True, hide_index=True)
            else:
                st.warning('No basin statistics available.')
        else:
            st.info('Click to compute per-basin area, upstream area, and mean elevation.')


# ── Sub-tab 2: Streams ───────────────────────────────────────

def _render_streams(aoi_json, map_center):
    """Stream network extracted from flow accumulation."""
    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.68rem;'
        'letter-spacing:2px;color:rgba(144,202,249,0.35);margin-bottom:8px;">'
        'HYDROSHEDS 03ACC · STREAM EXTRACTION · STRAHLER PROXY</div>',
        unsafe_allow_html=True,
    )

    # Threshold slider
    stream_threshold = st.slider(
        'Stream Threshold (upstream cells)',
        min_value=50, max_value=500, value=100, step=50,
        help='Minimum upstream cell count to classify a pixel as stream. '
             'Lower = more streams, higher = only major channels.',
        key='hydro_stream_thresh',
    )

    try:
        with st.spinner('Computing stream network...'):
            hydro = get_all_hydrology_data(aoi_json, stream_threshold)
    except Exception as e:
        st.error(f'Stream network computation failed — {e}')
        return

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric('Stream Length', f'{hydro["stream_length_km"]} km')
    m2.metric('Max Accumulation', f'{hydro["max_accumulation"]:,.0f} cells')
    m3.metric('Mean Accumulation', f'{hydro["mean_accumulation"]:,.0f} cells')

    st.markdown('<br>', unsafe_allow_html=True)

    # Controls + Map
    col_ctrl, col_map = st.columns([1, 3])

    with col_ctrl:
        stream_layer = st.radio(
            'Map Layer',
            ['Stream Order', 'Flow Accumulation'],
            key='hydro_stream_layer',
        )
        st.markdown('<br>', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:0.72rem;color:rgba(144,202,249,0.5);'
            'font-family:\'Inter\',sans-serif;">'
            '<strong>Stream Order (Proxy)</strong><br>'
            'Approximated via log10 binning of flow accumulation. '
            'Correlates with Strahler order per Horton\'s laws.<br><br>'
            f'<strong>Threshold:</strong> {stream_threshold} cells<br>'
            f'<strong>Pixel size:</strong> ~90 m (3 arc-sec)'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_map:
        m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB dark_matter')
        folium.GeoJson(
            json.loads(aoi_json), name='AOI Boundary',
            style_function=lambda _: {
                'fillColor': 'none', 'color': '#00FFFF',
                'weight': 2, 'dashArray': '6 4',
            },
        ).add_to(m)

        if stream_layer == 'Stream Order':
            folium.TileLayer(
                tiles=hydro['stream_url'], attr='GEE · HydroSHEDS',
                name='Stream Order', opacity=0.9,
            ).add_to(m)
            m.get_root().html.add_child(
                folium.Element(get_stream_order_legend(m.get_name()))
            )
        else:
            folium.TileLayer(
                tiles=hydro['flow_acc_url'], attr='GEE · HydroSHEDS',
                name='Flow Accumulation (log)', opacity=0.8,
            ).add_to(m)
            m.get_root().html.add_child(
                folium.Element(get_flow_acc_legend(m.get_name()))
            )

        Fullscreen(position='topright', force_separate_button=True).add_to(m)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright',
                toggle_display=True, zoom_level_offset=-6).add_to(m)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, height=500)

    # Drainage density expander
    with st.expander('DRAINAGE DENSITY', expanded=False):
        if st.button('Compute Drainage Density', key='hydro_dd_btn', use_container_width=True):
            try:
                with st.spinner('Computing spatial drainage density...'):
                    dd = get_drainage_density(aoi_json, stream_threshold)
            except Exception as e:
                st.warning(f'Drainage density computation failed — {e}')
                dd = None
            if dd:
                dc1, dc2, dc3 = st.columns(3)
                dc1.metric('Drainage Density', f'{dd["scalar_density"]} km/km\u00b2')
                dc2.metric('Total Stream Length', f'{dd["total_length_km"]} km')
                dc3.metric('AOI Area', f'{dd["area_km2"]} km\u00b2')

                m_dd = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB dark_matter')
                folium.GeoJson(
                    json.loads(aoi_json), name='AOI',
                    style_function=lambda _: {
                        'fillColor': 'none', 'color': '#00FFFF',
                        'weight': 2, 'dashArray': '6 4',
                    },
                ).add_to(m_dd)
                folium.TileLayer(
                    tiles=dd['density_url'], attr='GEE · HydroSHEDS',
                    name='Drainage Density', opacity=0.8,
                ).add_to(m_dd)
                Fullscreen(position='topright').add_to(m_dd)
                folium.LayerControl(position='topright', collapsed=False).add_to(m_dd)
                folium_static(m_dd, height=400)
            else:
                st.warning('Drainage density computation failed.')
        else:
            st.info('Click to compute drainage density (km of stream per km\u00b2).')


# ── Sub-tab 3: Terrain ───────────────────────────────────────

def _render_terrain(aoi_json, map_center):
    """Flow accumulation, flow direction, conditioned DEM visualization."""
    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.68rem;'
        'letter-spacing:2px;color:rgba(144,202,249,0.35);margin-bottom:8px;">'
        'HYDROSHEDS · FLOW ACCUMULATION · FLOW DIRECTION · CONDITIONED DEM</div>',
        unsafe_allow_html=True,
    )

    try:
        with st.spinner('Loading terrain data...'):
            hydro = get_all_hydrology_data(aoi_json)
    except Exception as e:
        st.error(f'Terrain data loading failed — {e}')
        return

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric('DEM Min', f'{hydro["dem_min"]} m')
    m2.metric('DEM Max', f'{hydro["dem_max"]} m')
    m3.metric('DEM Mean', f'{hydro["dem_mean"]} m')

    st.markdown('<br>', unsafe_allow_html=True)

    # Controls + Map
    col_ctrl, col_map = st.columns([1, 3])

    with col_ctrl:
        terrain_layer = st.radio(
            'Map Layer',
            ['Flow Accumulation', 'Flow Direction', 'Conditioned DEM'],
            key='hydro_terrain_layer',
        )
        st.markdown('<br>', unsafe_allow_html=True)

        layer_info = {
            'Flow Accumulation': (
                'Number of upstream cells draining through each pixel. '
                'Displayed in log10 scale. High values indicate channels and valleys.'
            ),
            'Flow Direction': (
                'D8 flow direction encoded as powers of 2: '
                '1=E, 2=SE, 4=S, 8=SW, 16=W, 32=NW, 64=N, 128=NE. '
                'Each pixel drains to one of 8 neighbours.'
            ),
            'Conditioned DEM': (
                'Hydrologically conditioned SRTM DEM from HydroSHEDS. '
                'Sinks and flat areas have been filled/resolved to ensure '
                'continuous drainage paths.'
            ),
        }
        st.markdown(
            f'<div style="font-size:0.72rem;color:rgba(144,202,249,0.5);'
            f'font-family:\'Inter\',sans-serif;">{layer_info[terrain_layer]}</div>',
            unsafe_allow_html=True,
        )

    with col_map:
        layer_map = {
            'Flow Accumulation': ('flow_acc_url', 'Flow Accumulation (log)', 0.8),
            'Flow Direction': ('flow_dir_url', 'Flow Direction (D8)', 0.8),
            'Conditioned DEM': ('cond_dem_url', 'Conditioned DEM', 0.85),
        }
        url_key, layer_name, opacity = layer_map[terrain_layer]

        m = folium.Map(location=map_center, zoom_start=11, tiles='CartoDB dark_matter')
        folium.GeoJson(
            json.loads(aoi_json), name='AOI Boundary',
            style_function=lambda _: {
                'fillColor': 'none', 'color': '#00FFFF',
                'weight': 2, 'dashArray': '6 4',
            },
        ).add_to(m)
        folium.TileLayer(
            tiles=hydro[url_key], attr='GEE · HydroSHEDS',
            name=layer_name, opacity=opacity,
        ).add_to(m)

        if terrain_layer == 'Flow Accumulation':
            m.get_root().html.add_child(
                folium.Element(get_flow_acc_legend(m.get_name()))
            )

        Fullscreen(position='topright', force_separate_button=True).add_to(m)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright',
                toggle_display=True, zoom_level_offset=-6).add_to(m)
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        folium_static(m, height=500)

    # Methodology expander
    with st.expander('METHODOLOGY', expanded=False):
        st.markdown(
            '<div style="font-size:0.78rem;color:rgba(144,202,249,0.6);'
            'font-family:\'Inter\',sans-serif;line-height:1.8;">'
            '<strong>Data Source:</strong> WWF HydroSHEDS (Lehner & Grill, 2013) '
            'derived from SRTM 3 arc-second (~90 m) DEM.<br>'
            '<strong>Flow Accumulation:</strong> Pre-computed upstream cell count '
            '(03ACC). Displayed in log10 scale for visual clarity.<br>'
            '<strong>Flow Direction:</strong> D8 algorithm — each pixel assigned one '
            'of 8 drainage directions based on steepest descent.<br>'
            '<strong>Stream Order:</strong> Approximated by log10-binning flow accumulation '
            'into 5 classes. Correlates with Strahler order per Horton\'s bifurcation ratio.<br>'
            '<strong>Conditioned DEM:</strong> Hydrologically conditioned — sinks filled, '
            'flat areas resolved for continuous drainage routing.'
            '</div>',
            unsafe_allow_html=True,
        )
