from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    return audit_controller.overview(db)
