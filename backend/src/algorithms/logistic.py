"""Hand-written logistic regression (numpy only, no scikit-learn).

Pipeline
--------
1. Design matrix: numeric features (as-is) + one-hot categorical features.
2. Standardisation fitted **only on the training months** (mean/std), then applied
   to the validation month — this is the leak guard for the time split.
3. Full-batch gradient descent with L2 penalty and deterministic zero init.
4. Evaluation: AUC by the trapezoid rule over the ROC curve, average-precision
   style PR AUC, confusion matrix, and a threshold scan over 0.10..0.90.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from src.constants.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from src.constants.model_status import MIN_POSITIVE_RATE
from src.constants.risk_band import SCAN_THRESHOLDS


def _trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    """np.trapz (numpy 1.x) / np.trapezoid (numpy 2.x) compatible."""
    function = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    return float(function(y, x))


@dataclass
class Dataset:
    matrix: np.ndarray
    labels: np.ndarray
    names: list[str]
    meta: list[dict]


def build_dataset(records: list[dict], numeric_keys: list[str], categorical_keys: list[str]) -> Dataset:
    numeric_meta = {feature["key"]: feature for feature in NUMERIC_FEATURES}
    categorical_meta = {feature["key"]: feature for feature in CATEGORICAL_FEATURES}
    names: list[str] = list(numeric_keys)
    for key in categorical_keys:
        for value in categorical_meta[key]["values"]:
            names.append(f"{key}={value}")

    rows: list[list[float]] = []
    labels: list[int] = []
    meta: list[dict] = []
    for record in records:
        features = record["features"]
        row: list[float] = []
        for key in numeric_keys:
            value = features.get(key, 0.0)
            try:
                row.append(float(value))
            except (TypeError, ValueError):
                row.append(0.0)
        for key in categorical_keys:
            current = str(features.get(key, ""))
            for value in categorical_meta[key]["values"]:
                row.append(1.0 if current == value else 0.0)
        rows.append(row)
        labels.append(int(record.get("churn_next_30d", 0)))
        meta.append(record)
    matrix = np.asarray(rows, dtype=np.float64)
    label_array = np.asarray(labels, dtype=np.float64)
    if matrix.size == 0:
        matrix = np.zeros((0, len(names)), dtype=np.float64)
    return Dataset(matrix=matrix, labels=label_array, names=names, meta=meta)


def fit_standardizer(matrix: np.ndarray) -> dict[str, list[float]]:
    if matrix.shape[0] == 0:
        return {"mean": [0.0] * matrix.shape[1], "std": [1.0] * matrix.shape[1]}
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    return {"mean": mean.tolist(), "std": std.tolist()}


def apply_standardizer(matrix: np.ndarray, params: dict[str, list[float]]) -> np.ndarray:
    mean = np.asarray(params["mean"], dtype=np.float64)
    std = np.asarray(params["std"], dtype=np.float64)
    return (matrix - mean) / std


def train_logistic(
    matrix: np.ndarray,
    labels: np.ndarray,
    learning_rate: float = 0.15,
    l2: float = 0.02,
    epochs: int = 1800,
) -> tuple[np.ndarray, float, list[float]]:
    """Full-batch gradient descent with L2; deterministic (zero init)."""
    n_samples, n_features = matrix.shape
    weights = np.zeros(n_features, dtype=np.float64)
    bias = 0.0
    losses: list[float] = []
    for epoch in range(epochs):
        logits = matrix @ weights + bias
        probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))
        errors = probabilities - labels
        gradient_w = (matrix.T @ errors) / max(n_samples, 1) + l2 * weights
        gradient_b = float(errors.mean()) if n_samples else 0.0
        weights -= learning_rate * gradient_w
        bias -= learning_rate * gradient_b
        if epoch % 50 == 0 or epoch == epochs - 1:
            eps = 1e-12
            loss = -np.mean(
                labels * np.log(probabilities + eps) + (1.0 - labels) * np.log(1.0 - probabilities + eps)
            ) + 0.5 * l2 * float(weights @ weights)
            losses.append(round(float(loss), 6))
    return weights, bias, losses


def predict_proba(matrix: np.ndarray, weights: np.ndarray, bias: float) -> np.ndarray:
    logits = matrix @ weights + bias
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0)))


def roc_curve(labels: np.ndarray, scores: np.ndarray) -> tuple[list[dict], float]:
    positives = float(labels.sum())
    negatives = float(len(labels) - positives)
    if positives == 0 or negatives == 0:
        return [], 0.0
    order = np.argsort(-scores)
    sorted_labels = labels[order]
    sorted_scores = scores[order]
    tp = np.cumsum(sorted_labels)
    fp = np.cumsum(1.0 - sorted_labels)
    tpr = tp / positives
    fpr = fp / negatives
    points = [{"fpr": 0.0, "tpr": 0.0}]
    last_score = None
    for index in range(len(sorted_scores)):
        if last_score is not None and sorted_scores[index] == last_score:
            continue
        points.append({"fpr": round(float(fpr[index]), 5), "tpr": round(float(tpr[index]), 5)})
        last_score = sorted_scores[index]
    if points[-1] != {"fpr": 1.0, "tpr": 1.0}:
        points.append({"fpr": 1.0, "tpr": 1.0})
    fpr_array = np.asarray([point["fpr"] for point in points])
    tpr_array = np.asarray([point["tpr"] for point in points])
    auc = _trapezoid(tpr_array, fpr_array)
    return points, round(auc, 4)


def pr_curve(labels: np.ndarray, scores: np.ndarray) -> tuple[list[dict], float]:
    positives = float(labels.sum())
    if positives == 0:
        return [], 0.0
    order = np.argsort(-scores)
    sorted_labels = labels[order]
    sorted_scores = scores[order]
    tp = np.cumsum(sorted_labels)
    fp = np.cumsum(1.0 - sorted_labels)
    precision = tp / np.maximum(tp + fp, 1.0)
    recall = tp / positives
    points: list[dict] = []
    last_score = None
    for index in range(len(sorted_scores)):
        if last_score is not None and sorted_scores[index] == last_score:
            continue
        points.append(
            {"recall": round(float(recall[index]), 5), "precision": round(float(precision[index]), 5)}
        )
        last_score = sorted_scores[index]
    pr_auc = 0.0
    previous_recall = 0.0
    for point in points:
        pr_auc += (point["recall"] - previous_recall) * point["precision"]
        previous_recall = point["recall"]
    return points, round(float(pr_auc), 4)


def confusion(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predicted = (scores >= threshold).astype(np.float64)
    tp = float(((predicted == 1) & (labels == 1)).sum())
    fp = float(((predicted == 1) & (labels == 0)).sum())
    fn = float(((predicted == 0) & (labels == 1)).sum())
    tn = float(((predicted == 0) & (labels == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / max(len(labels), 1)
    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "flagged": int(tp + fp),
    }


def threshold_scan(labels: np.ndarray, scores: np.ndarray) -> list[dict]:
    scan: list[dict] = []
    for threshold in SCAN_THRESHOLDS:
        metrics = confusion(labels, scores, threshold)
        scan.append({"threshold": threshold, **metrics})
    return scan


def train_pipeline(
    train_records: list[dict],
    validation_records: list[dict],
    numeric_keys: list[str],
    categorical_keys: list[str],
    hyperparams: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hyperparams = hyperparams or {}
    learning_rate = float(hyperparams.get("learning_rate", 0.15))
    l2 = float(hyperparams.get("l2", 0.02))
    epochs = int(hyperparams.get("epochs", 1800))

    train = build_dataset(train_records, numeric_keys, categorical_keys)
    validation = build_dataset(validation_records, numeric_keys, categorical_keys)
    standardizer = fit_standardizer(train.matrix)
    train_scaled = apply_standardizer(train.matrix, standardizer)
    validation_scaled = apply_standardizer(validation.matrix, standardizer) if validation.matrix.size else validation.matrix

    weights, bias, losses = train_logistic(train_scaled, train.labels, learning_rate, l2, epochs)
    train_scores = predict_proba(train_scaled, weights, bias) if train.matrix.size else np.array([])
    validation_scores = predict_proba(validation_scaled, weights, bias) if validation.matrix.size else np.array([])

    validation_positives = int(validation.labels.sum())
    positive_rate = validation_positives / max(len(validation.labels), 1)
    warning = ""
    if 0 < len(validation.labels) and positive_rate < MIN_POSITIVE_RATE:
        warning = (
            f"验证月正例仅 {validation_positives}/{len(validation.labels)}（{positive_rate:.1%} < "
            f"{MIN_POSITIVE_RATE:.0%}），样本不均衡，指标置信度不足"
        )

    roc_points, auc = roc_curve(validation.labels, validation_scores)
    pr_points, pr_auc = pr_curve(validation.labels, validation_scores)
    coefficients = [
        {
            "name": name,
            "coefficient": round(float(weight), 6),
            "group": "one_hot" if "=" in name else ("intercept" if name == "intercept" else "numeric"),
        }
        for name, weight in zip(train.names, weights)
    ]
    coefficients.append({"name": "intercept", "coefficient": round(float(bias), 6), "group": "intercept"})

    metrics = {
        "auc": auc,
        "pr_auc": pr_auc,
        "train_rows": int(train.matrix.shape[0]),
        "validation_rows": int(validation.matrix.shape[0]),
        "train_positives": int(train.labels.sum()),
        "validation_positives": validation_positives,
        "train_positive_rate": round(float(train.labels.mean()) if len(train.labels) else 0.0, 4),
        "validation_positive_rate": round(positive_rate, 4),
        "loss_curve": losses[:: max(1, len(losses) // 24)],
        "confusion_035": confusion(validation.labels, validation_scores, 0.35),
        "mean_validation_score": round(float(validation_scores.mean()) if len(validation_scores) else 0.0, 4),
        "high_risk_at_035": int((validation_scores >= 0.35).sum()) if len(validation_scores) else 0,
    }

    return {
        "coefficients": coefficients,
        "metrics": metrics,
        "roc_points": roc_points,
        "pr_points": pr_points,
        "threshold_scan": threshold_scan(validation.labels, validation_scores),
        "standardization": {"names": train.names, **standardizer, "bias": round(float(bias), 6)},
        "train_rows": int(train.matrix.shape[0]),
        "validation_rows": int(validation.matrix.shape[0]),
        "train_positives": int(train.labels.sum()),
        "warning": warning,
        "validation_scores": validation_scores,
        "validation_records": validation.meta,
        "hyperparams": {"learning_rate": learning_rate, "l2": l2, "epochs": epochs},
    }


def contribution_reasons(record: dict, coefficients: list[dict], standardization: dict[str, Any], top_n: int = 3) -> list[dict]:
    """Reason codes: coefficient x standardised feature value (log-odds contribution)."""
    mean = dict(zip(standardization["names"], standardization["mean"]))
    std = dict(zip(standardization["names"], standardization["std"]))
    features = record["features"]
    by_name = {item["name"]: item["coefficient"] for item in coefficients if item["group"] != "intercept"}
    contributions: list[dict] = []
    for name, coefficient in by_name.items():
        if "=" in name:
            key, value = name.split("=", 1)
            if str(features.get(key, "")) != value:
                continue
            raw_value = value
        else:
            key = name
            try:
                raw_value = float(features.get(key, 0.0))
            except (TypeError, ValueError):
                raw_value = 0.0
        z_value = (float(raw_value) - mean.get(name, 0.0)) / (std.get(name, 1.0) or 1.0) if "=" not in name else 1.0
        contribution = coefficient * z_value
        contributions.append(
            {
                "feature": name,
                "label": _label_for(name),
                "raw_value": raw_value,
                "z_value": round(float(z_value), 4),
                "contribution": round(float(contribution), 4),
            }
        )
    contributions.sort(key=lambda item: item["contribution"], reverse=True)
    positives = [item for item in contributions if item["contribution"] > 0][:top_n]
    return positives or contributions[:top_n]


def _label_for(name: str) -> str:
    if "=" in name:
        return name.split("=", 1)[0]
    for feature in NUMERIC_FEATURES:
        if feature["key"] == name:
            return feature["label"]
    return name
