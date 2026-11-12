from sqlalchemy.orm import Session

from src.services import account_service, audit_service, feature_service, model_service, score_service


def list_logs(db: Session, limit: int = 100) -> dict:
    return {"items": audit_service.list_logs(db, limit)}


def overview(db: Session) -> dict:
    payload = account_service.overview(db)
    payload["feature_catalog"] = feature_service.feature_set_definition(db)
    payload["models"] = model_service.list_models(db, 10)
    payload["score_batches"] = score_service.list_batches(db, 10)
    return payload
