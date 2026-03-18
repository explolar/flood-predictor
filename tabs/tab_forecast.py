"""Tab: Weather Forecast + Flood Forecasting + GloFAS + Foundation Models."""

import json

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import folium_static

from gee_functions.gfs_forecast import get_gfs_flood_alert, get_gfs_forecast


def render_forecast_tab(aoi_json, params):
    """Render the FORECAST tab with Weather / Flood / GloFAS / AI Models sub-tabs."""
    st.markdown(
        "<div style=\"font-family:'Inter',sans-serif;font-size:0.78rem;"
        'letter-spacing:2px;color:rgba(144,202,249,0.4);margin-bottom:8px;">'
        "GFS · LSTM · GloFAS · PRITHVI · CLAY · ClimaX</div>",
        unsafe_allow_html=True,
    )

    fc_sub1, fc_sub2, fc_sub3, fc_sub4 = st.tabs(
        ["  WEATHER  ", "  FLOOD FORECAST  ", "  RIVER DISCHARGE  ", "  AI MODELS  "]
    )
    with fc_sub1:
        _render_weather(aoi_json, params)
    with fc_sub2:
        _render_flood_forecast(aoi_json, params)
    with fc_sub3:
        _render_glofas(aoi_json, params)
    with fc_sub4:
        _render_foundation_models(aoi_json, params)


# ── Sub-tab 1: Weather Forecast ──────────────────────────────


def _render_weather(aoi_json, params):
    """GFS 7-16 day weather forecast."""
    map_center = params["map_center"]

    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
        "NOAA GFS 0.25° · PRECIPITATION · TEMPERATURE · WIND · HUMIDITY</div>",
        unsafe_allow_html=True,
    )

    forecast_days = st.selectbox(
        "Forecast Horizon",
        [7, 10, 14, 16],
        format_func=lambda d: f"{d} days ({d * 24}h)",
        key="gfs_days",
    )

    if st.button("FETCH GFS FORECAST", key="gfs_btn", use_container_width=True):
        with st.spinner(f"Fetching {forecast_days}-day GFS forecast..."):
            try:
                result = get_gfs_forecast(aoi_json, forecast_hours=forecast_days * 24)
                if result:
                    # Summary metrics
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Total Precipitation", f"{result['total_precip_mm']:.0f} mm")
                    c2.metric("Max Daily Precip", f"{result['max_daily_precip_mm']:.0f} mm")
                    c3.metric("Mean Temperature", f"{result['mean_temp_c']:.1f} °C")
                    c4.metric("Max Wind Speed", f"{result['max_wind_ms']:.1f} m/s")

                    # Daily forecast table
                    st.markdown(
                        '<div style="font-family:JetBrains Mono,monospace;'
                        'font-size:0.65rem;color:#64B5F6;margin:12px 0 6px 0;">'
                        "DAILY FORECAST</div>",
                        unsafe_allow_html=True,
                    )
                    st.dataframe(result["daily_df"], hide_index=True, use_container_width=True)

                    # Precipitation chart
                    chart_df = result["daily_df"].set_index("Day")[["Precip (mm)", "Temp (°C)"]]
                    st.bar_chart(chart_df["Precip (mm)"], height=250)
                    st.line_chart(chart_df["Temp (°C)"], height=200)

                    # Maps (only if tiles available)
                    col_l, col_r = st.columns(2)
                    _aoi_style_fn = lambda _: {  # noqa: E731
                        "fillColor": "none",
                        "color": "#00FFFF",
                        "weight": 2,
                        "dashArray": "6 4",
                    }
                    with col_l:
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                            "TOTAL PRECIPITATION</div>",
                            unsafe_allow_html=True,
                        )
                        pm = folium.Map(location=map_center, zoom_start=9, tiles="CartoDB dark_matter")
                        if result.get("precip_tile_url"):
                            folium.TileLayer(
                                tiles=result["precip_tile_url"],
                                attr="GEE·GFS",
                                name="Precipitation",
                                opacity=0.8,
                            ).add_to(pm)
                        folium.GeoJson(json.loads(aoi_json), style_function=_aoi_style_fn).add_to(pm)
                        folium_static(pm, height=350)

                    with col_r:
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.6rem;color:#64B5F6;margin-bottom:4px;">'
                            "TEMPERATURE</div>",
                            unsafe_allow_html=True,
                        )
                        tm = folium.Map(location=map_center, zoom_start=9, tiles="CartoDB dark_matter")
                        if result.get("temp_tile_url"):
                            folium.TileLayer(
                                tiles=result["temp_tile_url"],
                                attr="GEE·GFS",
                                name="Temperature",
                                opacity=0.8,
                            ).add_to(tm)
                        folium.GeoJson(json.loads(aoi_json), style_function=_aoi_style_fn).add_to(tm)
                        folium_static(tm, height=350)

                    # Flood alert assessment
                    with st.expander("FLOOD ALERT ASSESSMENT", expanded=True):
                        rp_data = st.session_state.get("rp_data")
                        alert = get_gfs_flood_alert(aoi_json, rp_data=rp_data)
                        if alert:
                            st.markdown(
                                f'<div style="display:inline-flex;align-items:center;gap:10px;'
                                f"background:rgba(144,202,249,0.04);"
                                f"border:2px solid {alert['color']};border-radius:10px;"
                                f'padding:12px 20px;margin:8px 0;">'
                                f'<span style="font-size:1.5rem;">{alert["icon"]}</span>'
                                f"<div>"
                                f'<div style="font-family:JetBrains Mono,monospace;'
                                f"font-size:1.1rem;font-weight:700;color:{alert['color']};"
                                f'letter-spacing:3px;">{alert["level"]}</div>'
                                f'<div style="font-size:0.75rem;color:#90CAF9;">'
                                f"7-day total: {alert['total_7day_mm']:.0f} mm · "
                                f"Peak day {alert['peak_day']} ({alert['max_daily_mm']:.0f} mm)"
                                f"</div></div></div>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.warning("No GFS forecast data available. GFS data may have a ~6h delay from the latest run.")
            except Exception as e:
                st.error(f"GFS forecast failed: {e}")
    else:
        st.info("Click to fetch the latest NOAA GFS weather forecast for your AOI.")


# ── Sub-tab 2: Flood Forecast ────────────────────────────────


def _render_flood_forecast(aoi_json, params):
    """LSTM/GBM flood probability forecasting."""
    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
        "ERA5-LAND TRAINING · GFS INPUT · LSTM / GBM · 7-14 DAY FLOOD PROBABILITY</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style=\"font-family:'Inter',sans-serif;font-size:0.78rem;"
        'color:#90CAF9;margin-bottom:12px;">'
        "Trains on 6 years of monsoon-season ERA5-Land data (precipitation, "
        "temperature, soil moisture, runoff) to learn flood patterns. "
        "Then uses GFS forecast weather as input to predict flood probability "
        "for the next 7-14 days.</div>",
        unsafe_allow_html=True,
    )

    if st.button("TRAIN & FORECAST", key="lstm_btn", use_container_width=True):
        with st.spinner("Extracting training data from ERA5 (2018-2023 monsoon seasons)..."):
            try:
                from ml_models.flood_forecaster import FloodForecaster

                forecaster = FloodForecaster()

                # Try loading pre-trained
                loaded = forecaster.load()
                if not loaded:
                    st.info("No pre-trained model found. Training on ERA5 data...")
                    trained = forecaster.train(aoi_json)
                    if not trained:
                        st.error("Training failed — insufficient ERA5 data for this AOI.")
                        return

                st.success(
                    f"Model ready ({forecaster.model_type if hasattr(forecaster, 'model_type') else 'GBM/LSTM'})"
                )

                # Get recent ERA5 data for context
                from datetime import datetime, timedelta

                from gee_functions.era5 import get_era5_timeseries

                end_date = datetime.utcnow().strftime("%Y-%m-%d")
                start_date = (datetime.utcnow() - timedelta(days=35)).strftime("%Y-%m-%d")

                with st.spinner("Fetching recent climate data..."):
                    recent = get_era5_timeseries(aoi_json, start_date, end_date, variable="total_precipitation_sum")

                if recent and recent["timeseries"] is not None:
                    ts = recent["timeseries"].reset_index()
                    ts.columns = ["date", "precip"]
                    ts["precip"] = ts["precip"] * 1000  # m to mm
                    ts["temp"] = 30.0  # placeholder
                    ts["soil_moisture"] = 0.3
                    ts["runoff"] = ts["precip"] * 0.3
                    ts["humidity"] = 70.0

                    # Get GFS forecast
                    with st.spinner("Fetching GFS forecast for prediction input..."):
                        gfs = get_gfs_forecast(aoi_json, forecast_hours=168)

                    forecast_df = None
                    if gfs and gfs["daily_df"] is not None:
                        forecast_df = gfs["daily_df"]

                    with st.spinner("Running flood probability prediction..."):
                        prediction = forecaster.predict(ts, forecast_df)

                    if prediction:
                        # Alert banner
                        risk = prediction["risk_level"]
                        risk_colors = {
                            "HIGH": "#d73027",
                            "MODERATE": "#fc8d59",
                            "LOW": "#fee08b",
                            "MINIMAL": "#1a9850",
                        }
                        risk_color = risk_colors.get(risk, "#90CAF9")

                        st.markdown(
                            f'<div style="display:inline-flex;align-items:center;gap:10px;'
                            f"background:rgba(144,202,249,0.04);"
                            f"border:2px solid {risk_color};border-radius:10px;"
                            f'padding:12px 20px;margin:8px 0;">'
                            f'<div style="font-family:JetBrains Mono,monospace;'
                            f"font-size:1.1rem;font-weight:700;color:{risk_color};"
                            f'letter-spacing:3px;">FLOOD RISK: {risk}</div></div>',
                            unsafe_allow_html=True,
                        )

                        # Metrics
                        pc1, pc2, pc3, pc4 = st.columns(4)
                        pc1.metric("Max Probability", f"{prediction['max_probability']:.1%}")
                        pc2.metric("Peak Day", f"Day {prediction['peak_day']}")
                        pc3.metric("Mean Probability", f"{prediction['mean_probability']:.1%}")
                        pc4.metric("Model", prediction["model_type"])

                        # Probability timeline
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:12px 0 6px 0;">'
                            "DAILY FLOOD PROBABILITY</div>",
                            unsafe_allow_html=True,
                        )
                        prob_df = pd.DataFrame(
                            {
                                "Day": range(1, len(prediction["daily_probabilities"]) + 1),
                                "Flood Probability": prediction["daily_probabilities"],
                            }
                        )
                        st.bar_chart(prob_df.set_index("Day"), height=280)
                        st.dataframe(prob_df, hide_index=True, use_container_width=True)
                    else:
                        st.warning("Prediction failed — model may need more training data.")
                else:
                    st.warning("Could not fetch recent ERA5 data for this AOI.")
            except Exception as e:
                st.error(f"Flood forecast failed: {e}")
    else:
        st.info(
            "Click to train a flood forecaster on historical ERA5 data and "
            "predict flood probability using the latest GFS weather forecast."
        )


# ── Sub-tab 3: Prithvi SAR ──────────────────────────────────


def _render_prithvi(aoi_json, params):
    """Prithvi-enhanced SAR flood classification."""
    map_center = params["map_center"]

    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
        "NASA/IBM PRITHVI · SENTINEL-1 · ENHANCED SAR CLASSIFICATION</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style=\"font-family:'Inter',sans-serif;font-size:0.78rem;"
        'color:#90CAF9;margin-bottom:12px;">'
        "Enhanced SAR flood segmentation inspired by the NASA/IBM Prithvi "
        "geospatial foundation model. Uses 9 SAR + terrain features including "
        "SAR coefficient of variation for improved flood/non-flood discrimination. "
        "Falls back to Gradient Boosting when Prithvi weights unavailable.</div>",
        unsafe_allow_html=True,
    )

    prob_mode = st.checkbox("Show probability map", value=False, key="prithvi_prob")

    if st.button("RUN PRITHVI CLASSIFICATION", key="prithvi_btn", use_container_width=True):
        with st.spinner("Running enhanced SAR flood classification..."):
            try:
                from ml_models.prithvi_flood import PrithviFloodClassifier

                classifier = PrithviFloodClassifier()

                result = classifier.predict_for_aoi(
                    aoi_json,
                    f_start=params["f_start"],
                    f_end=params["f_end"],
                    p_start=params["p_start"],
                    p_end=params["p_end"],
                    threshold=params["f_threshold"],
                    polarization=params["polarization"],
                    speckle=params["apply_speckle"],
                    return_probability=prob_mode,
                )

                if result:
                    # Model info
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;'
                        f'font-size:0.6rem;color:rgba(144,202,249,0.4);margin:4px 0;">'
                        f"MODEL: {result['model_name']} · "
                        f"PRITHVI: {'ACTIVE' if result['prithvi_available'] else 'FALLBACK GBM'}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    # Metrics
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Flood Pixels", f"{result['flood_pixels']:,}")
                    mc2.metric("Flood Coverage", f"{result['flood_pct']:.1f}%")
                    mc3.metric("Total Samples", f"{result['n_samples']:,}")

                    # Map
                    m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                    layer_name = "Flood Probability" if prob_mode else "Flood Classification"
                    folium.TileLayer(
                        tiles=result["tile_url"],
                        attr="GEE·Prithvi",
                        name=layer_name,
                        opacity=0.85,
                    ).add_to(m)
                    folium.GeoJson(
                        json.loads(aoi_json),
                        style_function=lambda _: {
                            "fillColor": "none",
                            "color": "#00FFFF",
                            "weight": 2,
                            "dashArray": "6 4",
                        },
                    ).add_to(m)
                    folium.LayerControl(position="topright", collapsed=False).add_to(m)
                    folium_static(m, height=450)

                    # Feature importance
                    if result.get("feature_importance"):
                        with st.expander("FEATURE IMPORTANCE", expanded=False):
                            imp_df = pd.DataFrame(
                                [
                                    {"Feature": k, "Importance": v}
                                    for k, v in sorted(
                                        result["feature_importance"].items(),
                                        key=lambda x: x[1],
                                        reverse=True,
                                    )
                                ]
                            )
                            st.dataframe(imp_df, hide_index=True, use_container_width=True)
                            st.bar_chart(imp_df.set_index("Feature"), height=250)
                else:
                    st.warning(
                        "Classification returned no results. Ensure SAR imagery is available for the selected dates."
                    )
            except Exception as e:
                st.error(f"Prithvi classification failed: {e}")
    else:
        st.info(
            "Click to run enhanced SAR flood classification using "
            "Prithvi-inspired features on your configured SAR date range."
        )


# ── Sub-tab: River Discharge (GloFAS) ────────────────────────


def _render_glofas(aoi_json, params):
    """GloFAS-style river discharge estimation and return period analysis."""
    map_center = params["map_center"]

    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
        "ERA5 RUNOFF · HYDROSHEDS ROUTING · DISCHARGE RETURN PERIODS</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style=\"font-family:'Inter',sans-serif;font-size:0.78rem;"
        'color:#90CAF9;margin-bottom:12px;">'
        "Estimates river discharge using ERA5-Land surface runoff weighted by "
        "HydroSHEDS flow accumulation. Computes Gumbel return periods from "
        "20-year monsoon maxima and evaluates current flood exceedance risk.</div>",
        unsafe_allow_html=True,
    )

    from gee_functions.glofas import (
        get_discharge_return_levels,
        get_flood_exceedance_forecast,
        get_river_discharge_estimate,
    )

    # Discharge time-series
    with st.expander("DISCHARGE TIME-SERIES", expanded=True):
        dc1, dc2 = st.columns(2)
        with dc1:
            dis_start = st.date_input("Start", value=pd.Timestamp("2024-06-01"), key="dis_start")
        with dc2:
            dis_end = st.date_input("End", value=pd.Timestamp("2024-10-31"), key="dis_end")

        if st.button("COMPUTE DISCHARGE", key="dis_btn", use_container_width=True):
            with st.spinner("Computing river discharge estimates..."):
                try:
                    result = get_river_discharge_estimate(aoi_json, dis_start, dis_end)
                    if result:
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Mean Discharge Index", f"{result['mean_discharge']:.3f}")
                        m2.metric("Peak Discharge", f"{result['max_discharge']:.3f}")
                        m3.metric("Total Runoff", f"{result['total_runoff_mm']:.0f} mm")

                        st.line_chart(result["timeseries"][["discharge_idx", "runoff_mm"]], height=280)

                        dm = folium.Map(location=map_center, zoom_start=10, tiles="CartoDB dark_matter")
                        folium.TileLayer(
                            tiles=result["tile_url"],
                            attr="GEE·ERA5·HydroSHEDS",
                            name="Discharge Proxy",
                            opacity=0.85,
                        ).add_to(dm)
                        folium.GeoJson(
                            json.loads(aoi_json),
                            style_function=lambda _: {
                                "fillColor": "none",
                                "color": "#00FFFF",
                                "weight": 2,
                                "dashArray": "6 4",
                            },
                        ).add_to(dm)
                        folium.LayerControl(position="topright", collapsed=False).add_to(dm)
                        folium_static(dm, height=400)
                    else:
                        st.warning("No discharge data available for this period.")
                except Exception as e:
                    st.error(f"Discharge computation failed: {e}")
        else:
            st.info("Click to compute river discharge estimates for the selected period.")

    # Return periods
    with st.expander("DISCHARGE RETURN PERIODS", expanded=False):
        if st.button("COMPUTE RETURN LEVELS", key="dis_rp_btn", use_container_width=True):
            with st.spinner("Fitting Gumbel distribution to 20-year monsoon maxima..."):
                try:
                    rp = get_discharge_return_levels(aoi_json)
                    if rp:
                        st.markdown(
                            '<div style="font-family:JetBrains Mono,monospace;'
                            'font-size:0.65rem;color:#64B5F6;margin:8px 0 4px 0;">'
                            f"GUMBEL FIT · {rp['n_years']} YEARS · "
                            f"MEAN MAX = {rp['mean_annual_max']:.3f}</div>",
                            unsafe_allow_html=True,
                        )
                        rp_df = pd.DataFrame(
                            [{"Return Period (yr)": t, "Discharge Index": v} for t, v in rp["return_levels"].items()]
                        )
                        st.dataframe(rp_df, hide_index=True, use_container_width=True)
                        st.bar_chart(rp_df.set_index("Return Period (yr)"), height=250)
                    else:
                        st.warning("Insufficient data for return period analysis.")
                except Exception as e:
                    st.error(f"Return period computation failed: {e}")

    # Flood exceedance
    with st.expander("FLOOD EXCEEDANCE FORECAST", expanded=False):
        if st.button("EVALUATE EXCEEDANCE", key="dis_exc_btn", use_container_width=True):
            with st.spinner("Comparing GFS forecast against discharge return levels..."):
                try:
                    exc = get_flood_exceedance_forecast(aoi_json)
                    if exc:
                        st.markdown(
                            f'<div style="display:inline-flex;align-items:center;gap:10px;'
                            f"background:rgba(144,202,249,0.04);"
                            f"border:2px solid {exc['color']};border-radius:10px;"
                            f'padding:12px 20px;margin:8px 0;">'
                            f'<div style="font-family:JetBrains Mono,monospace;'
                            f"font-size:1.1rem;font-weight:700;color:{exc['color']};"
                            f'letter-spacing:3px;">{exc["level"]}</div>'
                            f'<div style="font-size:0.75rem;color:#90CAF9;">'
                            f"Exceeds {exc['exceedance_return_period']}-year level · "
                            f"Forecast peak: {exc['forecast_max_precip_mm']:.0f} mm/day"
                            f"</div></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.warning(
                            "Could not evaluate exceedance. Ensure GFS data and historical baseline are available."
                        )
                except Exception as e:
                    st.error(f"Exceedance evaluation failed: {e}")


# ── Sub-tab: AI Foundation Models ─────────────────────────────


def _render_foundation_models(aoi_json, params):
    """Multi-model foundation model selection and flood classification."""
    map_center = params["map_center"]

    st.markdown(
        '<div style="font-family:JetBrains Mono,monospace;font-size:0.65rem;'
        'color:rgba(144,202,249,0.4);letter-spacing:2px;margin-bottom:8px;">'
        "PRITHVI-EO-2.0 · CLAY · ClimaX · PANGU-WEATHER · FOUNDATION MODELS</div>",
        unsafe_allow_html=True,
    )

    from ml_models.foundation_models import MODEL_REGISTRY, FoundationFloodClassifier

    # Model selection
    st.markdown(
        "<div style=\"font-family:'Inter',sans-serif;font-size:0.78rem;"
        'color:#90CAF9;margin-bottom:12px;">'
        "Select a geospatial foundation model for enhanced flood classification. "
        "Uses 12 features (SAR + terrain + water history + roughness). "
        "Falls back to Gradient Boosting when model weights are unavailable.</div>",
        unsafe_allow_html=True,
    )

    # Model cards
    cols = st.columns(len(MODEL_REGISTRY))
    for i, (key, info) in enumerate(MODEL_REGISTRY.items()):
        with cols[i]:
            st.markdown(
                f'<div style="background:rgba(144,202,249,0.04);'
                f"border:1px solid rgba(144,202,249,0.15);border-radius:8px;"
                f'padding:10px;text-align:center;">'
                f'<div style="font-family:JetBrains Mono,monospace;'
                f'font-size:0.7rem;color:#64B5F6;font-weight:700;">{info["name"]}</div>'
                f'<div style="font-size:0.6rem;color:rgba(144,202,249,0.5);">'
                f"{info['params']} · {info['input']}</div>"
                f'<div style="font-size:0.55rem;color:rgba(144,202,249,0.35);'
                f'margin-top:4px;">{info["task"]}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    model_key = st.selectbox(
        "Select Model",
        list(MODEL_REGISTRY.keys()),
        format_func=lambda k: f"{MODEL_REGISTRY[k]['name']} ({MODEL_REGISTRY[k]['params']})",
        key="fm_model",
    )
    prob_mode = st.checkbox("Probability map", value=False, key="fm_prob")

    if st.button("RUN CLASSIFICATION", key="fm_btn", use_container_width=True):
        with st.spinner(f"Running {MODEL_REGISTRY[model_key]['name']} classification..."):
            try:
                classifier = FoundationFloodClassifier(model_key=model_key)
                result = classifier.predict_for_aoi(
                    aoi_json,
                    f_start=params["f_start"],
                    f_end=params["f_end"],
                    p_start=params["p_start"],
                    p_end=params["p_end"],
                    threshold=params["f_threshold"],
                    polarization=params["polarization"],
                    speckle=params["apply_speckle"],
                    return_probability=prob_mode,
                )

                if result:
                    # Status
                    status = "FOUNDATION MODEL" if result["foundation_active"] else "GBM FALLBACK"
                    status_color = "#1a9850" if result["foundation_active"] else "#fc8d59"
                    st.markdown(
                        f'<div style="font-family:JetBrains Mono,monospace;'
                        f'font-size:0.6rem;color:{status_color};margin:4px 0;">'
                        f"{result['model_name']} · {status} · "
                        f"{result['n_features']} FEATURES</div>",
                        unsafe_allow_html=True,
                    )

                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Flood Pixels", f"{result['flood_pixels']:,}")
                    mc2.metric("Flood Coverage", f"{result['flood_pct']:.1f}%")
                    mc3.metric("Samples", f"{result['n_samples']:,}")

                    m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                    folium.TileLayer(
                        tiles=result["tile_url"],
                        attr=f"GEE·{result['model_name']}",
                        name=result["model_name"],
                        opacity=0.85,
                    ).add_to(m)
                    folium.GeoJson(
                        json.loads(aoi_json),
                        style_function=lambda _: {
                            "fillColor": "none",
                            "color": "#00FFFF",
                            "weight": 2,
                            "dashArray": "6 4",
                        },
                    ).add_to(m)
                    folium.LayerControl(position="topright", collapsed=False).add_to(m)
                    folium_static(m, height=450)

                    if result.get("feature_importance"):
                        with st.expander("FEATURE IMPORTANCE", expanded=False):
                            imp_df = pd.DataFrame(
                                [
                                    {"Feature": k, "Importance": v}
                                    for k, v in sorted(
                                        result["feature_importance"].items(),
                                        key=lambda x: x[1],
                                        reverse=True,
                                    )
                                ]
                            )
                            st.dataframe(imp_df, hide_index=True, use_container_width=True)
                            st.bar_chart(imp_df.set_index("Feature"), height=250)
                else:
                    st.warning("Classification returned no results.")
            except Exception as e:
                st.error(f"Foundation model classification failed: {e}")
    else:
        st.info("Select a foundation model and click to run flood classification.")
