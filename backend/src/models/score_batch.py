from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class ScoreBatch(Base):
    """一次评分批次：阈值、预算、风险分档、名单与原因。

    生命周期（``lifecycle``）三态分离：

    - draft（草稿）：候选策略，不驱动风险图与导出；
    - active（现行策略）：全局唯一（见部分唯一索引），名单与导出都跟随它；
    - archived（历史版本）：被切换下来的旧版本，永久保留但不再生效。

    ``policy_fingerprint`` 标识同一模型 + 同一组策略参数，重复执行直接复用既有
    草稿/现行批次，不新增版本。
    """

    __tablename__ = "score_batches"
    __table_args__ = (
        # 现行策略全局唯一：从数据库层面保证不可能同时留下两个 active 版本。
        Index(
            "uq_score_batches_active_one",
            "lifecycle",
            unique=True,
            postgresql_where=text("lifecycle = 'active'"),
        ),
        # 同一策略（同模型同参数）在未归档的版本里只允许出现一次 → 重复执行不新增版本。
        Index(
            "uq_score_batches_fingerprint_open",
            "policy_fingerprint",
            unique=True,
            postgresql_where=text("lifecycle <> 'archived'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="succeeded", nullable=False)
    lifecycle: Mapped[str] = mapped_column(
        String(16), default="draft", server_default="draft", nullable=False
    )
    # 仅 active / archived（即曾经发布过的策略版本）有版本号，草稿为 None。
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 发布后由哪个批次接替（历史版本指向把它切换下来的新版本）。
    superseded_by: Mapped[int | None] = mapped_column(
        ForeignKey("score_batches.id"), nullable=True
    )
    policy_fingerprint: Mapped[str] = mapped_column(String(80), default="", server_default="", nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    budget_total: Mapped[float] = mapped_column(Float, nullable=False)
    cost_per_account: Mapped[float] = mapped_column(Float, nullable=False)
    retention_lift: Mapped[float] = mapped_column(Float, nullable=False)
    bands: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    selected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 兼容列：等价于 lifecycle in ('active', 'archived')，新代码统一读写 lifecycle。
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    published_by: Mapped[str] = mapped_column(String(120), default="", server_default="", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), default="seed", server_default="seed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
