from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import Role
from src.controllers import model_controller
from src.middlewares.rbac import require_roles
from src.schemas.model import TrainRequest

router = APIRouter(prefix="/models", tags=["model"])


@router.get("")
def list_models(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    return model_controller.list_models(db, limit)


@router.post("/train", status_code=202)
def train(
    payload: TrainRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(Role.ADMIN, Role.ANALYST)),
) -> dict:
    return model_controller.train(db, payload, actor, request)


@router.get("/{model_id}")
def get_model(model_id: int, db: Session = Depends(get_db)) -> dict:
    return model_controller.get_model(db, model_id)
