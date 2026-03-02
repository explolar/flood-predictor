"""Tab 2: SAR Inundation Detection."""

import streamlit as st
import folium
import pandas as pd
from folium.plugins import Fullscreen, MiniMap
from streamlit_folium import folium_static

from gee_functions.sar import get_all_sar_data, get_flood_depth_tile, get_recession_data
from gee_functions.chirps import get_chirps_series, get_return_period
from gee_functions.layers import get_ndvi_tile, get_jrc_flood_history
from gee_functions.infrastructure import get_osm_infrastructure, get_osm_roads, get_dam_data
from gee_functions.crop import get_crop_loss_data
from ui_components.legends import get_sar_legend


def render_sar_tab(aoi_json, params):
    """Render the SAR inundation tab."""
    f_start = params['f_start']
    f_end = params['f_end']
    p_start = params['p_start']
    p_end = params['p_end']
    f_threshold = params['f_threshold']
    polarization = params['polarization']
    apply_speckle = params['apply_speckle']
    aoi = params['aoi']
    map_center = params['map_center']
    crop_type = params['crop_type']
    crop_price = params['crop_price']

    with st.spinner(f'Querying Sentinel-1 {polarization} SAR archive...'):
        sar = get_all_sar_data(aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
    st.session_state.area_ha = sar['area_ha']
    st.session_state.pop_exposed = f"{sar['pop_exposed']:,}"

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">INUNDATED AREA</div>
            <div class="metric-value">{sar['area_ha']}</div><div class="metric-sub">Hectares · post-event SAR</div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="metric-card"><div class="metric-label">POPULATION EXPOSED</div>
            <div class="metric-value" style="font-size:1.8rem;">{sar['pop_exposed']:,}</div><div class="metric-sub">WorldPop 2020 · 100m</div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""<div class="metric-card"><div class="metric-label">THRESHOLD · POLAR.</div>
            <div class="metric-value" style="font-size:1.6rem;">{f_threshold} dB</div><div class="metric-sub">{polarization} · {'Speckle filtered' if apply_speckle else 'Raw'}</div></div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        sar_view = st.radio("Map Layer", ("Flood Mask", "Severity Zones", "Flood Depth", "Pre-flood SAR", "Post-flood SAR", "Change Intensity", "NDVI Damage"), label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        show_infra = st.checkbox("Show Infrastructure (OSM)", value=False)
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("DOWNLOAD FLOOD MASK", "#", use_container_width=True)

    with col2:
        m2 = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
        folium.GeoJson(aoi.getInfo(), name='AOI Boundary',
            style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(m2)
        folium.TileLayer(tiles=sar['water_url'], attr='GEE', name='Permanent Water').add_to(m2)
        depth_data = None
        if sar_view == "Severity Zones":
            folium.TileLayer(tiles=sar['severity_url'], attr='GEE', name='Flood Severity').add_to(m2)
        elif sar_view == "Pre-flood SAR":
            folium.TileLayer(tiles=sar['pre_url'], attr='GEE', name=f'Pre-flood {polarization} (dB)').add_to(m2)
        elif sar_view == "Post-flood SAR":
            folium.TileLayer(tiles=sar['post_url'], attr='GEE', name=f'Post-flood {polarization} (dB)').add_to(m2)
        elif sar_view == "Change Intensity":
            folium.TileLayer(tiles=sar['diff_url'], attr='GEE', name='Backscatter Δ (dB)').add_to(m2)
        elif sar_view == "Flood Depth":
            with st.spinner("Estimating flood depth..."):
                depth_data = get_flood_depth_tile(aoi_json, str(f_start), str(f_end), str(p_start), str(p_end), f_threshold, polarization, apply_speckle)
            if depth_data:
                folium.TileLayer(tiles=depth_data['tile_url'], attr='GEE·SRTM', name='Flood Depth (m)').add_to(m2)
        elif sar_view == "NDVI Damage":
            with st.spinner("Computing NDVI damage..."):
                ndvi_tile = get_ndvi_tile(aoi_json, str(p_start), str(p_end), str(f_start), str(f_end))
            if ndvi_tile:
                folium.TileLayer(tiles=ndvi_tile, attr='GEE·ESA', name='NDVI Damage (pre−post)').add_to(m2)
            else:
                st.warning("NDVI Damage unavailable — no cloud-free Sentinel-2 scenes for the selected dates.")
        else:
            folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Active Flood').add_to(m2)
        if show_infra:
            with st.spinner("Fetching OSM infrastructure..."):
                infra_data = get_osm_infrastructure(aoi_json)
            icon_map = {'hospital': ('red', '🏥'), 'school': ('blue', '🏫'), 'fire_station': ('orange', '🚒'), 'police': ('purple', '🚓')}
            for feat in infra_data:
                color, icon_emoji = icon_map.get(feat['type'], ('gray', '📍'))
                folium.CircleMarker(location=[feat['lat'], feat['lon']], radius=7, color=color, fill=True, fill_color=color, fill_opacity=0.7, tooltip=f"{icon_emoji} {feat['name']} ({feat['type']})").add_to(m2)
            if infra_data:
                st.markdown(f"""<div class="infra-legend">
                    <span class="infra-chip"><span style="color:red">●</span>Hospital ({sum(1 for f in infra_data if f['type']=='hospital')})</span>
                    <span class="infra-chip"><span style="color:blue">●</span>School ({sum(1 for f in infra_data if f['type']=='school')})</span>
                    <span class="infra-chip"><span style="color:orange">●</span>Fire Stn ({sum(1 for f in infra_data if f['type']=='fire_station')})</span>
                    <span class="infra-chip"><span style="color:purple">●</span>Police ({sum(1 for f in infra_data if f['type']=='police')})</span>
                </div>""", unsafe_allow_html=True)
        Fullscreen(position='topright', force_separate_button=True).add_to(m2)
        MiniMap(tile_layer='CartoDB dark_matter', position='bottomright', toggle_display=True, zoom_level_offset=-6).add_to(m2)
        folium.LayerControl(position='topright', collapsed=False).add_to(m2)
        m2.get_root().html.add_child(folium.Element(get_sar_legend(m2.get_name())))
        folium_static(m2, height=560)
        if sar_view == "Flood Depth" and depth_data:
            volume_Mm3 = round(sar['area_ha'] * 10000 * depth_data['mean_depth'] / 1e6, 3)
            dm1, dm2_col, dm3, dm4 = st.columns(4)
            dm1.metric("Mean Flood Depth", f"{depth_data['mean_depth']} m")
            dm2_col.metric("Max Flood Depth", f"{depth_data['max_depth']} m")
            dm3.metric("Flood Volume", f"{volume_Mm3} M m³")
            dm4.metric("Depth Scale", "0 – 4 m")
            if depth_data.get('histogram'):
                hist = depth_data['histogram']
                st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:10px 0 4px;">FLOOD DEPTH DISTRIBUTION · PIXEL COUNT PER DEPTH BAND</div>', unsafe_allow_html=True)
                hist_df = pd.DataFrame({'Depth Band (m)': list(hist.keys()), 'Pixels': list(hist.values())}).set_index('Depth Band (m)')
                st.bar_chart(hist_df, color="#fd8d3c", height=180)

    with st.expander("CHIRPS RAINFALL TIME SERIES", expanded=False):
        with st.spinner("Fetching CHIRPS daily rainfall..."):
            rain_df = get_chirps_series(aoi_json, str(p_start), str(f_end))
        if rain_df is not None and not rain_df.empty:
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;color:rgba(0,255,255,0.5);letter-spacing:2px;margin-bottom:8px;">MEAN DAILY RAINFALL (mm) · AOI AVERAGE</div>', unsafe_allow_html=True)
            st.area_chart(rain_df, color="#00FFFF", height=200)
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("Total Rainfall", f"{rain_df['rainfall_mm'].sum():.1f} mm")
            col_r2.metric("Peak Daily", f"{rain_df['rainfall_mm'].max():.1f} mm")
            col_r3.metric("Rainy Days", f"{(rain_df['rainfall_mm'] > 1).sum()}")
        else:
            st.info("No CHIRPS data available for the selected date range.")

    with st.expander("FLOOD RETURN PERIOD ANALYSIS  [Gumbel Distribution]", expanded=False):
        with st.spinner("Computing 24-year monsoon rainfall statistics..."):
            rp_data = get_return_period(aoi_json)
        st.session_state.rp_data = rp_data
        if rp_data:
            col_rp1, col_rp2, col_rp3 = st.columns(3)
            col_rp1.metric("Mean Monsoon Rain", f"{rp_data['mean']:.0f} mm")
            col_rp2.metric("Std Deviation", f"± {rp_data['std']:.0f} mm")
            col_rp3.metric("Max Observed", f"{rp_data['max_obs']:.0f} mm")
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:12px 0 6px;">RETURN PERIOD TABLE · MONSOON TOTAL (Jun–Oct)</div>', unsafe_allow_html=True)
            max_rp = max(rp_data['return_periods'].values())
            rows_html = ''
            for T, val in rp_data['return_periods'].items():
                bar_w = int(80 * val / max_rp)
                rows_html += f'<tr><td>{T}-yr</td><td class="rp-val">{val:.0f} mm</td><td><span class="rp-bar" style="width:{bar_w}px;"></span></td></tr>'
            st.markdown(f'<table class="rp-table"><tr><th>RETURN PERIOD</th><th>RAINFALL</th><th>RELATIVE</th></tr>{rows_html}</table>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:0.7rem;color:#3a5060;font-family:JetBrains Mono,monospace;margin-top:10px;">Based on {rp_data["n_years"]} years CHIRPS · Gumbel extreme value distribution</div>', unsafe_allow_html=True)
        else:
            st.warning("Return period calculation failed. Check GEE connectivity.")

    with st.expander("CROP LOSS ASSESSMENT  [NDVI × WorldCover Cropland]", expanded=False):
        with st.spinner("Analysing cropland damage..."):
            crop_data = get_crop_loss_data(aoi_json, str(p_start), str(p_end), str(f_start), str(f_end), crop_price)
        if crop_data:
            cl1, cl2, cl3, cl4 = st.columns(4)
            cl1.metric("Total Cropland", f"{crop_data['total_crop_ha']:,.0f} ha")
            cl2.metric("Damaged Area", f"{crop_data['damaged_ha']:,.0f} ha")
            cl3.metric("Damage %", f"{crop_data['damage_pct']:.1f} %")
            cl4.metric("Est. Crop Loss", f"₹ {crop_data['loss_estimate']:,}")
            st.markdown('<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;color:rgba(0,255,255,0.4);letter-spacing:2px;margin:10px 0 4px;">NDVI DAMAGE ON CROPLAND · GREEN = HEALTHY · RED = DAMAGED</div>', unsafe_allow_html=True)
            crop_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.TileLayer(tiles=crop_data['tile_url'], attr='GEE·S2·ESA', name='Crop NDVI Damage').add_to(crop_map)
            folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(crop_map)
            folium_static(crop_map, height=400)
            st.markdown(f'<div style="font-size:0.7rem;color:#3a5060;font-family:JetBrains Mono,monospace;margin-top:8px;">Crop: {crop_type} · Price: ₹{crop_price:,}/ha · NDVI drop threshold: 0.10 · Source: Sentinel-2 SR + ESA WorldCover</div>', unsafe_allow_html=True)
        else:
            st.warning("Crop loss analysis unavailable. No Sentinel-2 data or no cropland in AOI.")

    with st.expander("JRC HISTORICAL FLOOD FREQUENCY  [1984 – 2021]", expanded=False):
        with st.spinner("Fetching 38-year JRC Monthly Water History..."):
            jrc_hist = get_jrc_flood_history(aoi_json)
        if jrc_hist:
            jrc_df = pd.DataFrame({'Year': list(jrc_hist.keys()), 'Flood Months': list(jrc_hist.values())}).set_index('Year')
            total_flood_months = sum(jrc_hist.values())
            peak_yr = max(jrc_hist, key=jrc_hist.get)
            avg_months = round(total_flood_months / len(jrc_hist), 1)
            jh1, jh2, jh3 = st.columns(3)
            jh1.metric("Peak Flood Year", str(peak_yr))
            jh2.metric("Avg Flood Months/yr", f"{avg_months} mo")
            jh3.metric("Total Flood Months", f"{total_flood_months}")
            st.bar_chart(jrc_df, color="#2E86C1", height=220)
        else:
            st.warning("JRC flood history unavailable for this AOI.")

    with st.expander("ROAD NETWORK IMPACT  [OSM · Evacuation Routes]", expanded=False):
        with st.spinner("Fetching road network from OSM..."):
            road_data = get_osm_roads(aoi_json)
        if road_data and road_data['roads']:
            hw_colors = {'motorway': '#e74c3c', 'trunk': '#e67e22', 'primary': '#f1c40f', 'secondary': '#2ecc71', 'tertiary': '#3498db', 'road': '#95a5a6'}
            evac_count = sum(1 for r in road_data['roads'] if r['evacuation'])
            rn1, rn2, rn3 = st.columns(3)
            total_km = sum(road_data['km_by_type'].values())
            rn1.metric("Total Road Length", f"{total_km:.1f} km")
            rn2.metric("Road Types", f"{len(road_data['km_by_type'])}")
            rn3.metric("Evacuation Routes", f"{evac_count} segments")
            road_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
            folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Flood Mask', opacity=0.55).add_to(road_map)
            for road in road_data['roads']:
                color = '#00FF88' if road['evacuation'] else hw_colors.get(road['highway'], '#95a5a6')
                weight = 4 if road['evacuation'] else 2
                folium.PolyLine(locations=[[c[1], c[0]] for c in road['coords']], color=color, weight=weight, opacity=0.85, tooltip=f"{road['highway'].title()} · {road['name'] or 'unnamed'} · {road['length_km']} km").add_to(road_map)
            folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(road_map)
            folium_static(road_map, height=420)
            km_df = pd.DataFrame(list(road_data['km_by_type'].items()), columns=['Highway Type', 'Length (km)']).sort_values('Length (km)', ascending=False).set_index('Highway Type')
            st.dataframe(km_df, use_container_width=True)
        else:
            st.warning("No road data available for this AOI.")

    with st.expander("DAMS & RESERVOIRS UPSTREAM  [GRanD v1.3 · 150 km radius]", expanded=False):
        with st.spinner("Querying GRanD dam database..."):
            dam_list = get_dam_data(aoi_json)
        if dam_list:
            dam_map = folium.Map(location=map_center, zoom_start=8, tiles="CartoDB dark_matter")
            folium.TileLayer(tiles=sar['flood_url'], attr='GEE', name='Flood Mask', opacity=0.5).add_to(dam_map)
            folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(dam_map)
            for dam in dam_list:
                cap = dam['capacity_mcm']
                radius = max(6, min(22, int(cap ** 0.35))) if cap > 0 else 7
                folium.CircleMarker(location=[dam['lat'], dam['lon']], radius=radius, color='#00BFFF', fill=True, fill_color='#00BFFF', fill_opacity=0.6,
                    tooltip=f"🏞 {dam['name']} · {dam['river']}<br>Capacity: {int(cap):,} MCM · Use: {dam['main_use']} · Built: {dam['year']}").add_to(dam_map)
            folium_static(dam_map, height=420)
            da1, da2, da3 = st.columns(3)
            da1.metric("Dams Found", f"{len(dam_list)}")
            da2.metric("Total Capacity", f"{sum(d['capacity_mcm'] for d in dam_list):,.0f} MCM")
            da3.metric("Largest Dam", dam_list[0]['name'] if dam_list else "—")
            dam_df = pd.DataFrame([{'Name': d['name'], 'River': d['river'], 'Capacity (MCM)': int(d['capacity_mcm']), 'Use': d['main_use'], 'Built': d['year']} for d in dam_list])
            st.dataframe(dam_df, use_container_width=True, hide_index=True)
        else:
            st.info("No dams found within 150 km of this AOI.")

    with st.expander("FLOOD RECESSION TRACKER  [SAR · +12 / +24 / +36 days]", expanded=False):
        with st.spinner("Computing post-event SAR flood extent (4 × 12-day windows)..."):
            recession = get_recession_data(aoi_json, str(f_end), str(p_start), str(p_end), polarization, f_threshold, apply_speckle)
        if recession:
            valid = [r for r in recession if r['Flood Area (ha)'] is not None]
            if valid:
                rec_df = pd.DataFrame(valid).set_index('Phase')
                peak = rec_df['Flood Area (ha)'].max()
                final = rec_df['Flood Area (ha)'].iloc[-1]
                receded_pct = round(100 * (peak - final) / peak, 1) if peak > 0 else 0
                rv1, rv2, rv3 = st.columns(3)
                rv1.metric("Peak Flood Area", f"{peak:,.0f} ha")
                rv2.metric("Latest Extent", f"{final:,.0f} ha")
                rv3.metric("Area Receded", f"{receded_pct} %")
                st.line_chart(rec_df, color="#FF6B6B", height=200)
            else:
                st.info("No SAR imagery found in post-event windows.")
        else:
            st.warning("Recession analysis failed. Check GEE connectivity.")

    # ── PHASE 2 ANALYTICAL MODULES ─────────────────
    with st.expander("POPULATION DISPLACEMENT  [WorldPop Demographics]", expanded=False):
        if st.button("ESTIMATE DISPLACEMENT", key="pop_disp_btn", use_container_width=True):
            with st.spinner("Querying WorldPop demographic data..."):
                try:
                    from gee_functions.population import get_displacement_estimate
                    pop_data = get_displacement_estimate(aoi_json)
                    if pop_data:
                        pd1, pd2, pd3, pd4 = st.columns(4)
                        pd1.metric("Total Population", f"{pop_data['total_population']:,}")
                        pd2.metric("Displaced Estimate", f"{pop_data['displaced_estimate']:,}")
                        pd3.metric("Children Affected", f"{pop_data['children_affected']:,}")
                        pd4.metric("Elderly Affected", f"{pop_data['elderly_affected']:,}")
                    else:
                        st.warning("Population data unavailable for this AOI.")
                except Exception as e:
                    st.error(f"Population estimate failed: {e}")
        else:
            st.info("Click to estimate population displacement using WorldPop age/sex demographics.")

    with st.expander("BUILDING DAMAGE ASSESSMENT  [Google Open Buildings]", expanded=False):
        if st.button("ASSESS BUILDING DAMAGE", key="bldg_dmg_btn", use_container_width=True):
            with st.spinner("Cross-referencing buildings with flood depth..."):
                try:
                    from gee_functions.buildings import get_building_damage
                    bldg = get_building_damage(aoi_json, f_start, f_end, p_start, p_end, f_threshold, polarization, apply_speckle)
                    if bldg:
                        bd1, bd2, bd3 = st.columns(3)
                        bd1.metric("Total Buildings", f"{bldg['total_buildings']:,}")
                        bd2.metric("Affected", f"{bldg['total_affected']:,}")
                        dc = bldg['damage_counts']
                        bd3.metric("Severe+Destroyed", f"{dc['severe'] + dc['destroyed']:,}")
                        damage_df = pd.DataFrame([
                            {'Category': 'Minor (0-0.5m)', 'Count': dc['minor']},
                            {'Category': 'Moderate (0.5-1.5m)', 'Count': dc['moderate']},
                            {'Category': 'Severe (1.5-3m)', 'Count': dc['severe']},
                            {'Category': 'Destroyed (>3m)', 'Count': dc['destroyed']},
                        ]).set_index('Category')
                        st.bar_chart(damage_df, color="#fc8d59", height=180)
                        bldg_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=bldg['tile_url'], attr='GEE·GOB', name='Building Damage').add_to(bldg_map)
                        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(bldg_map)
                        folium_static(bldg_map, height=380)
                    else:
                        st.warning("No building data found in this AOI (Google Open Buildings).")
                except Exception as e:
                    st.error(f"Building damage assessment failed: {e}")
        else:
            st.info("Click to assess building damage using Google Open Buildings + flood depth.")

    with st.expander("SOIL MOISTURE  [NASA SMAP · 9km]", expanded=False):
        if st.button("LOAD SOIL MOISTURE", key="soil_btn", use_container_width=True):
            with st.spinner("Fetching NASA SMAP soil moisture data..."):
                try:
                    from gee_functions.soil_moisture import get_soil_moisture_data
                    sm = get_soil_moisture_data(aoi_json, str(p_start), str(f_end))
                    if sm:
                        sm1, sm2 = st.columns(2)
                        sm1.metric("Mean Soil Moisture", f"{sm['mean_soil_moisture']:.3f} m³/m³")
                        sm2.metric("Observations", sm['n_observations'])
                        if sm['timeseries'] is not None:
                            st.line_chart(sm['timeseries'], color="#41ab5d", height=200)
                        sm_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=sm['tile_url'], attr='GEE·SMAP', name='Soil Moisture').add_to(sm_map)
                        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(sm_map)
                        folium_static(sm_map, height=380)
                    else:
                        st.warning("SMAP data unavailable for this AOI/date range.")
                except Exception as e:
                    st.error(f"Soil moisture fetch failed: {e}")
        else:
            st.info("Click to view NASA SMAP soil moisture for the analysis period.")

    with st.expander("WATER QUALITY  [Sentinel-2 Turbidity & Chlorophyll]", expanded=False):
        if st.button("ANALYZE WATER QUALITY", key="wq_btn", use_container_width=True):
            with st.spinner("Computing water quality indices from Sentinel-2..."):
                try:
                    from gee_functions.water_quality import get_turbidity_map
                    wq = get_turbidity_map(aoi_json, str(f_start), str(f_end))
                    if wq:
                        wq1, wq2, wq3 = st.columns(3)
                        wq1.metric("Turbidity (NDTI)", f"{wq['mean_ndti']:.4f}")
                        wq2.metric("Level", wq['turbidity_level'])
                        wq3.metric("Chl-a Ratio", f"{wq['mean_chl_ratio']:.3f}")
                        wq_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                        folium.TileLayer(tiles=wq['ndti_tile'], attr='GEE·S2', name='Turbidity (NDTI)').add_to(wq_map)
                        folium.TileLayer(tiles=wq['chl_tile'], attr='GEE·S2', name='Chlorophyll-a').add_to(wq_map)
                        folium.GeoJson(aoi.getInfo(), style_function=lambda _: {'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'}).add_to(wq_map)
                        folium.LayerControl(position='topright', collapsed=False).add_to(wq_map)
                        folium_static(wq_map, height=380)
                    else:
                        st.warning("Water quality analysis unavailable — no cloud-free Sentinel-2 scenes.")
                except Exception as e:
                    st.error(f"Water quality analysis failed: {e}")
        else:
            st.info("Click to analyze turbidity and chlorophyll from Sentinel-2.")
