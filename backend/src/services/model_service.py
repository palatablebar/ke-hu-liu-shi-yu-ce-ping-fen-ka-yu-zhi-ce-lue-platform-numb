"""Training orchestration: feature-set load, time split, LR pipeline, batch persistence."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.algorithms.logistic import train_pipeline
from src.config.celery_app import celery_app
from src.constants.messages import MSG_MODEL_NOT_FOUND, MSG_TRAIN_BUSY
from src.constants.model_status import ModelStatus
from src.models.account_feature import AccountFeature
from src.models.feature_set import FeatureSet
from src.models.model_run import ModelRun
from src.utils.logger import log_event


def model_payload(run: ModelRun) -> dict:
    return {
        "id": run.id,
        "run_no": run.run_no,
        "label": run.label,
        "feature_set_id": run.feature_set_id,
        "status": run.status,
        "hyperparams": run.hyperparams,
        "coefficients": run.coefficients,
        "metrics": run.metrics,
        "roc_points": run.roc_points,
        "pr_points": run.pr_points,
        "threshold_scan": run.threshold_scan,
        "standardization": run.standardization,
        "train_rows": run.train_rows,
        "validation_rows": run.validation_rows,
        "train_positives": run.train_positives,
        "warning": run.warning,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat(sep=" ", timespec="seconds") if run.started_at else None,
        "finished_at": run.finished_at.isoformat(sep=" ", timespec="seconds") if run.finished_at else None,
        "created_by": run.created_by,
        "created_at": run.created_at.isoformat(sep=" ", timespec="seconds") if run.created_at else None,
    }


def latest_model(db: Session) -> ModelRun | None:
    return (
        db.execute(
            select(ModelRun)
            .where(ModelRun.status == ModelStatus.SUCCEEDED.value)
            .order_by(ModelRun.id.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )


def get_model(db: Session, model_id: int) -> ModelRun:
    run = db.get(ModelRun, model_id)
    if run is None:
        raise HTTPException(status_code=404, detail=MSG_MODEL_NOT_FOUND)
    return run


def list_models(db: Session, limit: int = 20) -> list[dict]:
    rows = db.execute(select(ModelRun).order_by(ModelRun.id.desc()).limit(limit)).scalars().all()
    return [model_payload(row) for row in rows]


def next_run_no(db: Session) -> int:
    current = db.execute(select(func.max(ModelRun.run_no))).scalar()
    return int(current or 0) + 1


def create_model_run(
    db: Session,
    *,
    actor_email: str,
    label: str | None = None,
    hyperparams: dict | None = None,
    dispatch: bool = True,
) -> ModelRun:
    busy = db.execute(
        select(ModelRun).where(ModelRun.status.in_([ModelStatus.PENDING.value, ModelStatus.RUNNING.value]))
    ).scalar_one_or_none()
    if busy is not None:
        raise HTTPException(status_code=409, detail=MSG_TRAIN_BUSY)
    feature_set = (
        db.execute(select(FeatureSet).where(FeatureSet.status == "active").order_by(FeatureSet.id.desc()))
        .scalars()
        .first()
    )
    if feature_set is None:
        raise HTTPException(status_code=409, detail="没有启用中的特征集")
    run_no = next_run_no(db)
    run = ModelRun(
        run_no=run_no,
        label=label or f"model-{run_no}",
        feature_set_id=feature_set.id,
        status=ModelStatus.PENDING.value,
        hyperparams=hyperparams or {},
        created_by=actor_email,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    if dispatch:
        celery_app.send_task("churnmod.train_model", args=[run.id])
    log_event("MODEL_RUN_CREATED", run_id=run.id, run_no=run.run_no, actor=actor_email)
    return run


def _records(db: Session, months: list[str], feature_set: FeatureSet) -> list[dict]:
    rows = (
        db.execute(
            select(AccountFeature)
            .where(AccountFeature.month_label.in_(months))
            .order_by(AccountFeature.account_id, AccountFeature.month)
        )
        .scalars()
        .all()
    )
    return [
        {
            "account_id": row.account_id,
            "features": row.features,
            "churn_next_30d": row.churn_next_30d,
            "month_label": row.month_label,
        }
        for row in rows
    ]


def execute_train(db: Session, model_id: int) -> dict:
    run = db.get(ModelRun, model_id)
    if run is None:
        return {"ok": False, "error": "model run not found"}
    run.status = ModelStatus.RUNNING.value
    run.started_at = datetime.now()
    db.commit()
    try:
        feature_set = db.get(FeatureSet, run.feature_set_id)
        if feature_set is None:
            raise RuntimeError("feature set missing")
        hyperparams = {
            "learning_rate": float(run.hyperparams.get("learning_rate", 0.15)),
            "l2": float(run.hyperparams.get("l2", 0.02)),
            "epochs": int(run.hyperparams.get("epochs", 1800)),
        }
        train_records = _records(db, feature_set.train_months, feature_set)
        validation_records = _records(db, [feature_set.validation_month], feature_set)
        if not train_records or not validation_records:
            raise RuntimeError("训练或验证月份没有特征数据")

        outcome = train_pipeline(
            train_records,
            validation_records,
            list(feature_set.numeric_keys),
            list(feature_set.categorical_keys),
            hyperparams,
        )
        outcome.pop("validation_scores", None)
        outcome.pop("validation_records", None)
        run.coefficients = outcome["coefficients"]
        run.metrics = outcome["metrics"]
        run.roc_points = outcome["roc_points"]
        run.pr_points = outcome["pr_points"]
        run.threshold_scan = outcome["threshold_scan"]
        run.standardization = outcome["standardization"]
        run.train_rows = outcome["train_rows"]
        run.validation_rows = outcome["validation_rows"]
        run.train_positives = outcome["train_positives"]
        run.warning = outcome.get("warning", "")
        run.hyperparams = outcome["hyperparams"]
        run.status = ModelStatus.SUCCEEDED.value
        run.finished_at = datetime.now()
        db.commit()
        log_event(
            "MODEL_RUN_SUCCEEDED",
            run_id=run.id,
            auc=run.metrics.get("auc"),
            train_rows=run.train_rows,
            validation_rows=run.validation_rows,
        )
        return {"ok": True, "model_id": run.id, "metrics": run.metrics}
    except Exception as exc:
        db.rollback()
        run = db.get(ModelRun, model_id)
        if run is not None:
            run.status = ModelStatus.FAILED.value
            run.finished_at = datetime.now()
            run.error_message = f"{type(exc).__name__}: {exc}"[:500]
            db.commit()
        log_event("MODEL_RUN_FAILED", run_id=model_id, error=f"{type(exc).__name__}: {exc}")
        return {"ok": False, "error": str(exc)}
