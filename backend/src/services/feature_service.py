"""Feature catalogue, statistics and correlations (real numbers from account_features)."""
from __future__ import annotations

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.features import (
    CATEGORICAL_FEATURES,
    FEATURE_LABELS,
    NUMERIC_FEATURES,
    TARGET_LABEL,
)
from src.models.account_feature import AccountFeature
from src.models.feature_set import FeatureSet


def list_feature_sets(db: Session) -> list[dict]:
    rows = db.execute(select(FeatureSet).order_by(FeatureSet.id)).scalars().all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "version": row.version,
            "description": row.description,
            "target": row.target,
            "train_months": row.train_months,
            "validation_month": row.validation_month,
            "numeric_keys": row.numeric_keys,
            "categorical_keys": row.categorical_keys,
            "status": row.status,
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else None,
        }
        for row in rows
    ]


def feature_statistics(db: Session, month_label: str | None = None) -> dict:
    query = select(AccountFeature)
    if month_label:
        query = query.where(AccountFeature.month_label == month_label)
    rows = db.execute(query).scalars().all()
    if not rows:
        return {"rows": 0, "features": [], "categoricals": CATEGORICAL_FEATURES, "target": TARGET_LABEL}

    labels = np.asarray([row.churn_next_30d for row in rows], dtype=np.float64)
    statistics = []
    for feature in NUMERIC_FEATURES:
        values = np.asarray([float((row.features or {}).get(feature["key"], 0.0)) for row in rows], dtype=np.float64)
        std = float(values.std())
        correlation = 0.0
        if std > 1e-9 and labels.std() > 1e-9:
            correlation = float(np.corrcoef(values, labels)[0, 1])
        statistics.append(
            {
                "key": feature["key"],
                "label": feature["label"],
                "unit": feature["unit"],
                "direction": feature["direction"],
                "description": feature["description"],
                "mean": round(float(values.mean()), 4),
                "std": round(std, 4),
                "min": round(float(values.min()), 4),
                "max": round(float(values.max()), 4),
                "missing": int(sum(1 for row in rows if (row.features or {}).get(feature["key"]) in (None, ""))),
                "correlation": round(correlation, 4),
            }
        )
    statistics.sort(key=lambda item: abs(item["correlation"]), reverse=True)

    categorical_stats = []
    for feature in CATEGORICAL_FEATURES:
        key = feature["key"]
        counts = {value: 0 for value in feature["values"]}
        positives = {value: 0 for value in feature["values"]}
        for row in rows:
            value = str((row.features or {}).get(key, ""))
            if value in counts:
                counts[value] += 1
                positives[value] += int(row.churn_next_30d)
        categorical_stats.append(
            {
                "key": key,
                "label": feature["label"],
                "values": [
                    {
                        "value": value,
                        "count": counts[value],
                        "churn_rate": round(positives[value] / counts[value], 4) if counts[value] else 0.0,
                    }
                    for value in feature["values"]
                ],
            }
        )

    positives = int(labels.sum())
    return {
        "rows": len(rows),
        "target": TARGET_LABEL,
        "target_label": TARGET_LABEL,
        "positive_count": positives,
        "positive_rate": round(positives / len(rows), 4),
        "features": statistics,
        "categoricals": categorical_stats,
        "labels": FEATURE_LABELS,
        "months": sorted({row.month_label for row in rows}),
    }


def feature_set_definition(db: Session) -> dict:
    """Definitions + statistics for the active feature set (used by the design panel)."""
    active = (
        db.execute(select(FeatureSet).where(FeatureSet.status == "active").order_by(FeatureSet.id.desc()))
        .scalars()
        .first()
    )
    if active is None:
        return {"feature_set": None, "statistics": feature_statistics(db)}
    statistics = feature_statistics(db, active.validation_month)
    return {
        "feature_set": next(item for item in list_feature_sets(db) if item["id"] == active.id),
        "statistics": statistics,
        "catalog": {"numeric": NUMERIC_FEATURES, "categorical": CATEGORICAL_FEATURES},
        "counts": {
            "accounts": int(
                db.execute(select(func.count(func.distinct(AccountFeature.account_id)))).scalar() or 0
            ),
            "rows": int(db.execute(select(func.count(AccountFeature.id))).scalar() or 0),
        },
    }
