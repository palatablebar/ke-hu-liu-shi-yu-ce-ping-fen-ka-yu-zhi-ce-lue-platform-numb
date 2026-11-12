"""Celery task: train one logistic-regression batch inside the worker container."""
from src.config.celery_app import celery_app
from src.config.database import SessionLocal
from src.services import model_service


@celery_app.task(name="churnmod.train_model", bind=True, max_retries=0)
def train_model(self, model_id: int) -> dict:
    db = SessionLocal()
    try:
        return model_service.execute_train(db, model_id)
    finally:
        db.close()
