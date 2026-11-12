"""Scoring, risk banding, budget-constrained selection and CSV export."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.algorithms.logistic import apply_standardizer, build_dataset, contribution_reasons, predict_proba
from src.algorithms.risk_bands import build_results
from src.constants.features import FEATURE_LABELS
from src.constants.messages import MSG_SCORE_INVALID, MSG_SCORE_NOT_FOUND
from src.constants.risk_band import RISK_BAND_LABELS
from src.models.account import Account
from src.models.account_feature import AccountFeature
from src.models.feature_set import FeatureSet
from src.models.model_run import ModelRun
from src.models.score_batch import ScoreBatch
from src.services import model_service
from src.utils.csv_export import to_csv
from src.utils.logger import log_event

CSV_COLUMNS = (
    "rank",
    "account_code",
    "company_name",
    "industry",
    "plan",
    "region",
    "csm_owner_name",
    "monthly_fee",
    "score",
    "band_label",
    "lift",
    "expected_save",
    "reason_1",
    "reason_2",
    "reason_3",
)


def _score_records(model: ModelRun, records: list[dict]) -> list:
    import numpy as np

    numeric_keys = list(model.standardization["names"])
    dataset = build_dataset(records, [key for key in numeric_keys if "=" not in key], [])
    standardized = apply_standardizer(dataset.matrix, model.standardization)
    weights = np.asarray(
        [item["coefficient"] for item in model.coefficients if item["group"] != "intercept"], dtype=float
    )
    bias = float(model.standardization.get("bias", 0.0))
    return predict_proba(standardized, weights, bias), dataset


def _feature_rows_for_scoring(db: Session, feature_set: FeatureSet, model: ModelRun) -> list[dict]:
    month = feature_set.validation_month
    rows = db.execute(
        select(AccountFeature, Account)
        .join(Account, Account.id == AccountFeature.account_id)
        .where(AccountFeature.month_label == month)
        .order_by(Account.code)
    ).all()
    records = []
    for feature_row, account in rows:
        records.append(
            {
                "account": account,
                "account_code": account.code,
                "month_label": feature_row.month_label,
                "features": feature_row.features,
                "churn_next_30d": feature_row.churn_next_30d,
            }
        )
    return records


def _scored_items(model: ModelRun, records: list[dict], feature_set: FeatureSet) -> tuple[list[dict], object]:
    base_records = [{"features": record["features"], "churn_next_30d": record["churn_next_30d"]} for record in records]
    columns = list(model.standardization["names"])
    numeric_keys = [name for name in columns if "=" not in name]
    categorical_keys = list(feature_set.categorical_keys)
    dataset = build_dataset(base_records, numeric_keys, categorical_keys)
    import numpy as np

    standardized = apply_standardizer(dataset.matrix, model.standardization)
    weights = np.asarray(
        [item["coefficient"] for item in model.coefficients if item["group"] != "intercept"], dtype=float
    )
    scores = predict_proba(standardized, weights, float(model.standardization.get("bias", 0.0)))
    items = []
    for record, score in zip(records, scores):
        reasons = contribution_reasons(
            {"features": record["features"]},
            model.coefficients,
            model.standardization,
            top_n=3,
        )
        account = record["account"]
        items.append(
            {
                "account_code": account.code,
                "company_name": account.company_name,
                "industry": account.industry,
                "plan": account.plan,
                "region": account.region,
                "csm_owner_email": account.csm_owner_email,
                "csm_owner_name": account.csm_owner_name,
                "seats": account.seats,
                "monthly_fee": float(account.monthly_fee),
                "score": round(float(score), 6),
                "actual_churn": int(record["churn_next_30d"]),
                "reasons": reasons,
            }
        )
    return items, scores


def create_score_batch(
    db: Session,
    *,
    actor_email: str,
    threshold: float,
    budget_total: float,
    cost_per_account: float,
    retention_lift: float,
    model_run_id: int | None = None,
) -> ScoreBatch:
    if threshold <= 0 or threshold >= 1 or budget_total <= 0 or cost_per_account <= 0:
        raise HTTPException(status_code=422, detail=MSG_SCORE_INVALID)
    model = db.get(ModelRun, model_run_id) if model_run_id else model_service.latest_model(db)
    if model is None:
        raise HTTPException(status_code=409, detail="没有可用的训练批次，请先训练模型")
    feature_set = db.get(FeatureSet, model.feature_set_id)
    if feature_set is None:
        raise HTTPException(status_code=409, detail="训练批次缺少特征集")

    records = _feature_rows_for_scoring(db, feature_set, model)
    if not records:
        raise HTTPException(status_code=409, detail="验证月没有可评分的客户特征")
    items, _scores = _scored_items(model, records, feature_set)

    from src.algorithms.risk_bands import band_cuts

    cuts = band_cuts([item["score"] for item in items])
    results, summary = build_results(items, cuts, threshold, budget_total, cost_per_account, retention_lift)

    batch_no = int(db.execute(select(func.max(ScoreBatch.batch_no))).scalar() or 0) + 1
    batch = ScoreBatch(
        batch_no=batch_no,
        label=f"score-{batch_no}",
        model_run_id=model.id,
        status="succeeded",
        threshold=threshold,
        budget_total=budget_total,
        cost_per_account=cost_per_account,
        retention_lift=retention_lift,
        bands=cuts,
        summary={**summary, "account_rows": len(results), "model_auc": model.metrics.get("auc", 0.0)},
        results=results,
        selected_count=summary["selected_count"],
        created_by=actor_email,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    log_event("SCORE_BATCH_CREATED", batch_id=batch.id, batch_no=batch.batch_no, selected=batch.selected_count)
    return batch


def batch_payload(batch: ScoreBatch, include_results: bool = False) -> dict:
    payload = {
        "id": batch.id,
        "batch_no": batch.batch_no,
        "label": batch.label,
        "model_run_id": batch.model_run_id,
        "status": batch.status,
        "threshold": batch.threshold,
        "budget_total": batch.budget_total,
        "cost_per_account": batch.cost_per_account,
        "retention_lift": batch.retention_lift,
        "bands": batch.bands,
        "summary": batch.summary,
        "selected_count": batch.selected_count,
        "published": batch.published,
        "published_by": batch.published_by,
        "published_at": batch.published_at.isoformat(sep=" ", timespec="seconds") if batch.published_at else None,
        "created_by": batch.created_by,
        "created_at": batch.created_at.isoformat(sep=" ", timespec="seconds") if batch.created_at else None,
    }
    if include_results:
        payload["results"] = batch.results or []
    return payload


def latest_batch(db: Session) -> ScoreBatch | None:
    return db.execute(select(ScoreBatch).order_by(ScoreBatch.id.desc()).limit(1)).scalars().first()


def get_batch(db: Session, batch_id: int) -> ScoreBatch:
    batch = db.get(ScoreBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=MSG_SCORE_NOT_FOUND)
    return batch


def list_batches(db: Session, limit: int = 20) -> list[dict]:
    rows = db.execute(select(ScoreBatch).order_by(ScoreBatch.id.desc()).limit(limit)).scalars().all()
    return [batch_payload(row) for row in rows]


def export_csv(db: Session, batch_id: int, owner_email: str | None = None) -> tuple[str, str]:
    batch = get_batch(db, batch_id)
    rows = batch.results or []
    if owner_email:
        rows = [row for row in rows if row.get("csm_owner_email") == owner_email and row.get("selected")]
    else:
        rows = [row for row in rows if row.get("selected")]
    ranked = sorted(rows, key=lambda row: row.get("rank") or 10_000)
    payload = []
    for row in ranked:
        reasons = row.get("reasons") or []
        payload.append(
            {
                "rank": row.get("rank", ""),
                "account_code": row.get("account_code", ""),
                "company_name": row.get("company_name", ""),
                "industry": row.get("industry", ""),
                "plan": row.get("plan", ""),
                "region": row.get("region", ""),
                "csm_owner_name": row.get("csm_owner_name", ""),
                "monthly_fee": row.get("monthly_fee", ""),
                "score": row.get("score", ""),
                "band_label": row.get("band_label", ""),
                "lift": row.get("lift", ""),
                "expected_save": row.get("expected_save", ""),
                "reason_1": _reason_text(reasons, 0),
                "reason_2": _reason_text(reasons, 1),
                "reason_3": _reason_text(reasons, 2),
            }
        )
    return to_csv(CSV_COLUMNS, payload), f"churnmod_{batch.label}_top{len(payload)}.csv"


def _reason_text(reasons: list[dict], index: int) -> str:
    if index >= len(reasons):
        return ""
    reason = reasons[index]
    label = FEATURE_LABELS.get(reason["feature"], reason.get("label", reason["feature"]))
    return f"{label}={reason['raw_value']}（贡献 {reason['contribution']:+.3f}）"


def publish_batch(db: Session, batch_id: int, actor_email: str) -> dict:
    batch = get_batch(db, batch_id)
    if batch.published:
        from src.constants.messages import MSG_POLICY_LOCKED

        raise HTTPException(status_code=409, detail=MSG_POLICY_LOCKED)
    batch.published = True
    batch.published_by = actor_email
    batch.published_at = datetime.now()
    db.commit()
    db.refresh(batch)
    log_event("SCORE_POLICY_PUBLISHED", batch_id=batch.id, actor=actor_email, threshold=batch.threshold)
    return batch_payload(batch)


def band_distribution(batch: ScoreBatch) -> dict:
    return {
        band: RISK_BAND_LABELS.get(band, band) for band in (row.get("band") for row in (batch.results or [])) if band
    }
