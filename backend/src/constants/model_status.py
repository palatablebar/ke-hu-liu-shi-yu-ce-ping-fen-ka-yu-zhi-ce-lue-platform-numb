"""Training lifecycle — shared with frontend/src/constants/modelStatus.ts."""
from enum import StrEnum


class ModelStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


MODEL_STATUS_LABELS: dict[str, str] = {
    ModelStatus.PENDING: "排队中",
    ModelStatus.RUNNING: "训练中",
    ModelStatus.SUCCEEDED: "已完成",
    ModelStatus.FAILED: "失败",
}

MIN_POSITIVE_RATE = 0.05  # 正例 < 5% 时提示样本不均衡
