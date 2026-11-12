from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class ModelRun(Base):
    """一次逻辑回归训练批次：系数、标准化参数、评估曲线与阈值扫描。"""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    feature_set_id: Mapped[int] = mapped_column(ForeignKey("feature_sets.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    hyperparams: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    coefficients: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    roc_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pr_points: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    threshold_scan: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    standardization: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    train_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    train_positives: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
