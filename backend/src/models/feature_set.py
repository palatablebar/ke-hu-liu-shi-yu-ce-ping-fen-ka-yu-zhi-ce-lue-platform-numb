from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class FeatureSet(Base):
    """特征集定义：目标、训练/验证月份、参与建模的字段。"""

    __tablename__ = "feature_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    target: Mapped[str] = mapped_column(String(48), default="churn_next_30d", nullable=False)
    train_months: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    validation_month: Mapped[str] = mapped_column(String(10), nullable=False)
    numeric_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    categorical_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_by: Mapped[str] = mapped_column(String(120), default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
