from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import Role
from src.controllers import score_controller
from src.middlewares.rbac import require_roles
from src.schemas.score import ScoreCreateRequest

router = APIRouter(prefix="/scores", tags=["score"])


def _actor(request: Request) -> dict:
    return {
        "email": getattr(request.state, "user_email", ""),
        "role": getattr(request.state, "user_role", ""),
    }


# 静态路径优先注册，避免被 /{batch_id} 参数路由遮蔽。
@router.get("")
def list_batches(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    return score_controller.list_batches(db, limit)


@router.get("/active")
def active_batch(db: Session = Depends(get_db)) -> dict:
    return score_controller.active_batch(db)


@router.get("/export/active")
def export_active(request: Request, db: Session = Depends(get_db)) -> Response:
    return score_controller.export_active(db, _actor(request))


@router.post("", status_code=201)
def create_batch(
    payload: ScoreCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(Role.ADMIN, Role.ANALYST)),
) -> dict:
    return score_controller.create_batch(db, payload, actor, request)


@router.post("/{batch_id}/publish")
def publish(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_roles(Role.ADMIN)),
) -> dict:
    return score_controller.publish(db, batch_id, actor, request)


@router.get("/{batch_id}/diff")
def diff(batch_id: int, db: Session = Depends(get_db)) -> dict:
    return score_controller.diff(db, batch_id)


@router.get("/{batch_id}/export")
def export(batch_id: int, request: Request, db: Session = Depends(get_db)) -> Response:
    return score_controller.export(db, batch_id, _actor(request))


@router.get("/{batch_id}")
def get_batch(batch_id: int, include_results: bool = True, db: Session = Depends(get_db)) -> dict:
    return score_controller.get_batch(db, batch_id, include_results)
