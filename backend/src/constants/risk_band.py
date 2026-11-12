"""Risk bands and scoring policy constants — shared with frontend/src/constants/riskBand.ts."""
from enum import StrEnum


class RiskBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


RISK_BAND_LABELS: dict[str, str] = {
    RiskBand.HIGH: "高风险",
    RiskBand.MEDIUM: "中风险",
    RiskBand.LOW: "低风险",
}

SCAN_THRESHOLDS = [round(0.10 + 0.01 * index, 2) for index in range(81)]  # 0.10 .. 0.90
