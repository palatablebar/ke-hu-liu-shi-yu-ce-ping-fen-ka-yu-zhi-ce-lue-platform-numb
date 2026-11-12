from sqlalchemy.orm import Session

from src.services import account_service, feature_service
from src.utils.pagination import pagination


def risk_list(db: Session, actor: dict, search: str = "", band: str = "", page: int = 1, page_size: int = 20) -> dict:
    return account_service.risk_list(db, actor, search, band, pagination(page, page_size))


def detail(db: Session, actor: dict, code: str) -> dict:
    return account_service.account_detail(db, actor, code)


def features(db: Session) -> dict:
    return feature_service.feature_set_definition(db)


def overview(db: Session) -> dict:
    return account_service.overview(db)
