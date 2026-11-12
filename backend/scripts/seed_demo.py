"""Idempotent demo seed for 安澜云服务客户流失评分台.

Scene (batch-plan gb-576):
  240 SaaS accounts · 1,200 monthly feature rows (2026-07 ~ 2026-11)
  1 trained logistic-regression model (seed:baseline-lr)
  1 score batch at threshold 0.35 / budget ¥12,500 → Top-25 outreach list
  3 role accounts.

Every row is generated deterministically by ``src.services.fixture``. Re-running
upserts by natural keys (email / account code / account+month / feature-set name /
model label) and never overwrites user edits or new model/score batches. The
script ends with the machine readable line:

    SEED_SUMMARY brand=churnmod accounts=240 features=1200 models=1 scores=1 users=3
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from src.config.database import SessionLocal, init_db  # noqa: E402
from src.config.settings import settings  # noqa: E402
from src.constants.features import CATEGORICAL_KEYS, NUMERIC_KEYS  # noqa: E402
from src.constants.model_status import ModelStatus  # noqa: E402
from src.models.account import Account  # noqa: E402
from src.models.account_feature import AccountFeature  # noqa: E402
from src.models.feature_set import FeatureSet  # noqa: E402
from src.models.model_run import ModelRun  # noqa: E402
from src.models.score_batch import ScoreBatch  # noqa: E402
from src.models.user import User  # noqa: E402
from src.constants.score_lifecycle import ScoreLifecycle  # noqa: E402
from src.services import auth_service, model_service, score_service  # noqa: E402
from src.services.fixture import (  # noqa: E402
    TRAIN_MONTHS,
    VALIDATION_MONTH,
    build_dataset,
)
from src.utils.logger import log_event  # noqa: E402

DEMO_PASSWORD = "Demo@2026"
ACCOUNTS = (
    ("admin@churnmod.io", "顾襄", "admin", "客户成功负责人：特征 / 参数 / 阈值发布"),
    ("analyst@churnmod.io", "沈砚", "analyst", "数据分析师：训练 / 评估 / 调参"),
    ("csm@churnmod.io", "林知远", "csm", "客户成功经理：只读自己客户名单与原因"),
)
FEATURE_SET_NAME = "churn-baseline-v1"
SEED_MODEL_LABEL = "seed:baseline-lr"
SEED_SCORE_LABEL = "score-1"
SUMMARY_KEYS = ("accounts", "features", "models", "scores", "users")


def _get_or_create(db, model, predicate, values):
    row = db.execute(select(model).where(predicate)).scalar_one_or_none()
    if row is not None:
        return row, False
    row = model(**values)
    db.add(row)
    db.flush()
    return row, True


def _seed_users(db) -> None:
    for email, display_name, role, _note in ACCOUNTS:
        _get_or_create(
            db,
            User,
            User.email == email,
            {
                "email": email,
                "display_name": display_name,
                "role": role,
                "password_hash": auth_service.hash_password(DEMO_PASSWORD),
            },
        )
    db.commit()


def _seed_accounts(db, dataset: dict) -> dict[str, Account]:
    mapping: dict[str, Account] = {}
    for account in dataset["accounts"]:
        row, _ = _get_or_create(
            db,
            Account,
            Account.code == account["code"],
            {
                "code": account["code"],
                "company_name": account["company_name"],
                "industry": account["industry"],
                "plan": account["plan"],
                "region": account["region"],
                "seats": account["seats"],
                "monthly_fee": account["monthly_fee"],
                "csm_owner_email": account["csm_owner_email"],
                "csm_owner_name": account["csm_owner_name"],
                "contract_end": account["contract_end"],
                "status": account["status"],
                "churn_date": account["churn_date"],
            },
        )
        mapping[account["code"]] = row
    db.commit()
    return mapping


def _seed_features(db, dataset: dict, accounts: dict[str, Account]) -> int:
    inserted = 0
    for row in dataset["feature_rows"]:
        account = accounts.get(row["account_code"])
        if account is None:
            continue
        exists = db.execute(
            select(AccountFeature.id).where(
                AccountFeature.account_id == account.id,
                AccountFeature.month == row["month"],
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        db.add(
            AccountFeature(
                account_id=account.id,
                month=row["month"],
                month_label=row["month_label"],
                features=row["features"],
                churn_next_30d=row["churn_next_30d"],
                label_known=1,
            )
        )
        inserted += 1
    db.commit()
    return inserted


def _seed_feature_set(db) -> FeatureSet:
    row, _ = _get_or_create(
        db,
        FeatureSet,
        FeatureSet.name == FEATURE_SET_NAME,
        {
            "name": FEATURE_SET_NAME,
            "version": 1,
            "description": "基线特征集：12 个用量/工单/账单数值特征 + 行业/版本/区域 one-hot，目标为未来 30 天流失",
            "target": "churn_next_30d",
            "train_months": list(TRAIN_MONTHS),
            "validation_month": VALIDATION_MONTH,
            "numeric_keys": list(NUMERIC_KEYS),
            "categorical_keys": list(CATEGORICAL_KEYS),
            "status": "active",
            "created_by": "seed@churnmod.io",
        },
    )
    db.commit()
    return row


def _seed_model(db) -> ModelRun:
    existing = db.execute(select(ModelRun).where(ModelRun.label == SEED_MODEL_LABEL)).scalar_one_or_none()
    if existing is not None and existing.status == ModelStatus.SUCCEEDED.value:
        return existing
    if existing is not None:
        db.delete(existing)
        db.commit()
    run = model_service.create_model_run(
        db,
        actor_email="seed@churnmod.io",
        label=SEED_MODEL_LABEL,
        hyperparams={"learning_rate": 0.15, "l2": 0.02, "epochs": 1800},
        dispatch=False,
    )
    outcome = model_service.execute_train(db, run.id)
    if not outcome.get("ok"):
        raise RuntimeError(f"seed training failed: {outcome.get('error')}")
    return model_service.get_model(db, run.id)


def _seed_score_batch(db, model: ModelRun) -> ScoreBatch:
    existing = db.execute(select(ScoreBatch).where(ScoreBatch.label == SEED_SCORE_LABEL)).scalar_one_or_none()
    if existing is not None:
        return existing
    batch, _reused = score_service.create_score_batch(
        db,
        actor_email="seed@churnmod.io",
        threshold=settings.DEFAULT_THRESHOLD,
        budget_total=settings.DEFAULT_BUDGET,
        cost_per_account=settings.COST_PER_ACCOUNT,
        retention_lift=settings.EXPECTED_RETENTION_LIFT,
        model_run_id=model.id,
    )
    return batch


def _ensure_seed_policy_active(db, batch: ScoreBatch) -> None:
    """种子批次作为系统的第一个现行策略（v1）；已存在现行策略时不抢占。"""
    if batch.lifecycle == ScoreLifecycle.ACTIVE:
        return
    if score_service.active_batch(db) is not None:
        return
    score_service.publish_batch(db, batch.id, "seed@churnmod.io")


def _summary(db) -> dict:
    return {
        "accounts": int(db.execute(select(func.count(Account.id))).scalar() or 0),
        "features": int(db.execute(select(func.count(AccountFeature.id))).scalar() or 0),
        "models": int(db.execute(select(func.count(ModelRun.id))).scalar() or 0),
        "scores": int(db.execute(select(func.count(ScoreBatch.id))).scalar() or 0),
        "users": int(db.execute(select(func.count(User.id))).scalar() or 0),
    }


def run_seed() -> dict:
    init_db()
    db = SessionLocal()
    try:
        dataset = build_dataset()
        _seed_users(db)
        accounts = _seed_accounts(db, dataset)
        inserted = _seed_features(db, dataset, accounts)
        _seed_feature_set(db)
        model = _seed_model(db)
        score_batch = _seed_score_batch(db, model)
        _ensure_seed_policy_active(db, score_batch)
        summary = _summary(db)
        line = "SEED_SUMMARY brand=churnmod " + " ".join(f"{key}={summary[key]}" for key in SUMMARY_KEYS)
        print(line, flush=True)
        log_event("SEED_SUMMARY", **summary, inserted_features=inserted)
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
