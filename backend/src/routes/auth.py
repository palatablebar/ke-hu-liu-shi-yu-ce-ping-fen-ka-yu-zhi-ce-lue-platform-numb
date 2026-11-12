from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(db, payload, request)


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict:
    return auth_controller.me(db, request)
