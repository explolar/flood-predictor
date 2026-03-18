"""Tab: Climate Projections — ERA5 historical + CMIP6 future scenarios + future risk maps."""

import json

import folium
import streamlit as st
from streamlit_folium import folium_static

from gee_functions.cmip6 import (
    AVAILABLE_MODELS,
    AVAILABLE_SCENARIOS,
    get_cmip6_precip_change,
    get_cmip6_projections,
    get_cmip6_scenario_comparison,
)
from gee_functions.era5 import get_era5_climate_summary, get_era5_monsoon_profile
from ml_models.flood_risk_model import FloodRiskPredictor


def render_projections_tab(aoi_json, params):
    """Render the climate projections sub-tab."""
    map_center = params['map_center']

    st.markdown(
        '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
        'letter-spacing:2px;color:rgba(144,202,249,0.4);margin-bottom:8px;">'
        'CLIMATE PROJECTIONS · ERA5-LAND · CMIP6 · SSP SCENARIOS</div>',
        unsafe_allow_html=True,
    )

    # ── ERA5 HISTORICAL CLIMATE ─────────────────────
    with st.expander("ERA5-LAND HISTORICAL CLIMATE", expanded=True):
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
            'ECMWF · ~11 KM · TEMPERATURE · RUNOFF · SOIL MOISTURE · ET</div>',
            unsafe_allow_html=True,
        )
        era5_year = st.selectbox(
            "Year", list(range(2024, 1999, -1)), index=0, key="era5_year"
        )

        if st.button("COMPUTE ERA5 CLIMATE SUMMARY", key="era5_btn", use_container_width=True):
            with st.spinner(f"Fetching ERA5-Land data for {era5_year}..."):
                try:
                    result = get_era5_climate_summary(aoi_json, year=era5_year)
                    if result:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Temperature", f"{result['temperature_c']} °C")
                        c2.metric("Precipitation", f"{result['total_precip_mm']:.0f} mm")
                        c3.metric("Surface Runoff", f"{result['total_runoff_mm']:.0f} mm")
                        c4.metric("Soil Moisture", f"{result['mean_soil_moisture']:.3f} m³/m³")

                        ec1, ec2 = st.columns(2)
                        ec1.metric("Evapotranspiration", f"{result['total_et_mm']:.0f} mm")

                        m = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB dark_matter")
                        folium.TileLayer(
                            tiles=result['tile_url'], attr='GEE·ERA5',
                            name='Surface Runoff (mm)', opacity=0.8,
                        ).add_to(m)
                        folium.GeoJson(
                            json.loads(aoi_json),
                            style_function=lambda _: {
                                'fillColor': 'none', 'color': '#00FFFF',
                                'weight': 2, 'dashArray': '6 4',
                            },
                        ).add_to(m)
                        folium.LayerControl(position='topright', collapsed=False).add_to(m)
                        folium_static(m, height=400)
                    else:
                        st.warning("No ERA5 data available for this year/region.")
                except Exception as e:
                    st.error(f"ERA5 computation failed: {e}")
        else:
            st.info("Click to compute ERA5-Land annual climate summary for the selected year.")

        # Monsoon profile sub-section
        if st.button("MONSOON PROFILE (JUN-OCT)", key="era5_monsoon_btn", use_container_width=True):
            with st.spinner(f"Computing monsoon profile for {era5_year}..."):
                try:
                    monsoon = get_era5_monsoon_profile(aoi_json, year=era5_year)
                    if monsoon:
                        df = monsoon['monthly_data']
                        month_names = {6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct'}
                        df['month_name'] = df['month'].map(month_names)
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:rgba(144,202,249,0.4);'
                            'letter-spacing:2px;margin:12px 0 6px 0;">'
                            'MONTHLY MONSOON BREAKDOWN</div>',
                            unsafe_allow_html=True,
                        )
                        st.bar_chart(
                            df.set_index('month_name')[['precip_mm', 'runoff_mm', 'et_mm']],
                            height=280,
                        )
                        st.dataframe(df[['month_name', 'precip_mm', 'runoff_mm', 'soil_moisture', 'et_mm']],
                                     hide_index=True, use_container_width=True)
                    else:
                        st.warning("No monsoon data available.")
                except Exception as e:
                    st.error(f"Monsoon profile failed: {e}")

    # ── CMIP6 FUTURE PROJECTIONS ────────────────────
    with st.expander("CMIP6 FUTURE PROJECTIONS", expanded=False):
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
            'NASA NEX-GDDP · ~25 KM · SSP245 / SSP585 · MULTI-MODEL</div>',
            unsafe_allow_html=True,
        )

        pc1, pc2 = st.columns(2)
        with pc1:
            cmip_scenario = st.selectbox("SSP Scenario", AVAILABLE_SCENARIOS,
                                          format_func=lambda s: s.upper(), key="cmip_ssp")
        with pc2:
            cmip_model = st.selectbox("Climate Model", AVAILABLE_MODELS, key="cmip_model")

        sc1, sc2 = st.columns(2)
        with sc1:
            cmip_start = st.number_input("Start Year", min_value=2025, max_value=2090,
                                          value=2030, step=5, key="cmip_start")
        with sc2:
            cmip_end = st.number_input("End Year", min_value=2030, max_value=2100,
                                        value=2050, step=5, key="cmip_end")

        if st.button("RUN PROJECTIONS", key="cmip_proj_btn", use_container_width=True):
            with st.spinner(f"Running {cmip_scenario.upper()} projections ({cmip_model})..."):
                try:
                    proj = get_cmip6_projections(
                        aoi_json, scenario=cmip_scenario, model=cmip_model,
                        start_year=cmip_start, end_year=cmip_end,
                    )
                    if proj:
                        mc1, mc2, mc3 = st.columns(3)
                        mc1.metric("Precipitation", f"{proj['mean_precip_mm_yr']:.0f} mm/yr")
                        mc2.metric("Max Temp", f"{proj['mean_tasmax_c']:.1f} °C")
                        mc3.metric("Min Temp", f"{proj['mean_tasmin_c']:.1f} °C")

                        col_l, col_r = st.columns(2)
                        with col_l:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                                'PRECIPITATION</div>',
                                unsafe_allow_html=True,
                            )
                            pm = folium.Map(location=map_center, zoom_start=9,
                                            tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=proj['precip_tile_url'], attr='GEE·CMIP6',
                                name='Precipitation', opacity=0.8,
                            ).add_to(pm)
                            folium.GeoJson(
                                json.loads(aoi_json),
                                style_function=lambda _: {
                                    'fillColor': 'none', 'color': '#00FFFF',
                                    'weight': 2, 'dashArray': '6 4',
                                },
                            ).add_to(pm)
                            folium_static(pm, height=350)

                        with col_r:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                                'MAX TEMPERATURE</div>',
                                unsafe_allow_html=True,
                            )
                            tm = folium.Map(location=map_center, zoom_start=9,
                                            tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=proj['temp_tile_url'], attr='GEE·CMIP6',
                                name='Temperature', opacity=0.8,
                            ).add_to(tm)
                            folium.GeoJson(
                                json.loads(aoi_json),
                                style_function=lambda _: {
                                    'fillColor': 'none', 'color': '#00FFFF',
                                    'weight': 2, 'dashArray': '6 4',
                                },
                            ).add_to(tm)
                            folium_static(tm, height=350)
                    else:
                        st.warning("No CMIP6 data available for this combination.")
                except Exception as e:
                    st.error(f"CMIP6 projection failed: {e}")
        else:
            st.info("Select scenario, model, and period, then click to run future climate projections.")

    # ── SCENARIO COMPARISON ─────────────────────────
    with st.expander("SSP SCENARIO COMPARISON", expanded=False):
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
            'SSP245 vs SSP585 · THREE TIME HORIZONS · PRECIPITATION CHANGE</div>',
            unsafe_allow_html=True,
        )

        comp_model = st.selectbox("Model for Comparison", AVAILABLE_MODELS, key="comp_model")

        if st.button("COMPARE SSP SCENARIOS", key="cmip_comp_btn", use_container_width=True):
            with st.spinner(f"Comparing scenarios across time periods ({comp_model})..."):
                try:
                    comp = get_cmip6_scenario_comparison(aoi_json, model=comp_model)
                    if comp:
                        df = comp['comparison_df']
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:8px 0 4px 0;">'
                            'PRECIPITATION PROJECTIONS BY SCENARIO</div>',
                            unsafe_allow_html=True,
                        )
                        st.dataframe(df, hide_index=True, use_container_width=True)

                        # Pivot for chart
                        pivot = df.pivot(index='period', columns='scenario', values='precip_mm_yr')
                        st.bar_chart(pivot, height=280)

                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:12px 0 4px 0;">'
                            'TEMPERATURE PROJECTIONS BY SCENARIO</div>',
                            unsafe_allow_html=True,
                        )
                        pivot_t = df.pivot(index='period', columns='scenario', values='tasmax_c')
                        st.bar_chart(pivot_t, height=280)
                    else:
                        st.warning("No comparison data available.")
                except Exception as e:
                    st.error(f"Scenario comparison failed: {e}")

        # Precipitation change map
        if st.button("PRECIPITATION CHANGE MAP", key="cmip_change_btn", use_container_width=True):
            with st.spinner("Computing precipitation change relative to baseline..."):
                try:
                    change = get_cmip6_precip_change(aoi_json, model=comp_model)
                    if change:
                        ch1, ch2, ch3 = st.columns(3)
                        ch1.metric("Baseline (2015-2025)", f"{change['baseline_precip_mm']:.0f} mm/yr")
                        ch2.metric(f"Future ({change['future_period']})",
                                   f"{change['future_precip_mm']:.0f} mm/yr")
                        delta_color = "normal" if change['pct_change'] >= 0 else "inverse"
                        ch3.metric("Change", f"{change['pct_change']:+.1f}%",
                                   delta=f"{change['pct_change']:+.1f}%",
                                   delta_color=delta_color)

                        cm = folium.Map(location=map_center, zoom_start=9,
                                        tiles="CartoDB dark_matter")
                        folium.TileLayer(
                            tiles=change['change_tile_url'], attr='GEE·CMIP6',
                            name='Precip Change %', opacity=0.8,
                        ).add_to(cm)
                        folium.GeoJson(
                            json.loads(aoi_json),
                            style_function=lambda _: {
                                'fillColor': 'none', 'color': '#00FFFF',
                                'weight': 2, 'dashArray': '6 4',
                            },
                        ).add_to(cm)
                        folium.LayerControl(position='topright', collapsed=False).add_to(cm)
                        folium_static(cm, height=400)
                    else:
                        st.warning("No change data available.")
                except Exception as e:
                    st.error(f"Precipitation change computation failed: {e}")

    # ── FUTURE FLOOD RISK MAP ───────────────────────
    with st.expander("FUTURE FLOOD RISK MAP", expanded=False):
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
            'ML RISK PREDICTION · CMIP6 PROJECTED RAINFALL · CURRENT vs FUTURE</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
            'color:#90CAF9;margin-bottom:12px;">'
            'Predicts flood risk classes (1-5) using the trained Random Forest model '
            'with CMIP6 projected precipitation replacing current CHIRPS rainfall. '
            'Terrain, land cover, and water history layers remain unchanged.</div>',
            unsafe_allow_html=True,
        )

        fr1, fr2 = st.columns(2)
        with fr1:
            risk_scenario = st.selectbox("SSP Scenario", AVAILABLE_SCENARIOS,
                                          format_func=lambda s: s.upper(), key="risk_ssp")
        with fr2:
            risk_model = st.selectbox("Climate Model", AVAILABLE_MODELS, key="risk_gcm")

        fr3, fr4 = st.columns(2)
        with fr3:
            risk_start = st.number_input("Start Year", min_value=2025, max_value=2090,
                                          value=2040, step=5, key="risk_start")
        with fr4:
            risk_end = st.number_input("End Year", min_value=2030, max_value=2100,
                                        value=2060, step=5, key="risk_end")

        if st.button("GENERATE FUTURE RISK MAP", key="future_risk_btn", use_container_width=True):
            with st.spinner("Training model on current data & projecting future risk..."):
                try:
                    predictor = FloodRiskPredictor(include_era5=False)

                    # Current risk (for comparison)
                    current = predictor.predict_for_aoi(aoi_json)

                    # Future risk with CMIP6 rainfall
                    future = predictor.predict_future_risk(
                        aoi_json, scenario=risk_scenario, model=risk_model,
                        start_year=risk_start, end_year=risk_end,
                    )

                    if current and future:
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:12px 0 6px 0;">'
                            'CURRENT vs PROJECTED FLOOD RISK</div>',
                            unsafe_allow_html=True,
                        )

                        # Metrics row
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Scenario", risk_scenario.upper())
                        m2.metric("Period", future['period'])
                        m3.metric("Samples", f"{future['n_samples']:,}")

                        # Side-by-side maps
                        map_l, map_r = st.columns(2)

                        _aoi_geojson = json.loads(aoi_json)

                        def _aoi_style(_):
                            return {
                                'fillColor': 'none', 'color': '#00FFFF',
                                'weight': 2, 'dashArray': '6 4',
                            }

                        with map_l:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                                'CURRENT RISK (CHIRPS 2023)</div>',
                                unsafe_allow_html=True,
                            )
                            cm_now = folium.Map(location=map_center, zoom_start=10,
                                                tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=current['tile_url'], attr='GEE·RF',
                                name='Current Risk', opacity=0.85,
                            ).add_to(cm_now)
                            folium.GeoJson(_aoi_geojson, style_function=_aoi_style).add_to(cm_now)
                            folium_static(cm_now, height=380)

                        with map_r:
                            st.markdown(
                                f'<div style="font-family:JetBrains Mono,monospace;'
                                f'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                                f'PROJECTED RISK ({risk_scenario.upper()} {future["period"]})</div>',
                                unsafe_allow_html=True,
                            )
                            cm_fut = folium.Map(location=map_center, zoom_start=10,
                                                tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=future['tile_url'], attr='GEE·RF·CMIP6',
                                name='Future Risk', opacity=0.85,
                            ).add_to(cm_fut)
                            folium.GeoJson(_aoi_geojson, style_function=_aoi_style).add_to(cm_fut)
                            folium_static(cm_fut, height=380)

                        # Risk class distribution comparison
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:16px 0 6px 0;">'
                            'RISK CLASS DISTRIBUTION</div>',
                            unsafe_allow_html=True,
                        )
                        _risk_labels = {1: 'Very Low', 2: 'Low', 3: 'Moderate', 4: 'High', 5: 'Very High'}
                        current_dist = current.get('risk_distribution') or {}
                        future_dist = future.get('risk_distribution', {})

                        # Build comparison table
                        dist_rows = []
                        for cls in range(1, 6):
                            c_count = current_dist.get(cls, 0)
                            f_count = future_dist.get(cls, 0)
                            c_n = current.get('n_samples', 1)
                            f_n = future.get('n_samples', 1)
                            dist_rows.append({
                                'Class': f"{cls} - {_risk_labels[cls]}",
                                'Current %': round(c_count / c_n * 100, 1) if c_n else 0,
                                'Future %': round(f_count / f_n * 100, 1) if f_n else 0,
                            })

                        import pandas as pd
                        dist_df = pd.DataFrame(dist_rows)
                        dist_df['Change (pp)'] = dist_df['Future %'] - dist_df['Current %']
                        st.dataframe(dist_df, hide_index=True, use_container_width=True)

                        # Bar chart
                        chart_df = dist_df.set_index('Class')[['Current %', 'Future %']]
                        st.bar_chart(chart_df, height=280)

                        # Legend
                        st.markdown(
                            '<div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">'
                            '<div style="display:flex;align-items:center;gap:4px;">'
                            '<div style="width:12px;height:12px;background:#1a9850;border-radius:2px;"></div>'
                            '<span style="font-size:0.7rem;color:#90CAF9;">1 Very Low</span></div>'
                            '<div style="display:flex;align-items:center;gap:4px;">'
                            '<div style="width:12px;height:12px;background:#91cf60;border-radius:2px;"></div>'
                            '<span style="font-size:0.7rem;color:#90CAF9;">2 Low</span></div>'
                            '<div style="display:flex;align-items:center;gap:4px;">'
                            '<div style="width:12px;height:12px;background:#ffffbf;border-radius:2px;"></div>'
                            '<span style="font-size:0.7rem;color:#90CAF9;">3 Moderate</span></div>'
                            '<div style="display:flex;align-items:center;gap:4px;">'
                            '<div style="width:12px;height:12px;background:#fc8d59;border-radius:2px;"></div>'
                            '<span style="font-size:0.7rem;color:#90CAF9;">4 High</span></div>'
                            '<div style="display:flex;align-items:center;gap:4px;">'
                            '<div style="width:12px;height:12px;background:#d73027;border-radius:2px;"></div>'
                            '<span style="font-size:0.7rem;color:#90CAF9;">5 Very High</span></div>'
                            '</div>',
                            unsafe_allow_html=True,
                        )

                    elif current and not future:
                        st.warning("CMIP6 data not available for this scenario/model/period. "
                                   "Current risk map was generated but future projection failed.")
                    else:
                        st.error("Could not generate risk predictions. "
                                 "Ensure the AOI has sufficient data coverage.")
                except Exception as e:
                    st.error(f"Future risk mapping failed: {e}")
        else:
            st.info(
                "Select a climate scenario, model, and future period, then click to generate "
                "side-by-side current vs. projected flood risk maps."
            )

    # ── MULTI-MODEL ENSEMBLE + RISK DELTA ───────────
    with st.expander("MULTI-MODEL ENSEMBLE + RISK CHANGE", expanded=False):
        st.markdown(
            '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
            'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
            'ENSEMBLE MAJORITY VOTE · MULTIPLE GCMs · SPATIAL RISK DELTA</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-family:\'Inter\',sans-serif;font-size:0.78rem;'
            'color:#90CAF9;margin-bottom:12px;">'
            'Runs flood risk prediction across multiple CMIP6 climate models and '
            'combines results via majority vote. The risk delta map shows where '
            'flood risk increases (red) or decreases (green) compared to current conditions.</div>',
            unsafe_allow_html=True,
        )

        e1, e2 = st.columns(2)
        with e1:
            ens_scenario = st.selectbox("SSP Scenario", AVAILABLE_SCENARIOS,
                                         format_func=lambda s: s.upper(), key="ens_ssp")
        with e2:
            ens_n_models = st.selectbox("Number of GCMs", [2, 3, 4, 6], index=2, key="ens_n")

        e3, e4 = st.columns(2)
        with e3:
            ens_start = st.number_input("Start Year", min_value=2025, max_value=2090,
                                         value=2040, step=5, key="ens_start")
        with e4:
            ens_end = st.number_input("End Year", min_value=2030, max_value=2100,
                                       value=2060, step=5, key="ens_end")

        if st.button("RUN ENSEMBLE PROJECTION", key="ens_btn", use_container_width=True):
            with st.spinner(f"Running {ens_n_models}-model ensemble ({ens_scenario.upper()})..."):
                try:
                    predictor = FloodRiskPredictor(include_era5=False)
                    result = predictor.predict_future_risk_ensemble(
                        aoi_json, scenario=ens_scenario,
                        models=AVAILABLE_MODELS[:ens_n_models],
                        start_year=ens_start, end_year=ens_end,
                    )

                    if result:
                        # Summary metrics
                        em1, em2, em3, em4 = st.columns(4)
                        em1.metric("GCMs Used", result['n_models'])
                        em2.metric("Scenario", result['scenario'].upper())
                        em3.metric("Period", result['period'])
                        delta_str = f"{result['mean_risk_delta']:+.2f}"
                        em4.metric("Mean Risk Change", delta_str,
                                   delta=delta_str,
                                   delta_color="inverse" if result['mean_risk_delta'] > 0 else "normal")

                        st.markdown(
                            f'<div style="font-family:JetBrains Mono,monospace;'
                            f'font-size:0.6rem;color:rgba(144,202,249,0.4);margin:8px 0 4px 0;">'
                            f'MODELS: {", ".join(result["models_used"])}</div>',
                            unsafe_allow_html=True,
                        )

                        # Three maps: current / ensemble future / delta
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:12px 0 6px 0;">'
                            'CURRENT · ENSEMBLE FUTURE · RISK CHANGE</div>',
                            unsafe_allow_html=True,
                        )

                        _aoi_gj = json.loads(aoi_json)

                        def _style_aoi(_):
                            return {
                                'fillColor': 'none', 'color': '#00FFFF',
                                'weight': 2, 'dashArray': '6 4',
                            }

                        col_a, col_b, col_c = st.columns(3)

                        with col_a:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.55rem;color:#64B5F6;margin-bottom:4px;">'
                                'CURRENT</div>',
                                unsafe_allow_html=True,
                            )
                            m1 = folium.Map(location=map_center, zoom_start=10,
                                            tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=result['current_tile_url'], attr='GEE·RF',
                                name='Current Risk', opacity=0.85,
                            ).add_to(m1)
                            folium.GeoJson(_aoi_gj, style_function=_style_aoi).add_to(m1)
                            folium_static(m1, height=340)

                        with col_b:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.55rem;color:#64B5F6;margin-bottom:4px;">'
                                'ENSEMBLE FUTURE</div>',
                                unsafe_allow_html=True,
                            )
                            m2 = folium.Map(location=map_center, zoom_start=10,
                                            tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=result['ensemble_tile_url'], attr='GEE·RF·ENS',
                                name='Ensemble Risk', opacity=0.85,
                            ).add_to(m2)
                            folium.GeoJson(_aoi_gj, style_function=_style_aoi).add_to(m2)
                            folium_static(m2, height=340)

                        with col_c:
                            st.markdown(
                                '<div style="font-family:JetBrains Mono,monospace;'
                                'font-size:0.55rem;color:#64B5F6;margin-bottom:4px;">'
                                'RISK DELTA</div>',
                                unsafe_allow_html=True,
                            )
                            m3 = folium.Map(location=map_center, zoom_start=10,
                                            tiles="CartoDB dark_matter")
                            folium.TileLayer(
                                tiles=result['delta_tile_url'], attr='GEE·DELTA',
                                name='Risk Change', opacity=0.85,
                            ).add_to(m3)
                            folium.GeoJson(_aoi_gj, style_function=_style_aoi).add_to(m3)
                            folium_static(m3, height=340)

                        # Delta legend
                        st.markdown(
                            '<div style="display:flex;gap:8px;margin:8px 0;flex-wrap:wrap;'
                            'justify-content:center;">'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#1a9850;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">-3 Much Lower</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#91cf60;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">-2</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#d9ef8b;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">-1</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#f7f7f7;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">0 No Change</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#fee08b;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">+1</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#fc8d59;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">+2</span></div>'
                            '<div style="display:flex;align-items:center;gap:3px;">'
                            '<div style="width:10px;height:10px;background:#d73027;border-radius:2px;"></div>'
                            '<span style="font-size:0.65rem;color:#90CAF9;">+3 Much Higher</span></div>'
                            '</div>',
                            unsafe_allow_html=True,
                        )

                        # Distribution comparison table
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:16px 0 6px 0;">'
                            'ENSEMBLE RISK DISTRIBUTION</div>',
                            unsafe_allow_html=True,
                        )
                        _rl = {1: 'Very Low', 2: 'Low', 3: 'Moderate', 4: 'High', 5: 'Very High'}
                        c_dist = result['current_distribution']
                        e_dist = result['ensemble_distribution']
                        n_s = result['n_samples'] or 1
                        rows = []
                        for cls in range(1, 6):
                            c_pct = round(c_dist.get(cls, 0) / n_s * 100, 1)
                            e_pct = round(e_dist.get(cls, 0) / n_s * 100, 1)
                            rows.append({
                                'Class': f"{cls} - {_rl[cls]}",
                                'Current %': c_pct,
                                'Ensemble %': e_pct,
                                'Change (pp)': round(e_pct - c_pct, 1),
                            })

                        import pandas as pd
                        d_df = pd.DataFrame(rows)
                        st.dataframe(d_df, hide_index=True, use_container_width=True)

                        chart = d_df.set_index('Class')[['Current %', 'Ensemble %']]
                        st.bar_chart(chart, height=260)

                        # Per-model breakdown
                        with st.expander("PER-MODEL BREAKDOWN", expanded=False):
                            pm_dist = result['per_model_distribution']
                            pm_rows = []
                            for gcm, dist in pm_dist.items():
                                total = sum(dist.values()) or 1
                                pm_rows.append({
                                    'Model': gcm,
                                    **{f"Class {c}%": round(dist.get(c, 0) / total * 100, 1)
                                       for c in range(1, 6)},
                                })
                            st.dataframe(pd.DataFrame(pm_rows), hide_index=True,
                                         use_container_width=True)

                    else:
                        st.warning("Ensemble projection failed. Check CMIP6 data availability "
                                   "for the selected scenario and period.")
                except Exception as e:
                    st.error(f"Ensemble projection failed: {e}")
        else:
            st.info(
                "Runs the RF model across multiple CMIP6 climate models and combines "
                "via majority vote for robust future risk estimation."
            )
