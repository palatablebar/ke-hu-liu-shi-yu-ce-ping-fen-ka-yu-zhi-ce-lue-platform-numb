from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import account_controller
from src.services import feature_service

router = APIRouter(prefix="/features", tags=["feature"])


@router.get("/sets")
def list_sets(db: Session = Depends(get_db)) -> dict:
    return {"items": feature_service.list_feature_sets(db)}


@router.get("")
def definition(db: Session = Depends(get_db)) -> dict:
    return account_controller.features(db)


@router.get("/statistics")
def statistics(month: str = "", db: Session = Depends(get_db)) -> dict:
    return feature_service.feature_statistics(db, month or None)
