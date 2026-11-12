"""Customer risk list scoped by role, account detail and overview numbers."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.messages import MSG_ACCOUNT_NOT_FOUND, MSG_FORBIDDEN
from src.constants.risk_band import RISK_BAND_LABELS
from src.models.account import Account
from src.models.account_feature import AccountFeature
from src.models.model_run import ModelRun
from src.models.score_batch import ScoreBatch
from src.services import feature_service, model_service, score_service
from src.utils.pagination import Pagination, as_page


def _scope_email(actor: dict) -> str | None:
    return actor["email"] if actor["role"] == "csm" else None


def risk_list(
    db: Session,
    actor: dict,
    search: str,
    band: str,
    pagination: Pagination,
) -> dict:
    # 风险图只跟随现行策略；草稿不影响名单，没有发布过策略时名单为空。
    batch = score_service.active_batch(db)
    if batch is None:
        return {**as_page([], 0, pagination), "batch": None, "bands": {}}
    scope = _scope_email(actor)
    rows = batch.results or []
    if scope:
        rows = [row for row in rows if row.get("csm_owner_email") == scope]
    if search:
        needle = search.strip().lower()
        rows = [
            row
            for row in rows
            if needle in row.get("account_code", "").lower() or needle in row.get("company_name", "").lower()
        ]
    if band:
        rows = [row for row in rows if row.get("band") == band]
    rows = sorted(rows, key=lambda row: row.get("score", 0.0), reverse=True)
    total = len(rows)
    start = pagination.offset
    items = rows[start : start + pagination.page_size]
    payload = as_page(items, total, pagination)
    payload.update(
        {
            "batch": score_service.batch_payload(batch),
            "bands": {key: RISK_BAND_LABELS[key] for key in RISK_BAND_LABELS},
            "scope_owner": scope,
        }
    )
    return payload


def account_detail(db: Session, actor: dict, code: str) -> dict:
    account = db.execute(select(Account).where(Account.code == code)).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail=MSG_ACCOUNT_NOT_FOUND)
    scope = _scope_email(actor)
    if scope and account.csm_owner_email != scope:
        raise HTTPException(status_code=403, detail=MSG_FORBIDDEN)
    features = (
        db.execute(
            select(AccountFeature).where(AccountFeature.account_id == account.id).order_by(AccountFeature.month)
        )
        .scalars()
        .all()
    )
    batch = score_service.active_batch(db)
    score_row = None
    if batch is not None:
        score_row = next(
            (row for row in (batch.results or []) if row.get("account_code") == code),
            None,
        )
    return {
        "account": {
            "code": account.code,
            "company_name": account.company_name,
            "industry": account.industry,
            "plan": account.plan,
            "region": account.region,
            "seats": account.seats,
            "monthly_fee": account.monthly_fee,
            "csm_owner_email": account.csm_owner_email,
            "csm_owner_name": account.csm_owner_name,
            "contract_end": account.contract_end.isoformat(),
            "status": account.status,
            "churn_date": account.churn_date.isoformat() if account.churn_date else None,
        },
        "months": [
            {
                "month": row.month_label,
                "features": row.features,
                "churn_next_30d": row.churn_next_30d,
            }
            for row in features
        ],
        "score": score_row,
        "batch": score_service.batch_payload(batch) if batch else None,
    }


def overview(db: Session) -> dict:
    account_count = int(db.execute(select(func.count(Account.id))).scalar() or 0)
    feature_count = int(db.execute(select(func.count(AccountFeature.id))).scalar() or 0)
    model_count = int(db.execute(select(func.count(ModelRun.id))).scalar() or 0)
    score_count = int(db.execute(select(func.count(ScoreBatch.id))).scalar() or 0)
    batch = score_service.active_batch(db)
    model = model_service.latest_model(db)
    churn_sum, churn_total = db.execute(
        select(func.coalesce(func.sum(AccountFeature.churn_next_30d), 0), func.count(AccountFeature.id))
    ).one()
    owner_rows = db.execute(
        select(Account.csm_owner_name, func.count(Account.id)).group_by(Account.csm_owner_name)
    ).all()
    stats = feature_service.feature_statistics(db)
    return {
        "brand": "churnmod",
        "accounts": account_count,
        "feature_rows": feature_count,
        "model_count": model_count,
        "score_count": score_count,
        "churn_rate": round(int(churn_sum) / int(churn_total), 4) if churn_total else 0.0,
        "churn_positive_rows": int(churn_sum),
        "latest_model": model_service.model_payload(model) if model else None,
        "active_batch": score_service.batch_payload(batch) if batch else None,
        # 兼容旧前端字段名。
        "latest_batch": score_service.batch_payload(batch) if batch else None,
        "owners": [{"name": name, "accounts": int(count)} for name, count in owner_rows],
        "top_features": stats["features"][:5],
        "months": stats.get("months", []),
        "target": "churn_next_30d",
        "target_label": "未来 30 天是否流失",
        "role_scope": "CSM 仅能看到自己名下的客户名单",
    }
