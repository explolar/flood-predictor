"""Tab 5: ML Intelligence — clean, consolidated layout."""

import os
import streamlit as st
import folium
import pandas as pd
from streamlit_folium import folium_static

from ui_components.legends import get_mca_legend


def render_ml_tab(aoi_json, params):
    """Render the ML Intelligence tab with sub-tab navigation."""
    f_start = params['f_start']
    f_end = params['f_end']
    p_start = params['p_start']
    p_end = params['p_end']
    f_threshold = params['f_threshold']
    polarization = params['polarization']
    apply_speckle = params['apply_speckle']
    aoi = params['aoi']
    map_center = params['map_center']

    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.78rem;'
        'letter-spacing:2px;color:rgba(0,255,255,0.4);margin-bottom:12px;">'
        'MACHINE LEARNING SUITE</div>',
        unsafe_allow_html=True,
    )

    # ── Sub-tab navigation ─────────────────────────
    ml_tab1, ml_tab2, ml_tab3 = st.tabs([
        "  CLASSIFIERS  ", "  ANALYTICS  ", "  TOOLS & DIAGNOSTICS  "
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SUB-TAB 1: CLASSIFIERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with ml_tab1:
        _render_classifiers(
            aoi_json, aoi, map_center,
            f_start, f_end, p_start, p_end,
            f_threshold, polarization, apply_speckle,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SUB-TAB 2: ANALYTICS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with ml_tab2:
        _render_analytics(
            aoi_json, aoi,
            f_start, f_end, p_start, p_end,
            f_threshold, polarization, apply_speckle,
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  SUB-TAB 3: TOOLS & DIAGNOSTICS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with ml_tab3:
        _render_tools(
            aoi_json,
            f_start, f_end, p_start, p_end,
            f_threshold, polarization, apply_speckle,
        )


# ─────────────────────────────────────────────────
#  CLASSIFIERS
# ─────────────────────────────────────────────────
def _render_classifiers(aoi_json, aoi, map_center,
                        f_start, f_end, p_start, p_end,
                        f_threshold, polarization, apply_speckle):
    """Flood Risk RF · SAR Multi-model (GB / XGB / LGBM / Ensemble)."""

    from ml_models.flood_risk_model import FloodRiskPredictor
    from ml_models.sar_classifier import SARFloodClassifier

    # ── 1. FLOOD RISK PREDICTION ──────────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin:16px 0 6px;">'
        'FLOOD RISK PREDICTION</div>'
        '<div style="font-size:0.7rem;color:#3a5060;margin-bottom:10px;">'
        'Random Forest · 6 GEE features · 5-class risk output</div>',
        unsafe_allow_html=True,
    )

    if st.button("RUN RISK PREDICTION", key="ml_risk_btn", use_container_width=True):
        with st.spinner("Extracting features & running Random Forest..."):
            try:
                predictor = FloodRiskPredictor()
                result = predictor.predict_for_aoi(aoi_json)
                if result and result.get('tile_url'):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Model", "Random Forest")
                    c2.metric("Features", f"{len(predictor.feature_names)}")
                    c3.metric("Samples", f"{result.get('n_samples', 'N/A')}")
                    c4.metric("OOB Score", f"{result.get('oob_score', 'N/A')}")
                    m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                    folium.TileLayer(tiles=result['tile_url'], attr='GEE·ML', name='ML Risk').add_to(m)
                    folium.GeoJson(aoi.getInfo(), style_function=lambda _: {
                        'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'
                    }).add_to(m)
                    folium.LayerControl(position='topright', collapsed=False).add_to(m)
                    m.get_root().html.add_child(folium.Element(get_mca_legend(m.get_name())))
                    folium_static(m, height=450)
                    if result.get('feature_importance'):
                        imp_df = (pd.DataFrame(list(result['feature_importance'].items()),
                                               columns=['Feature', 'Importance'])
                                  .sort_values('Importance', ascending=False)
                                  .set_index('Feature'))
                        st.bar_chart(imp_df, color="#00FFFF", height=200)
                else:
                    st.warning("Risk prediction returned no results.")
            except Exception as e:
                st.error(f"Risk prediction failed: {e}")
    else:
        st.info("Run ML flood risk prediction on the current AOI.")

    st.markdown('<hr style="border-color:rgba(0,255,255,0.08);margin:24px 0;">', unsafe_allow_html=True)

    # ── 2. SAR FLOOD CLASSIFICATION ───────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin-bottom:6px;">'
        'SAR FLOOD CLASSIFICATION</div>'
        '<div style="font-size:0.7rem;color:#3a5060;margin-bottom:10px;">'
        'Multi-model pixel-wise classification · GB / XGB / LGBM / Ensemble</div>',
        unsafe_allow_html=True,
    )

    col_model, col_prob = st.columns([3, 1])
    with col_model:
        sar_model_choice = st.radio(
            "Classifier", ("Gradient Boosting", "XGBoost", "LightGBM", "Ensemble"),
            horizontal=True, key="sar_model_choice", label_visibility="collapsed",
        )
    with col_prob:
        show_probability = st.checkbox("Probability map", key="ml_sar_prob")

    if st.button("RUN CLASSIFICATION", key="ml_sar_btn", use_container_width=True):
        with st.spinner(f"Running {sar_model_choice}..."):
            try:
                if sar_model_choice == "XGBoost":
                    from ml_models.xgb_classifier import XGBFloodClassifier
                    classifier = XGBFloodClassifier()
                elif sar_model_choice == "LightGBM":
                    from ml_models.lgbm_classifier import LGBMFloodClassifier
                    classifier = LGBMFloodClassifier()
                elif sar_model_choice == "Ensemble":
                    from ml_models.ensemble_stacker import EnsembleFloodClassifier
                    classifier = EnsembleFloodClassifier()
                else:
                    classifier = SARFloodClassifier()

                result = classifier.classify_for_aoi(
                    aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
                    f_threshold, polarization, apply_speckle,
                    return_probability=show_probability,
                )
                if result and result.get('tile_url'):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Model", result.get('model_name', sar_model_choice))
                    c2.metric("ML Flood", f"{result.get('ml_area_ha', 0)} ha")
                    c3.metric("Threshold", f"{result.get('threshold_area_ha', 0)} ha")
                    diff = result.get('ml_area_ha', 0) - result.get('threshold_area_ha', 0)
                    c4.metric("Diff", f"{diff:+.1f} ha")
                    m = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB dark_matter")
                    folium.TileLayer(tiles=result['tile_url'], attr='GEE·ML', name='ML Classification').add_to(m)
                    folium.GeoJson(aoi.getInfo(), style_function=lambda _: {
                        'fillColor': 'none', 'color': '#00FFFF', 'weight': 2, 'dashArray': '6 4'
                    }).add_to(m)
                    folium.LayerControl(position='topright', collapsed=False).add_to(m)
                    folium_static(m, height=450)
                    if result.get('feature_importance'):
                        imp_df = (pd.DataFrame(list(result['feature_importance'].items()),
                                               columns=['Feature', 'Importance'])
                                  .sort_values('Importance', ascending=False)
                                  .set_index('Feature'))
                        st.bar_chart(imp_df, color="#FF6B6B", height=200)
                else:
                    st.warning("Classification returned no results.")
            except ImportError as ie:
                st.error(f"Missing dependency: {ie}")
            except Exception as e:
                st.error(f"Classification failed: {e}")
    else:
        st.info("Select a classifier and click RUN to classify flood pixels.")


# ─────────────────────────────────────────────────
#  ANALYTICS
# ─────────────────────────────────────────────────
def _render_analytics(aoi_json, aoi,
                      f_start, f_end, p_start, p_end,
                      f_threshold, polarization, apply_speckle):
    """SHAP Explainability · Anomaly Detection."""

    from ml_models.sar_classifier import SARFloodClassifier

    # ── SHAP EXPLAINABILITY ───────────────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin:16px 0 6px;">'
        'SHAP EXPLAINABILITY</div>'
        '<div style="font-size:0.7rem;color:#3a5060;margin-bottom:10px;">'
        'Shapley values · Feature attribution · Model transparency</div>',
        unsafe_allow_html=True,
    )

    if st.button("COMPUTE SHAP VALUES", key="ml_shap_btn", use_container_width=True):
        with st.spinner("Computing SHAP values..."):
            try:
                from ml_models.explainability import SHAPExplainer
                from ml_models.data_extraction import extract_sar_training_samples
                df = extract_sar_training_samples(
                    aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
                    f_threshold, polarization, apply_speckle, n_points=3000, scale=30,
                )
                feature_names = ['pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
                                 'elevation', 'slope', 'jrc_occ', 'jrc_season']
                classifier = SARFloodClassifier()
                classifier.train(df)

                explainer = SHAPExplainer()
                explainer.explain(classifier.model, df, feature_names, max_samples=300)

                shap_df = explainer.get_feature_shap_df(feature_names)
                if shap_df is not None:
                    st.dataframe(shap_df.set_index('Feature'), use_container_width=True)

                img_b64 = explainer.summary_plot_base64()
                if img_b64:
                    st.markdown(
                        f'<img src="data:image/png;base64,{img_b64}" '
                        f'style="width:100%;border-radius:8px;border:1px solid rgba(0,255,255,0.1);">',
                        unsafe_allow_html=True,
                    )
            except ImportError:
                st.error("shap/matplotlib not installed. Run: pip install shap matplotlib")
            except Exception as e:
                st.error(f"SHAP computation failed: {e}")
    else:
        st.info("Compute SHAP feature attributions for the SAR flood classifier.")

    st.markdown('<hr style="border-color:rgba(0,255,255,0.08);margin:24px 0;">', unsafe_allow_html=True)

    # ── ANOMALY DETECTION ─────────────────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin-bottom:6px;">'
        'ANOMALY DETECTION</div>'
        '<div style="font-size:0.7rem;color:#3a5060;margin-bottom:10px;">'
        'Isolation Forest · Monthly SAR backscatter patterns</div>',
        unsafe_allow_html=True,
    )

    ad_start_year = st.slider("Historical range start", 2018, 2023, 2018, key="ad_start")
    if st.button("DETECT ANOMALIES", key="ml_anomaly_btn", use_container_width=True):
        with st.spinner("Analyzing monthly SAR statistics..."):
            try:
                from ml_models.anomaly_detector import FloodAnomalyDetector
                detector = FloodAnomalyDetector(contamination=0.1)
                result = detector.detect_from_sar_timeseries(
                    aoi_json, start_year=ad_start_year, end_year=2024,
                    polarization=polarization,
                )
                if result:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Months Analyzed", result['n_total'])
                    c2.metric("Anomalies", result['n_anomalies'])
                    c3.metric("Features", len(result['features_used']))

                    chart_df = detector.get_anomaly_chart_data()
                    if chart_df is not None:
                        st.line_chart(chart_df[['mean_backscatter']], height=200)
                        if result['n_anomalies'] > 0:
                            anomaly_df = chart_df[chart_df['anomaly'] == 1][['mean_backscatter', 'anomaly_score']]
                            st.markdown(
                                '<div style="font-size:0.7rem;color:rgba(0,255,255,0.4);'
                                'letter-spacing:2px;margin:10px 0 4px;">ANOMALOUS MONTHS</div>',
                                unsafe_allow_html=True,
                            )
                            st.dataframe(anomaly_df, use_container_width=True)
                else:
                    st.warning("Insufficient SAR data for anomaly detection.")
            except Exception as e:
                st.error(f"Anomaly detection failed: {e}")
    else:
        st.info("Analyze monthly SAR backscatter patterns for anomalies.")


# ─────────────────────────────────────────────────
#  TOOLS & DIAGNOSTICS
# ─────────────────────────────────────────────────
def _render_tools(aoi_json,
                  f_start, f_end, p_start, p_end,
                  f_threshold, polarization, apply_speckle):
    """AutoML Tuning · Model Diagnostics."""

    # ── AUTOML TUNING ─────────────────────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin:16px 0 6px;">'
        'HYPERPARAMETER TUNING</div>'
        '<div style="font-size:0.7rem;color:#3a5060;margin-bottom:10px;">'
        'Optuna Bayesian optimization · Cross-validated F1</div>',
        unsafe_allow_html=True,
    )

    col_tune, col_trials = st.columns([2, 1])
    with col_tune:
        tune_model = st.radio(
            "Model to tune", ("Gradient Boosting", "XGBoost"),
            horizontal=True, key="tune_model", label_visibility="collapsed",
        )
    with col_trials:
        n_trials = st.slider("Trials", 10, 100, 30, step=10, key="n_trials")

    if st.button("START TUNING", key="ml_tune_btn", use_container_width=True):
        with st.spinner(f"Running {n_trials} Optuna trials for {tune_model}..."):
            try:
                from ml_models.automl_tuner import OptunaTuner
                from ml_models.data_extraction import extract_sar_training_samples
                tuner = OptunaTuner(n_trials=n_trials)
                df = extract_sar_training_samples(
                    aoi_json, str(f_start), str(f_end), str(p_start), str(p_end),
                    f_threshold, polarization, apply_speckle, n_points=5000, scale=30,
                )
                feature_names = ['pre_sar', 'post_sar', 'sar_diff', 'sar_ratio',
                                 'elevation', 'slope', 'jrc_occ', 'jrc_season']
                if tune_model == "XGBoost":
                    result = tuner.tune_xgboost(df, feature_names)
                else:
                    result = tuner.tune_gradient_boosting(df, feature_names)

                c1, c2 = st.columns(2)
                c1.metric("Best F1", f"{result['best_score']:.4f}")
                c2.metric("Trials", result['n_trials'])
                st.json(result['best_params'])

                history_df = tuner.get_optimization_history()
                if history_df is not None:
                    st.line_chart(history_df.set_index('trial')['score'], height=200)
            except ImportError:
                st.error("Optuna not installed. Run: pip install optuna")
            except Exception as e:
                st.error(f"Tuning failed: {e}")
    else:
        st.info("Run Bayesian hyperparameter optimization with Optuna.")

    st.markdown('<hr style="border-color:rgba(0,255,255,0.08);margin:24px 0;">', unsafe_allow_html=True)

    # ── MODEL DIAGNOSTICS ─────────────────────────
    st.markdown(
        '<div style="font-family:\'Rajdhani\',sans-serif;font-size:0.95rem;'
        'font-weight:700;letter-spacing:2px;color:#00FFFF;margin-bottom:10px;">'
        'MODEL DIAGNOSTICS</div>',
        unsafe_allow_html=True,
    )

    model_files = [
        ("Flood Risk RF", "models/flood_risk_rf.joblib"),
        ("SAR Classifier GB", "models/sar_classifier_gb.joblib"),
        ("SAR Classifier XGB", "models/sar_classifier_xgb.joblib"),
        ("SAR Classifier LGBM", "models/sar_classifier_lgbm.joblib"),
        ("Ensemble Stacker", "models/ensemble_stacker.joblib"),
    ]
    diag_data = []
    for name, path in model_files:
        exists = os.path.exists(path)
        size = f"{os.path.getsize(path) / 1024:.1f} KB" if exists else "—"
        diag_data.append({
            "Model": name,
            "Status": "Trained" if exists else "On-the-fly",
            "File": path,
            "Size": size,
        })
    st.dataframe(pd.DataFrame(diag_data), use_container_width=True, hide_index=True)
    st.caption("Models without pre-trained files will train on-the-fly using the current AOI. "
               "Use `training/` scripts for offline pre-training.")
