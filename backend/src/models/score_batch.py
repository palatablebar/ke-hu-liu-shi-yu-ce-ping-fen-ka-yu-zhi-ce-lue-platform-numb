from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class ScoreBatch(Base):
    """一次评分批次：阈值、预算、风险分档、名单与原因。"""

    __tablename__ = "score_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="succeeded", nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    budget_total: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_account: Mapped[float] = mapped_column(Float, nullable=False)
    retention_lift: Mapped[float] = mapped_column(Float, nullable=False)
    bands: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_by: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
