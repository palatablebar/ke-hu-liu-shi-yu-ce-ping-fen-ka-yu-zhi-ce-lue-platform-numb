from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import Role
from src.controllers import audit_controller
from src.middlewares.rbac import require_roles
from src.schemas.common import PageMeta  # noqa: F401  (schema layer reference)

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
def list_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_roles(Role.ADMIN)),
) -> dict:
    return audit_controller.list_logs(db, limit)
