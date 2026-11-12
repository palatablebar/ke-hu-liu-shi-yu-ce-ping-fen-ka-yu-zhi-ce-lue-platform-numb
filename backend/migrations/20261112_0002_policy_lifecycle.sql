-- churnmod policy-lifecycle migration (PostgreSQL 16)
-- 从「published 布尔位」迁移到「草稿 / 现行策略 / 历史版本」三态模型。
-- 幂等：可重复执行；全新库由 init_db 的 create_all 直接建成新结构，本脚本仅升级存量库。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. 生命周期列：默认草稿，随后按旧 published 位回填。
ALTER TABLE score_batches
    ADD COLUMN IF NOT EXISTS lifecycle VARCHAR(16) NOT NULL DEFAULT 'draft';

UPDATE score_batches
SET lifecycle = CASE WHEN published THEN 'active' ELSE 'draft' END
WHERE lifecycle = 'draft';

-- 2. 策略版本号（曾经发布过的版本按发布时间/主键分配单调版本号；草稿保持 NULL）。
ALTER TABLE score_batches
    ADD COLUMN IF NOT EXISTS policy_version INTEGER;

UPDATE score_batches
SET policy_version = sub.version_no
FROM (
    SELECT id, ROW_NUMBER() OVER (ORDER BY COALESCE(published_at, created_at), id) AS version_no
    FROM score_batches
    WHERE published = TRUE
) AS sub
WHERE score_batches.id = sub.id AND score_batches.policy_version IS NULL;

-- 3. 接替关系与策略指纹（指纹用于「同一策略重复执行不新增版本」）。
ALTER TABLE score_batches
    ADD COLUMN IF NOT EXISTS superseded_by INTEGER REFERENCES score_batches(id),
    ADD COLUMN IF NOT EXISTS policy_fingerprint VARCHAR(80) NOT NULL DEFAULT '';

-- 4. 现行策略全局唯一：数据库层面保证不可能同时留下两个 active 版本。
CREATE UNIQUE INDEX IF NOT EXISTS uq_score_batches_active_one
    ON score_batches (lifecycle)
    WHERE lifecycle = 'active';

-- 5. 同一策略（同模型同参数）在未归档版本中只允许一份 → 重复执行复用而非新增。
--    存量数据若存在历史重复，先回填再建索引；回填采用 sha1 指纹，与服务端口径一致。
UPDATE score_batches
SET policy_fingerprint = encode(
    digest(
        'model=' || model_run_id
        || '|threshold=' || to_char(threshold, 'FM999990.000000')
        || '|budget=' || to_char(budget_total, 'FM99999999990.00')
        || '|cost=' || to_char(cost_per_account, 'FM99999999990.00')
        || '|lift=' || to_char(retention_lift, 'FM999990.000000'),
        'sha1'
    ),
    'hex'
)
WHERE policy_fingerprint = '';

-- 极端存量情况下若存在重复的未归档指纹，保留最早一条、其余转历史版本后再建索引。
UPDATE score_batches AS dup
SET lifecycle = 'archived',
    superseded_by = keep.id
FROM (
    SELECT MIN(id) AS id, policy_fingerprint
    FROM score_batches
    WHERE lifecycle <> 'archived' AND policy_fingerprint <> ''
    GROUP BY policy_fingerprint
    HAVING COUNT(*) > 1
) AS keep
WHERE dup.policy_fingerprint = keep.policy_fingerprint
  AND dup.lifecycle <> 'archived'
  AND dup.id <> keep.id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_score_batches_fingerprint_open
    ON score_batches (policy_fingerprint)
    WHERE lifecycle <> 'archived';

-- 6. 兼容列 published / published_by / published_at 保留，新代码以 lifecycle 为准。
COMMENT ON COLUMN score_batches.lifecycle IS 'draft=草稿 / active=现行策略(唯一) / archived=历史版本';
COMMENT ON COLUMN score_batches.policy_version IS '发布后的单调策略版本号，草稿为 NULL';
COMMENT ON COLUMN score_batches.superseded_by IS '把本版本切换下来的新批次 id';
COMMENT ON COLUMN score_batches.policy_fingerprint IS '模型+阈值+预算+成本+挽留比例的 sha1 指纹';
