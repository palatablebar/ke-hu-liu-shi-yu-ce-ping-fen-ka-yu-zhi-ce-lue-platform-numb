from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class AccountFeature(Base):
    """客户月度特征快照；自然键 (account, month)。"""

    __tablename__ = "account_features"
    __table_args__ = (UniqueConstraint("account_id", "month", name="uq_feature_account_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    month_label: Mapped[str] = mapped_column(String(10), nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    churn_next_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label_known: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
