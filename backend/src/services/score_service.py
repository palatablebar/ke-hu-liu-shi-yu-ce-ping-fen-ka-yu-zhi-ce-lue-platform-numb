"""Scoring, risk banding, budget-constrained selection and CSV export.

策略生命周期（与 ``constants/score_lifecycle.py`` 对应）：

    draft（草稿） → active（现行策略，全局唯一） → archived（历史版本，只留不生效）

- 新建批次永远是草稿，不影响风险图与导出；
- 风险名单与导出名单统一读取 :func:`active_batch`；
- 发布在单个事务 + 行锁内完成「旧版本归档 / 新版本生效」，失败整体回滚；
- 同模型同参数（policy_fingerprint）重复执行直接复用既有草稿/现行批次，不新增版本。
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.algorithms.logistic import apply_standardizer, build_dataset, contribution_reasons, predict_proba
from src.algorithms.risk_bands import build_results
from src.constants.features import FEATURE_LABELS
from src.constants.messages import (
    MSG_POLICY_DRAFT_ONLY,
    MSG_POLICY_LOCKED,
    MSG_POLICY_NOT_ACTIVE,
    MSG_SCORE_INVALID,
    MSG_SCORE_NOT_FOUND,
)
from src.constants.risk_band import RISK_BAND_LABELS
from src.constants.score_lifecycle import ScoreLifecycle
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


def policy_fingerprint(
    *,
    model_run_id: int,
    threshold: float,
    budget_total: float,
    cost_per_account: float,
    retention_lift: float,
) -> str:
    """同一模型 + 同一组策略参数的确定性指纹（参数按固定精度归一，避免浮点尾差）。"""
    raw = "|".join(
        [
            f"model={model_run_id}",
            f"threshold={float(threshold):.6f}",
            f"budget={float(budget_total):.2f}",
            f"cost={float(cost_per_account):.2f}",
            f"lift={float(retention_lift):.6f}",
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def create_score_batch(
    db: Session,
    *,
    actor_email: str,
    threshold: float,
    budget_total: float,
    cost_per_account: float,
    retention_lift: float,
    model_run_id: int | None = None,
) -> tuple[ScoreBatch, bool]:
    """生成评分草稿。

    返回 ``(batch, reused)``：同一策略已存在（草稿或现行）时直接复用、不新增版本，
    ``reused=True``。整个过程一个事务，任何失败都回滚，不留半成品草稿。
    """
    if threshold <= 0 or threshold >= 1 or budget_total <= 0 or cost_per_account <= 0:
        raise HTTPException(status_code=422, detail=MSG_SCORE_INVALID)
    model = db.get(ModelRun, model_run_id) if model_run_id else model_service.latest_model(db)
    if model is None:
        raise HTTPException(status_code=409, detail="没有可用的训练批次，请先训练模型")
    feature_set = db.get(FeatureSet, model.feature_set_id)
    if feature_set is None:
        raise HTTPException(status_code=409, detail="训练批次缺少特征集")

    fingerprint = policy_fingerprint(
        model_run_id=model.id,
        threshold=threshold,
        budget_total=budget_total,
        cost_per_account=cost_per_account,
        retention_lift=retention_lift,
    )
    # 幂等：同一策略在草稿/现行版本里已存在则直接返回；历史归档不参与复用。
    existing = db.execute(
        select(ScoreBatch).where(
            ScoreBatch.policy_fingerprint == fingerprint,
            ScoreBatch.lifecycle != ScoreLifecycle.ARCHIVED,
        )
    ).scalar_one_or_none()
    if existing is not None:
        log_event(
            "SCORE_BATCH_REUSED",
            batch_id=existing.id,
            batch_no=existing.batch_no,
            lifecycle=existing.lifecycle,
            actor=actor_email,
        )
        return existing, True

    try:
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
            lifecycle=ScoreLifecycle.DRAFT,
            policy_fingerprint=fingerprint,
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
        db.flush()  # 让部分唯一索引有机会拦截并发下的重复指纹
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        # 并发请求同时算出同一指纹：赢家已落库，回滚后复用赢家，仍然不新增版本。
        db.rollback()
        winner = db.execute(
            select(ScoreBatch).where(
                ScoreBatch.policy_fingerprint == fingerprint,
                ScoreBatch.lifecycle != ScoreLifecycle.ARCHIVED,
            )
        ).scalar_one_or_none()
        if winner is not None:
            log_event("SCORE_BATCH_REUSED_RACE", batch_id=winner.id, actor=actor_email)
            return winner, True
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(batch)
    log_event(
        "SCORE_BATCH_CREATED",
        batch_id=batch.id,
        batch_no=batch.batch_no,
        selected=batch.selected_count,
        actor=actor_email,
    )
    return batch, False


def batch_payload(batch: ScoreBatch | None, include_results: bool = False) -> dict | None:
    if batch is None:
        return None
    payload = {
        "id": batch.id,
        "batch_no": batch.batch_no,
        "label": batch.label,
        "model_run_id": batch.model_run_id,
        "status": batch.status,
        "lifecycle": batch.lifecycle,
        "policy_version": batch.policy_version,
        "superseded_by": batch.superseded_by,
        "policy_fingerprint": batch.policy_fingerprint,
        "threshold": batch.threshold,
        "budget_total": batch.budget_total,
        "cost_per_account": batch.cost_per_account,
        "retention_lift": batch.retention_lift,
        "bands": batch.bands,
        "summary": batch.summary,
        "selected_count": batch.selected_count,
        # 兼容旧前端字段：曾经发布过（现行或历史）即为 True。
        "published": batch.lifecycle in (ScoreLifecycle.ACTIVE, ScoreLifecycle.ARCHIVED),
        "is_active": batch.lifecycle == ScoreLifecycle.ACTIVE,
        "published_by": batch.published_by,
        "published_at": batch.published_at.isoformat(sep=" ", timespec="seconds") if batch.published_at else None,
        "created_by": batch.created_by,
        "created_at": batch.created_at.isoformat(sep=" ", timespec="seconds") if batch.created_at else None,
    }
    if include_results:
        payload["results"] = batch.results or []
    return payload


def active_batch(db: Session) -> ScoreBatch | None:
    """全局唯一的现行策略；风险名单与导出名单都只能跟随它。"""
    return db.execute(
        select(ScoreBatch).where(ScoreBatch.lifecycle == ScoreLifecycle.ACTIVE).limit(1)
    ).scalars().first()


def get_batch(db: Session, batch_id: int) -> ScoreBatch:
    batch = db.get(ScoreBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=MSG_SCORE_NOT_FOUND)
    return batch


def list_batches(db: Session, limit: int = 20) -> list[dict]:
    rows = db.execute(select(ScoreBatch).order_by(ScoreBatch.id.desc()).limit(limit)).scalars().all()
    return [batch_payload(row) for row in rows]


def export_csv(db: Session, batch_id: int | None = None, owner_email: str | None = None) -> tuple[str, str]:
    """导出现行策略名单。指定非现行批次一律拒绝，避免旧版本名单继续外流。"""
    if batch_id is None:
        batch = active_batch(db)
        if batch is None:
            raise HTTPException(status_code=409, detail="还没有现行策略，请先发布一个草稿")
    else:
        batch = get_batch(db, batch_id)
        if batch.lifecycle != ScoreLifecycle.ACTIVE:
            raise HTTPException(status_code=409, detail=MSG_POLICY_NOT_ACTIVE)
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
    return to_csv(CSV_COLUMNS, payload), f"churnmod_policy_v{batch.policy_version}_top{len(payload)}.csv"


def _reason_text(reasons: list[dict], index: int) -> str:
    if index >= len(reasons):
        return ""
    reason = reasons[index]
    label = FEATURE_LABELS.get(reason["feature"], reason.get("label", reason["feature"]))
    return f"{label}={reason['raw_value']}（贡献 {reason['contribution']:+.3f}）"


def publish_batch(db: Session, batch_id: int, actor_email: str) -> dict:
    """一次性完成策略切换。

    单事务 + ``FOR UPDATE`` 行锁 + 部分唯一索引三重保证：

    1. 草稿 → 现行策略，分配单调递增的策略版本号；
    2. 旧现行策略 → 历史版本（archived），记录接替者，永久保留但不再生效；
    3. 两位负责人并发发布时，后到者等待先到者提交，绝不可能出现两个现行版本；
    4. 任何一步失败整体回滚，现行策略保持切换前状态，不留半成品。
    """
    try:
        # 锁定候选草稿行；并发发布会在这把行锁上串行化。
        batch = db.execute(
            select(ScoreBatch).where(ScoreBatch.id == batch_id).with_for_update()
        ).scalar_one_or_none()
        if batch is None:
            raise HTTPException(status_code=404, detail=MSG_SCORE_NOT_FOUND)

        if batch.lifecycle == ScoreLifecycle.ACTIVE:
            # 幂等：现行策略重复发布不做任何变更，直接返回当前切换结果。
            db.rollback()
            return _switch_result(db, batch, previous=None, switched=False, reason="already_active")
        if batch.lifecycle == ScoreLifecycle.ARCHIVED:
            raise HTTPException(status_code=409, detail=MSG_POLICY_LOCKED)
        if batch.lifecycle != ScoreLifecycle.DRAFT:
            raise HTTPException(status_code=409, detail=MSG_POLICY_DRAFT_ONLY)

        previous = db.execute(
            select(ScoreBatch)
            .where(ScoreBatch.lifecycle == ScoreLifecycle.ACTIVE)
            .with_for_update()
        ).scalars().first()

        next_version = int(
            db.execute(
                select(func.coalesce(func.max(ScoreBatch.policy_version), 0)).where(
                    ScoreBatch.policy_version.isnot(None)
                )
            ).scalar()
            or 0
        ) + 1

        now = datetime.now()
        batch.lifecycle = ScoreLifecycle.ACTIVE
        batch.policy_version = next_version
        batch.published = True
        batch.published_by = actor_email
        batch.published_at = now

        previous_payload = None
        if previous is not None:
            previous.lifecycle = ScoreLifecycle.ARCHIVED
            previous.superseded_by = batch.id
            previous_payload = batch_payload(previous)

        db.flush()  # 触发 uq_score_batches_active_one 校验（双活在库层也插不进去）
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        log_event("SCORE_POLICY_SWITCH_CONFLICT", batch_id=batch_id, actor=actor_email, error=str(exc))
        from src.constants.messages import MSG_POLICY_SWITCH_FAILED

        raise HTTPException(status_code=409, detail=MSG_POLICY_SWITCH_FAILED)
    except Exception:
        db.rollback()
        raise

    db.refresh(batch)
    log_event(
        "SCORE_POLICY_PUBLISHED",
        batch_id=batch.id,
        policy_version=batch.policy_version,
        previous_batch_id=previous_payload["id"] if previous_payload else None,
        actor=actor_email,
        threshold=batch.threshold,
    )
    return _switch_result(db, batch, previous=previous_payload, switched=True, reason="switched")


def _switch_result(
    db: Session,
    batch: ScoreBatch,
    *,
    previous: dict | None,
    switched: bool,
    reason: str,
) -> dict:
    return {
        "switched": switched,
        "reason": reason,
        "active": batch_payload(batch),
        "previous": previous,
        "active_count": int(
            db.execute(
                select(func.count(ScoreBatch.id)).where(ScoreBatch.lifecycle == ScoreLifecycle.ACTIVE)
            ).scalar()
            or 0
        ),
    }


def policy_diff(db: Session, candidate_id: int) -> dict:
    """候选草稿/任意批次相对现行策略的参数与名单差异，供页面展示「候选差异」。"""
    candidate = get_batch(db, candidate_id)
    current = active_batch(db)
    candidate_payload = batch_payload(candidate)
    current_payload = batch_payload(current) if current else None

    param_keys = ("threshold", "budget_total", "cost_per_account", "retention_lift")
    param_changes = []
    for key in param_keys:
        old_value = getattr(current, key) if current else None
        new_value = getattr(candidate, key)
        param_changes.append(
            {
                "field": key,
                "current": old_value,
                "candidate": new_value,
                "changed": (old_value is None) or (float(old_value) != float(new_value)),
            }
        )

    current_rows = {row["account_code"]: row for row in (current.results or [])} if current else {}
    candidate_rows = {row["account_code"]: row for row in (candidate.results or [])}

    def selected(codes_map: dict) -> set[str]:
        return {code for code, row in codes_map.items() if row.get("selected")}

    def high_risk(codes_map: dict) -> set[str]:
        return {code for code, row in codes_map.items() if row.get("band") == "high"}

    current_selected, candidate_selected = selected(current_rows), selected(candidate_rows)
    current_high, candidate_high = high_risk(current_rows), high_risk(candidate_rows)

    added, removed = [], []
    for code in sorted(candidate_selected - current_selected):
        row = candidate_rows[code]
        added.append(
            {
                "account_code": code,
                "company_name": row.get("company_name", ""),
                "score": row.get("score"),
                "rank": row.get("rank"),
                "expected_save": row.get("expected_save"),
            }
        )
    for code in sorted(current_selected - candidate_selected):
        row = current_rows[code]
        removed.append(
            {
                "account_code": code,
                "company_name": row.get("company_name", ""),
                "score": row.get("score"),
                "rank": row.get("rank"),
                "expected_save": row.get("expected_save"),
            }
        )

    score_moves = []
    for code in sorted(current_rows.keys() & candidate_rows.keys()):
        delta = round(float(candidate_rows[code]["score"]) - float(current_rows[code]["score"]), 6)
        if abs(delta) >= 0.01:
            score_moves.append(
                {
                    "account_code": code,
                    "company_name": candidate_rows[code].get("company_name", ""),
                    "current_score": current_rows[code]["score"],
                    "candidate_score": candidate_rows[code]["score"],
                    "delta": delta,
                }
            )

    return {
        "candidate": candidate_payload,
        "current": current_payload,
        "param_changes": param_changes,
        "summary": {
            "current_high_risk": len(current_high),
            "candidate_high_risk": len(candidate_high),
            "high_risk_added": len(candidate_high - current_high),
            "high_risk_removed": len(current_high - candidate_high),
            "current_selected": len(current_selected),
            "candidate_selected": len(candidate_selected),
            "selected_added": len(added),
            "selected_removed": len(removed),
            "score_moves": len(score_moves),
        },
        "selected_added": added,
        "selected_removed": removed,
        "score_moves": score_moves[:50],
    }


def band_distribution(batch: ScoreBatch) -> dict:
    return {
        band: RISK_BAND_LABELS.get(band, band) for band in (row.get("band") for row in (batch.results or [])) if band
    }
