from fastapi import Request
from sqlalchemy.orm import Session

from src.schemas.model import TrainRequest
from src.services import audit_service, model_service


def list_models(db: Session, limit: int = 20) -> dict:
    return {"items": model_service.list_models(db, limit)}


def get_model(db: Session, model_id: int) -> dict:
    return model_service.model_payload(model_service.get_model(db, model_id))


def train(db: Session, payload: TrainRequest, actor: dict, request: Request) -> dict:
    run = model_service.create_model_run(
        db,
        actor_email=actor["email"],
        label=payload.label,
        hyperparams={
            "learning_rate": payload.learning_rate,
            "l2": payload.l2,
            "epochs": payload.epochs,
        },
        dispatch=True,
    )
    audit_service.record(
        db,
        actor_email=actor["email"],
        actor_role=actor["role"],
        action="model.train",
        resource_type="model_run",
        resource_id=str(run.id),
        detail={"run_no": run.run_no, "hyperparams": run.hyperparams},
        ip=request.client.host if request.client else "",
        request_id=getattr(request.state, "request_id", ""),
    )
    return model_service.model_payload(run)
