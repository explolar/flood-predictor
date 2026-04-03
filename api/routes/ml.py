"""ML API routes."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException

from api.dependencies import aoi_to_json, initialize_ee_api
from api.schemas import AnalysisResponse, MLRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ML"])


def _get_classifier(model_name: str):
    """Instantiate the appropriate classifier by model name."""
    if model_name == "xgboost":
        from ml_models.xgb_classifier import XGBFloodClassifier

        return XGBFloodClassifier()
    elif model_name == "lightgbm":
        from ml_models.lgbm_classifier import LGBMFloodClassifier

        return LGBMFloodClassifier()
    elif model_name == "ensemble":
        from ml_models.ensemble_stacker import EnsembleFloodClassifier

        return EnsembleFloodClassifier()
    else:
        from ml_models.sar_classifier import SARFloodClassifier

        return SARFloodClassifier()


@router.post("/classify", response_model=AnalysisResponse)
async def classify_flood(request: MLRequest):
    """Run ML flood classification."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        classifier = _get_classifier(request.model)

        result = await asyncio.to_thread(
            classifier.classify_for_aoi,
            aoi_json,
            request.f_start,
            request.f_end,
            request.p_start,
            request.p_end,
            request.threshold,
            request.polarization,
            request.speckle,
            return_probability=request.return_probability,
        )

        if result:
            return AnalysisResponse(success=True, data=result)
        return AnalysisResponse(success=False, error="Classification returned no results.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _compute_shap(model_name: str, aoi_json: str, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """
    Train/load the classifier and compute SHAP feature importance.

    Only tree-based models are supported (GradientBoosting, XGBoost, LightGBM).
    The ensemble model uses its gb_model (GradientBoosting base learner) for SHAP.
    Data extraction is cached, so this doesn't duplicate GEE calls if classify was run first.
    """
    from ml_models.data_extraction import extract_sar_training_samples
    from ml_models.explainability import SHAPExplainer

    classifier = _get_classifier(model_name)

    # Load pretrained or train on-the-fly (same logic as classify_for_aoi)
    pretrained = classifier.load()

    # Extract features (cached via @cache_data)
    df = extract_sar_training_samples(
        aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle, n_points=4000, scale=30
    )

    if df.empty or len(df) < 100:
        return None

    if not pretrained:
        classifier.train(df)

    # Pick the tree-based model to explain
    if model_name == "ensemble":
        # Ensemble uses LogisticRegression meta-learner which isn't tree-based.
        # Explain the GradientBoosting base learner instead.
        tree_model = classifier.gb_model
    else:
        tree_model = classifier.model

    feature_names = classifier.feature_names

    explainer = SHAPExplainer()
    explainer.explain(tree_model, df, feature_names, max_samples=500)

    # Mean |SHAP| per feature as dict
    shap_df = explainer.get_feature_shap_df(feature_names)
    if shap_df is None:
        return None

    shap_importance = {str(k): float(v) for k, v in zip(shap_df["Feature"], shap_df["Mean |SHAP|"])}

    # Generate the SHAP summary bar plot as base64 PNG
    summary_plot = explainer.summary_plot_base64(max_display=len(feature_names))

    return {
        "shap_importance": shap_importance,
        "summary_plot_b64": summary_plot,
        "n_samples_explained": len(df) if len(df) <= 500 else 500,
        "model_name": model_name,
    }


@router.post("/explain", response_model=AnalysisResponse)
async def explain_model(request: MLRequest):
    """Compute SHAP explainability for the selected ML model.

    Returns mean |SHAP| values per feature and an optional summary plot.
    Only tree-based models are supported (GradientBoosting, XGBoost, LightGBM, Ensemble).
    """
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        result = await asyncio.to_thread(
            _compute_shap,
            request.model,
            aoi_json,
            request.f_start,
            request.f_end,
            request.p_start,
            request.p_end,
            request.threshold,
            request.polarization,
            request.speckle,
        )

        if result:
            return AnalysisResponse(success=True, data=result)
        return AnalysisResponse(success=False, error="SHAP computation returned no results (too few samples?).")
    except ImportError as e:
        logger.warning("SHAP dependency missing: %s", e)
        return AnalysisResponse(success=False, error=f"SHAP not available: {e}")
    except Exception as e:
        logger.exception("SHAP computation failed")
        raise HTTPException(status_code=500, detail=f"SHAP computation failed: {e}")


@router.post("/risk-prediction", response_model=AnalysisResponse)
async def predict_risk(request: MLRequest):
    """Run Random Forest flood risk prediction."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from ml_models.flood_risk_model import FloodRiskPredictor

        predictor = FloodRiskPredictor()
        result = await asyncio.to_thread(predictor.predict_for_aoi, aoi_json)

        if result:
            return AnalysisResponse(success=True, data=result)
        return AnalysisResponse(success=False, error="Prediction returned no results.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
