"""ML API routes."""

from fastapi import APIRouter, HTTPException
from api.schemas import MLRequest, AnalysisResponse
from api.dependencies import initialize_ee_api, aoi_to_json

router = APIRouter(prefix="/ml", tags=["ML"])


@router.post("/classify", response_model=AnalysisResponse)
async def classify_flood(request: MLRequest):
    """Run ML flood classification."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        if request.model == "xgboost":
            from ml_models.xgb_classifier import XGBFloodClassifier
            classifier = XGBFloodClassifier()
        elif request.model == "lightgbm":
            from ml_models.lgbm_classifier import LGBMFloodClassifier
            classifier = LGBMFloodClassifier()
        elif request.model == "ensemble":
            from ml_models.ensemble_stacker import EnsembleFloodClassifier
            classifier = EnsembleFloodClassifier()
        else:
            from ml_models.sar_classifier import SARFloodClassifier
            classifier = SARFloodClassifier()

        result = classifier.classify_for_aoi(
            aoi_json, request.f_start, request.f_end,
            request.p_start, request.p_end,
            request.threshold, request.polarization, request.speckle,
            return_probability=request.return_probability
        )

        if result:
            return AnalysisResponse(success=True, data=result)
        return AnalysisResponse(success=False, error="Classification returned no results.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-prediction", response_model=AnalysisResponse)
async def predict_risk(request: MLRequest):
    """Run Random Forest flood risk prediction."""
    initialize_ee_api()
    aoi_json = aoi_to_json(request.geojson)

    try:
        from ml_models.flood_risk_model import FloodRiskPredictor
        predictor = FloodRiskPredictor()
        result = predictor.predict_for_aoi(aoi_json)

        if result:
            return AnalysisResponse(success=True, data=result)
        return AnalysisResponse(success=False, error="Prediction returned no results.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
