import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "flood_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(bind=True, name="train_ml_model_task")
def train_ml_model_task(self, model_name, aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle):
    """Background task to extract Earth Engine samples and train Random Forest/XGBoost over an extended period."""
    from api.dependencies import initialize_ee_api
    from api.routes.ml import _get_classifier
    import json

    # Init EE inside the worker thread
    initialize_ee_api()

    # Get model and train
    classifier = _get_classifier(model_name)
    
    self.update_state(state='PROGRESS', meta={'message': 'Extracting GEE samples...'})
    
    # Actually run the classification which trains and returns a payload
    result = classifier.classify_for_aoi(
        aoi_json, f_start, f_end, p_start, p_end, threshold, polarization, speckle, return_probability=False
    )
    
    return result
