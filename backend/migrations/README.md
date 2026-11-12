# migrations

Runtime schema is created idempotently by `src.config.database.init_db()`
(SQLAlchemy `Base.metadata.create_all`) on backend startup, so a fresh
`docker compose up` needs no migration step.

| 文件 | 说明 |
|---|---|
| `20261112_0001_initial.sql` | 全量 PostgreSQL 16 DDL 快照（与 `src/models/*` 保持一致），用于评审 / 离线建库 |
| `20261112_0002_policy_lifecycle.sql` | 策略生命周期升级：草稿 / 现行策略 / 历史版本三态分离；存量库按顺序执行即可，幂等可重跑 |

## 策略生命周期（score_batches.lifecycle）

| 取值 | 含义 | 约束 |
|---|---|---|
| `draft` | 草稿，候选策略 | 不驱动风险图与导出；同指纹在未归档版本中唯一 |
| `active` | 现行策略 | 部分唯一索引 `uq_score_batches_active_one` 保证全局只有一个 |
| `archived` | 历史版本 | 被新版本原子切换下来，永久保留但不再生效；`superseded_by` 指向接替批次 |

- `policy_version`：发布时分配的单调版本号（草稿为 NULL）。
- `policy_fingerprint`：模型 + 阈值 + 预算 + 单客成本 + 挽留比例的 sha1 指纹，
  同一策略重复执行直接复用既有草稿/现行批次，不新增版本。
- 兼容列 `published` 保留，等价于 `lifecycle IN ('active','archived')`，新代码以 `lifecycle` 为准。

## 其余表

| table | 说明 |
|---|---|
| `users` | 三角色演示账号（admin / analyst / csm） |
| `accounts` | SaaS 客户主档（240 家，含 CSM 归属与合同信息） |
| `account_features` | 客户月度特征快照（自然键 account + month，含流失标签） |
| `feature_sets` | 特征集定义与训练/验证月份（时间切分防泄漏） |
| `model_runs` | 逻辑回归训练批次：系数、AUC/PR、阈值扫描、标准化参数 |
| `audit_logs` | 横切审计日志 |
