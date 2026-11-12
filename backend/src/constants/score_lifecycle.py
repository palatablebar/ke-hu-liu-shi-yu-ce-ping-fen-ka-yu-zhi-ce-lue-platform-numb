"""Score-policy lifecycle — shared with frontend/src/constants/scoreLifecycle.ts.

三个互斥阶段把「草稿 / 现行策略 / 历史版本」彻底分开：

- ``draft``    草稿：新建评分批次的候选，仅供策略台查看与对比，不驱动任何名单；
- ``active``   现行策略：全局有且仅有一个（部分唯一索引兜底），风险图与导出都跟随它；
- ``archived`` 历史版本：被新版本原子切换下来的旧策略，只保留、永不再生效。
"""
from enum import StrEnum


class ScoreLifecycle(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


SCORE_LIFECYCLE_LABELS: dict[str, str] = {
    ScoreLifecycle.DRAFT: "草稿",
    ScoreLifecycle.ACTIVE: "现行策略",
    ScoreLifecycle.ARCHIVED: "历史版本",
}
