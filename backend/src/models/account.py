from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class Account(Base):
    """SaaS 客户主档（演示 240 家）。"""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(80), nullable=False)
    industry: Mapped[str] = mapped_column(String(24), nullable=False)
    plan: Mapped[str] = mapped_column(String(24), nullable=False)
    region: Mapped[str] = mapped_column(String(24), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_fee: Mapped[float] = mapped_column(Float, nullable=False)
    csm_owner_email: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    csm_owner_name: Mapped[str] = mapped_column(String(40), nullable=False)
    contract_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    churn_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
