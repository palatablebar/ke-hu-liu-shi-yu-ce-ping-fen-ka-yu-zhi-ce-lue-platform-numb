"""Deterministic demo fixture for churnmod — pure data, no database imports.

240 SaaS accounts × 5 monthly feature snapshots (1,200 rows). The churn label is a
noisy function of the account's latent risk trajectory, so the hand-written
logistic regression lands around AUC ≈ 0.78 on the held-out month while the
threshold 0.35 flags roughly 38 accounts — the numbers quoted in the demo story.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta

BRAND = "churnmod"
ACCOUNT_COUNT = 240
MONTHS: tuple[date, ...] = (
    date(2026, 7, 1),
    date(2026, 8, 1),
    date(2026, 9, 1),
    date(2026, 10, 1),
    date(2026, 11, 1),
)
MONTH_LABELS = tuple(month.strftime("%Y-%m") for month in MONTHS)
TRAIN_MONTHS = MONTH_LABELS[:4]
VALIDATION_MONTH = MONTH_LABELS[4]

# label model: latent = risk + noise; churn when latent > LABEL_CUT
LABEL_CUT = 0.74
LABEL_SIGMA = 0.15
FEATURE_NOISE = 1.5

INDUSTRIES = ("电商", "金融", "制造", "教育", "医疗")
PLANS = ("标准版", "专业版", "旗舰版")
REGIONS = ("华北", "华东", "华南", "西南")
COMPANY_PREFIX = (
    "海岳", "云栖", "北辰", "青禾", "恒澜", "星野", "锦程", "鼎新", "朗途", "沐辰",
    "南栀", "西岭", "长川", "知行", "合润", "远帆", "初禾", "拓维", "知微", "和光",
)
COMPANY_SUFFIX = ("科技", "网络", "数据", "信息", "智能")

OWNERS = (
    ("csm@churnmod.io", "林知远"),
    ("chen@churnmod.io", "陈晚晴"),
    ("zhou@churnmod.io", "周砚"),
)


def _rng(*parts: object) -> random.Random:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def account_code(index: int) -> str:
    return f"ACC-{index + 1:04d}"


def _features_for(risk: float, rng: random.Random) -> dict:
    noise = FEATURE_NOISE
    day_noise = rng.gauss(0, 1) * noise
    usage_days = _clamp(round(24 - 14 * risk + 4.5 * day_noise), 1, 30)
    ratio_noise = rng.gauss(0, 1) * noise
    active_ratio = _clamp(0.86 - 0.56 * risk + 0.11 * ratio_noise, 0.03, 0.99)
    api_noise = rng.gauss(0, 1) * noise
    api_calls_k = _clamp(round(420 * (0.9 - risk) + 85 * api_noise), 1, 980)
    storage_noise = rng.gauss(0, 1) * noise
    storage_gb = _clamp(round(120 * (1.15 - risk) + 26 * storage_noise), 5, 320)
    tickets_noise = rng.gauss(0, 1) * noise
    tickets_open = max(0, round(1 + 9 * risk + 2.2 * tickets_noise))
    p1_noise = rng.gauss(0, 1) * noise
    tickets_p1 = max(0, round(0.2 + 3 * risk + 0.8 * p1_noise))
    nps_noise = rng.gauss(0, 1) * noise
    nps = _clamp(round(52 - 112 * risk + 17 * nps_noise), -100, 100)
    overdue_noise = rng.gauss(0, 1) * noise
    invoice_overdue_days = max(0, round(42 * risk + 12 * overdue_noise))
    seat_noise = rng.gauss(0, 1) * noise
    seat_utilization = _clamp(active_ratio * (0.96 + 0.08 * seat_noise), 0.02, 1.0)
    sponsor = int(rng.random() > 0.30 + 0.55 * risk)
    integration_noise = rng.gauss(0, 1) * noise
    integration_count = max(1, round(7 - 5 * risk + 1.2 * integration_noise))
    training_noise = rng.gauss(0, 1) * noise
    training_sessions = max(0, round(4 - 3 * risk + 0.8 * training_noise))
    return {
        "usage_days": int(usage_days),
        "active_user_ratio": round(float(active_ratio), 3),
        "api_calls_k": int(api_calls_k),
        "storage_gb": int(storage_gb),
        "tickets_open": int(tickets_open),
        "tickets_p1": int(tickets_p1),
        "nps": int(nps),
        "invoice_overdue_days": int(invoice_overdue_days),
        "seat_utilization": round(float(seat_utilization), 3),
        "executive_sponsor": int(sponsor),
        "integration_count": int(integration_count),
        "training_sessions": int(training_sessions),
    }


def build_accounts() -> list[dict]:
    accounts: list[dict] = []
    for index in range(ACCOUNT_COUNT):
        rng = _rng("account", index)
        base_risk = rng.uniform(0.26, 0.74)
        trend = rng.uniform(-0.028, 0.05)
        owner_email, owner_name = OWNERS[index // 80]
        seats = 20 + (index * 37) % 480
        monthly_fee = 800 + (index * 137) % 11200
        contract_end = date(2026, 12, 1) + timedelta(days=(index * 7) % 120)
        accounts.append(
            {
                "index": index,
                "code": account_code(index),
                "company_name": COMPANY_PREFIX[index % len(COMPANY_PREFIX)]
                + COMPANY_SUFFIX[(index * 3) % len(COMPANY_SUFFIX)]
                + "有限公司",
                "industry": INDUSTRIES[index % len(INDUSTRIES)],
                "plan": PLANS[(index * 2) % len(PLANS)],
                "region": REGIONS[(index * 7) % len(REGIONS)],
                "seats": seats,
                "monthly_fee": float(monthly_fee),
                "csm_owner_email": owner_email,
                "csm_owner_name": owner_name,
                "contract_end": contract_end,
                "base_risk": base_risk,
                "trend": trend,
            }
        )
    return accounts


def build_feature_rows(accounts: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for account in accounts:
        rng = _rng("trajectory", account["index"])
        churn_month: date | None = None
        for position, month in enumerate(MONTHS):
            risk = _clamp(account["base_risk"] + account["trend"] * position + rng.gauss(0, 0.05), 0.0, 1.0)
            features = _features_for(risk, rng)
            features["industry"] = account["industry"]
            features["plan"] = account["plan"]
            features["region"] = account["region"]
            latent = risk + rng.gauss(0, LABEL_SIGMA)
            label = 1 if latent > LABEL_CUT else 0
            if label and churn_month is None:
                churn_month = date(month.year + (month.month == 12), month.month % 12 + 1, 15)
            rows.append(
                {
                    "account_code": account["code"],
                    "month": month,
                    "month_label": month.strftime("%Y-%m"),
                    "features": features,
                    "churn_next_30d": label,
                    "label_known": True,
                }
            )
        account["churn_date"] = churn_month
        account["status"] = "churned" if churn_month else "active"
    return rows


def build_dataset() -> dict:
    accounts = build_accounts()
    rows = build_feature_rows(accounts)
    positive = sum(row["churn_next_30d"] for row in rows)
    validation = [row for row in rows if row["month_label"] == VALIDATION_MONTH]
    validation_positive = sum(row["churn_next_30d"] for row in validation)
    return {
        "brand": BRAND,
        "accounts": accounts,
        "feature_rows": rows,
        "months": list(MONTH_LABELS),
        "train_months": list(TRAIN_MONTHS),
        "validation_month": VALIDATION_MONTH,
        "expected": {
            "accounts": len(accounts),
            "features": len(rows),
            "churn_rate": round(positive / len(rows), 4),
            "validation_positives": validation_positive,
        },
    }
