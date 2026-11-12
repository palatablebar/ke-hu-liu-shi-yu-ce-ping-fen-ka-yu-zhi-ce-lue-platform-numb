# migrations

Runtime schema is created idempotently by `src.config.database.init_db()`
(SQLAlchemy `Base.metadata.create_all`) on backend startup, so a fresh
`docker compose up` needs no migration step.

`20261112_0001_initial.sql` is the authoritative PostgreSQL 16 DDL snapshot of the
models under `src/models/` for review / offline provisioning.

| table | 说明 |
|---|---|
| `users` | 三角色演示账号（admin / analyst / csm） |
| `accounts` | SaaS 客户主档（240 家，含 CSM 归属与合同信息） |
| `account_features` | 客户月度特征快照（自然键 account + month，含流失标签） |
| `feature_sets` | 特征集定义与训练/验证月份（时间切分防泄漏） |
| `model_runs` | 逻辑回归训练批次：系数、AUC/PR、阈值扫描、标准化参数 |
| `score_batches` | 评分批次：阈值、预算、风险分档、Top-K 名单与原因 |
| `audit_logs` | 横切审计日志 |
