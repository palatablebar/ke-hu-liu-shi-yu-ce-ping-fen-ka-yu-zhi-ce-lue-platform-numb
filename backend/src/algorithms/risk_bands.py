"""Risk banding, threshold metrics and budget-constrained outreach selection."""
from __future__ import annotations

import math

import numpy as np

from src.constants.risk_band import RISK_BAND_LABELS, RiskBand


def band_cuts(scores: list[float]) -> dict[str, float]:
    """Score quantiles for the three risk bands (thirds)."""
    if not scores:
        return {"low_max": 0.0, "high_min": 0.0}
    low_cut = float(np.percentile(np.asarray(scores, dtype=np.float64), 100.0 / 3.0))
    high_cut = float(np.percentile(np.asarray(scores, dtype=np.float64), 200.0 / 3.0))
    return {"low_max": round(low_cut, 6), "high_min": round(high_cut, 6)}


def assign_band(score: float, cuts: dict[str, float]) -> str:
    if score >= cuts["high_min"]:
        return RiskBand.HIGH.value
    if score >= cuts["low_max"]:
        return RiskBand.MEDIUM.value
    return RiskBand.LOW.value


def build_results(
    scored: list[dict],
    cuts: dict[str, float],
    threshold: float,
    budget_total: float,
    cost_per_account: float,
    retention_lift: float,
) -> tuple[list[dict], dict]:
    """Attach bands, expected save value, band lift and the budgeted top-K list."""
    overall_mean = float(np.mean([item["score"] for item in scored])) if scored else 0.0
    band_members: dict[str, list[float]] = {band.value: [] for band in RiskBand}
    results: list[dict] = []
    for item in scored:
        band = assign_band(item["score"], cuts)
        band_members[band].append(item["score"])
        results.append({**item, "band": band, "band_label": RISK_BAND_LABELS[band]})

    band_lift: dict[str, float] = {}
    for band, members in band_members.items():
        band_mean = float(np.mean(members)) if members else 0.0
        band_lift[band] = round(band_mean / overall_mean, 4) if overall_mean else 0.0

    for item in results:
        item["lift"] = band_lift[item["band"]]
        # 预期挽回 = 年化合同额 × 流失概率 × 触达可挽留比例
        item["expected_save"] = round(item["monthly_fee"] * 12.0 * item["score"] * retention_lift, 2)

    high_count = sum(1 for item in results if item["score"] >= threshold)
    k = int(math.floor(budget_total / cost_per_account)) if cost_per_account > 0 else 0
    ranked = sorted(results, key=lambda item: item["score"], reverse=True)
    selected_codes: set[str] = set()
    for rank, item in enumerate(ranked[: max(0, k)], start=1):
        item["rank"] = rank
        item["selected"] = True
        selected_codes.add(item["account_code"])
    for item in results:
        if item["account_code"] not in selected_codes:
            item["selected"] = False
            item["rank"] = None
    selected = [item for item in results if item["selected"]]

    total_expected_save = round(sum(item["expected_save"] for item in selected), 2)
    summary = {
        "scored": len(results),
        "high_risk": high_count,
        "high_band": len(band_members[RiskBand.HIGH.value]),
        "medium_band": len(band_members[RiskBand.MEDIUM.value]),
        "low_band": len(band_members[RiskBand.LOW.value]),
        "threshold": round(threshold, 4),
        "budget_total": round(budget_total, 2),
        "cost_per_account": round(cost_per_account, 2),
        "k": k,
        "selected_count": len(selected),
        "total_expected_save": total_expected_save,
        "avg_expected_save": round(total_expected_save / len(selected), 2) if selected else 0.0,
        "overall_mean_score": round(overall_mean, 4),
        "band_lift": band_lift,
        "band_cuts": cuts,
        "band_sizes": {band: len(members) for band, members in band_members.items()},
        "expected_save_formula": "年化合同额 × P(流失) × 触达可挽留比例",
        "retention_lift": round(retention_lift, 4),
    }
    return results, summary
