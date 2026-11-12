# Churn Chart · 客户流失预测评分卡与阈值策略台

安澜云服务 · 客户成功部的**流失预判海图**：把用量、工单、账单三类月度特征汇入一张 numpy 手写逻辑回归评分卡，先算流失概率，再按阈值与预算画出触达航线，名单上每家客户都带得走「为什么高风险」的三条原因。

> 一句话：把 CSM「凭感觉挑要跑的客户」变成可复核的概率、分档与预算约束。

## 1. 真实场景

- **客户**：安澜云服务 · 客户成功部（5 人），SaaS 客户 240 家（演示规模），续费前 30 天由 CSM 凭感觉筛「要跑」的客户。
- **现有工作流**：CSM 翻用量与工单记录人工判断，名单靠经验；去年整体流失 14%，流失后才复盘。
- **三个痛点**：① 靠感觉筛选浪费 CSM 时间；② 无法向客户解释「为什么高风险」；③ 阈值拍脑袋、触达预算有限。
- **上下游**：上游 = 客户用量 / 工单 / 账单月度特征表；本系统替代「人工凭感觉挑客户」；下游 = CSM 触达名单、续费例会。

## 2. 角色与权限

| 角色 | 账号 | 权限 | 典型动作 |
|---|---|---|---|
| `admin` 客户成功负责人 | `admin@churnmod.io` | 特征/参数/阈值发布、训练、评分、审计日志 | 发布阈值策略 |
| `analyst` 数据分析师 | `analyst@churnmod.io` | 训练 / 评估 / 调参 / 评分；**发布策略 403** | 训练模型、扫阈值 |
| `csm` 客户成功经理 | `csm@churnmod.io` | 只读**自己名下**客户名单与原因；训练/评分/发布均 **403** | 查名单、看原因、导出自己客户 |

密码统一 `Demo@2026`。CSM 的数据范围在后端按 `csm_owner_email` 过滤（不是前端隐藏）。

## 3. 四个核心实体

| 实体 | 表 | 说明 |
|---|---|---|
| `Account` | `accounts` | SaaS 客户主档（240 家，含行业/版本/区域/席位/合同额/CSM 归属） |
| `AccountFeature` | `account_features` | 月度特征快照（自然键 account+month，含 `churn_next_30d` 标签），5 个月 × 240 = 1,200 行 |
| `FeatureSet` | `feature_sets` | 特征集定义、训练 4 个月 / 验证第 5 个月（时间切分防泄漏） |
| `ModelRun` | `model_runs` | 训练批次：系数、标准化参数、AUC/PR、ROC/PR 散点、阈值扫描、混淆矩阵 |
| `ScoreBatch` | `score_batches` | 评分批次：阈值、预算、分档、Top-K 名单与原因、策略生命周期（draft 草稿 / active 现行策略 / archived 历史版本） |

每个实体都贯穿：表 → model → schema → service → controller → route → 前端 api → store → 页面/组件。

## 4. 两个真算算法（Python + numpy，前端只画后端返回的散点）

### 4.1 逻辑回归训练 `backend/src/algorithms/logistic.py`

1. 设计矩阵：12 个数值特征 + 行业/版本/区域 one-hot。
2. **时间切分防泄漏**：标准化均值/标准差只用前 4 个月（960 行）拟合，再应用到第 5 个月（240 行）。
3. 全批量梯度下降 + L2（默认 lr=0.15、l2=0.02、1800 轮，零初始化，确定性可复现）。
4. 评估：ROC 曲线逐点计算后用**梯形积分**得 AUC；PR 曲线按 recall 增量累计得 PR-AUC；阈值 0.10~0.90 扫描输出 precision/recall/F1；正例率 < 5% 时返回样本不均衡告警。
5. 基线结果：**AUC = 0.7843**、PR-AUC = 0.5013、阈值 0.35 命中 38 家（验证月 240 家 / 正例 48）。

### 4.2 风险分层与预算触达 `backend/src/algorithms/risk_bands.py`

1. 按评分三等分位切 3 档（高/中/低，各 80 家），档内 lift = 档均分 / 全体均分。
2. 阈值 `p ≥ 0.35` 计入高风险池（38 家）。
3. 预算约束：`K = floor(预算 / 单客成本) = floor(12500/500) = 25`，按分数（即 lift）降序取 Top-K。
4. 每家输出：概率、分档、lift、预期挽回 = 年化合同额 × P(流失) × 可挽留比例，以及**系数 × 标准化值 Top3 原因**。
5. 导出 CSV：25 行名单 + 原因（含 rank、score、band、expected_save）。

## 5. 页面（5）

1. **登录**（海图封面 + 罗盘 + 三账号）
2. **客户风险图** `/accounts`：评分名单、分数条、风险档、Top1 原因、预算内排名；点开客户抽屉看月度走势与 Top3 原因
3. **模型评估** `/models`：训练批次、AUC/PR-AUC、ROC 曲线、阈值-精确率/召回率曲线、混淆矩阵、样本不均衡告警
4. **特征与权重** `/features`：特征集口径、回归系数条（红推高/绿降低）、数值特征统计与相关系数、类别特征流失率
5. **阈值策略与触达预算** `/scores`：草稿/现行/历史三态编年、候选差异（参数 + 名单进出）、预算表单、Top-K 名单、一次性发布切换（admin）、导出现行策略 CSV

### 5.1 策略生命周期（草稿 / 现行 / 历史）

| 阶段 | `lifecycle` | 含义 | 约束 |
|---|---|---|---|
| 草稿 | `draft` | 新建评分批次的候选，仅供策略台查看与差异对比 | 不驱动风险图与导出；`policy_fingerprint` 在未归档版本中唯一 |
| 现行策略 | `active` | 全局唯一，客户风险图与导出名单共同跟随 | 部分唯一索引 `uq_score_batches_active_one` 兜底，不可能出现两个现行版本 |
| 历史版本 | `archived` | 被新版本切换下来的旧策略，永久保留 | 不再生效、不能重复发布/导出；`superseded_by` 指向接替批次 |

- **发布即原子切换**：单事务 + 行锁，旧现行策略归档、草稿升为现行并分配单调 `policy_version`；任何失败整体回滚，不留半成品。并发发布会串行化，后到者得到 409。
- **重复执行不新增版本**：同模型 + 同阈值/预算/成本/挽留比例（`policy_fingerprint` sha1）直接复用既有草稿或现行批次。
- **名单跟随同一现行版本**：`/accounts` 风险名单、`/scores/export/active` 与 `/scores/{id}/export`（仅现行可导出）统一读取 `active` 批次；草稿与历史版本无法导出对外名单。
- 新增端点：`GET /scores/active`、`GET /scores/{id}/diff`、`GET /scores/export/active`；发布响应返回 `switched / active / previous / active_count` 切换结果。

## 6. 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 前端 http://localhost:18249  后端 http://localhost:19249/docs  数据库 17749
```

启动时后端自动建表并执行幂等 seed，日志打印：

```text
SEED_SUMMARY brand=churnmod accounts=240 features=1200 models=1 scores=1 users=3
```

手动重跑（幂等）：

```bash
docker compose exec backend python scripts/seed_demo.py
```

## 7. 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite 5 + Pinia + vue-router 4；ROC/阈值曲线 SVG 自绘 |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2 + **numpy 1.26** |
| 异步 | Celery 5.4 + Redis 7（训练在 worker 容器执行） |
| 数据库 | PostgreSQL 16（JSONB 系数/曲线/名单） |
| 部署 | Docker Compose，恰好 5 服务：frontend / backend / worker / db / redis |

## 8. 目录

```text
gb-576/
├── backend/src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}
├── backend/src/algorithms/{logistic.py,risk_bands.py}     # 纯 numpy，可离线复算
├── backend/src/services/fixture.py                        # 确定性演示数据
├── backend/scripts/seed_demo.py                           # 幂等 seed
├── backend/migrations/                                    # DDL 快照 + 说明
├── worker/{Dockerfile,entrypoint.sh,healthy.py}
├── frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants,styles}
└── docker-compose.yml
```

## 9. 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 18249 / 19249 / 17749 | 端口映射 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | churnmod_* | PostgreSQL |
| `JWT_SECRET` / `JWT_EXPIRE_HOURS` | dev 值 / 8 | JWT |
| `DEFAULT_THRESHOLD` / `DEFAULT_BUDGET` | 0.35 / 12500 | seed 评分策略 |
| `COST_PER_ACCOUNT` / `EXPECTED_RETENTION_LIFT` | 500 / 0.35 | 预算与挽回口径 |
| `RATE_WINDOW_SECONDS` / `RATE_WINDOW_MAX` | 60 / 120 | 限流 |
| `SEED_DEMO` | true | 启动执行 seed |

## 10. 共享枚举（前后端各一份）

| 枚举 | 后端位置 | 前端位置 |
|---|---|---|
| 角色 `admin/analyst/csm` | `backend/src/constants/roles.py` | `frontend/src/constants/roles.ts` |
| 风险档 `high/medium/low` | `backend/src/constants/risk_band.py` | `frontend/src/constants/riskBand.ts` |
| 训练状态 `pending/running/succeeded/failed` | `backend/src/constants/model_status.py` | `frontend/src/constants/modelStatus.ts` |
| 策略生命周期 `draft/active/archived` | `backend/src/constants/score_lifecycle.py` | `frontend/src/constants/scoreLifecycle.ts` |
| 特征目录（12 数值 + 3 类别） | `backend/src/constants/features.py` | `frontend/src/constants/features.ts` |

## 11. 视觉

航海勘测图风：海图米色纸底 + 深靛墨色 + 罗盘刻度 + 等深线 + 经纬网格；双字体 **Marcellus**（标题/数字）+ **Noto Sans Mono**（正文/数据）；`oklch()` 色板，无纯黑纯白；响应式 1180 / 860 两档。

## 12. 已知边界

- 演示数据固定 240 客户 × 5 个月；真实客户量级需调整 `fixture.py` 与分页。
- 逻辑回归为手写全批量 GD，未做特征筛选 / 交叉验证 / 概率校准，AUC 仅样本外单月估计。
- 风险档按当期评分三等分，跨期不可直接比较；lift 只在演示数据上有意义。
- 更多细节见 `test-artifacts/gb-576/TESTING.md`。

## License

MIT (demo)。
