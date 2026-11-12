from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import account_controller

router = APIRouter(prefix="/accounts", tags=["account"])


def _actor(request: Request) -> dict:
    return {
        "email": getattr(request.state, "user_email", ""),
        "role": getattr(request.state, "user_role", ""),
    }


@router.get("")
def risk_list(
    request: Request,
    search: str = "",
    band: str = "",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    return account_controller.risk_list(db, _actor(request), search, band, page, page_size)


@router.get("/{code}")
def detail(code: str, request: Request, db: Session = Depends(get_db)) -> dict:
    return account_controller.detail(db, _actor(request), code)
