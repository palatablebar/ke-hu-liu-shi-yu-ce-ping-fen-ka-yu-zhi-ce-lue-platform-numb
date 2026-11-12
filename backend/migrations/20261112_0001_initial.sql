-- churnmod initial schema (PostgreSQL 16) — mirror of src/models/*
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    display_name VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    code VARCHAR(24) NOT NULL UNIQUE,
    company_name VARCHAR(80) NOT NULL,
    industry VARCHAR(24) NOT NULL,
    plan VARCHAR(24) NOT NULL,
    region VARCHAR(24) NOT NULL,
    seats INTEGER NOT NULL,
    monthly_fee DOUBLE PRECISION NOT NULL,
    csm_owner_email VARCHAR(120) NOT NULL,
    csm_owner_name VARCHAR(40) NOT NULL,
    contract_end DATE NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    churn_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_accounts_owner ON accounts (csm_owner_email);

CREATE TABLE IF NOT EXISTS account_features (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    month DATE NOT NULL,
    month_label VARCHAR(10) NOT NULL,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    churn_next_30d INTEGER NOT NULL DEFAULT 0,
    label_known INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_feature_account_month UNIQUE (account_id, month)
);
CREATE INDEX IF NOT EXISTS ix_features_month ON account_features (month);

CREATE TABLE IF NOT EXISTS feature_sets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    version INTEGER NOT NULL DEFAULT 1,
    description VARCHAR(255) NOT NULL DEFAULT '',
    target VARCHAR(48) NOT NULL DEFAULT 'churn_next_30d',
    train_months JSONB NOT NULL DEFAULT '[]'::jsonb,
    validation_month VARCHAR(10) NOT NULL,
    numeric_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    categorical_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_by VARCHAR(120) NOT NULL DEFAULT 'seed',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_runs (
    id SERIAL PRIMARY KEY,
    run_no INTEGER NOT NULL,
    label VARCHAR(64) NOT NULL UNIQUE,
    feature_set_id INTEGER NOT NULL REFERENCES feature_sets(id),
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    hyperparams JSONB NOT NULL DEFAULT '{}'::jsonb,
    coefficients JSONB NOT NULL DEFAULT '[]'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    roc_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    pr_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    threshold_scan JSONB NOT NULL DEFAULT '[]'::jsonb,
    standardization JSONB NOT NULL DEFAULT '{}'::jsonb,
    train_rows INTEGER NOT NULL DEFAULT 0,
    validation_rows INTEGER NOT NULL DEFAULT 0,
    train_positives INTEGER NOT NULL DEFAULT 0,
    warning VARCHAR(255) NOT NULL DEFAULT '',
    error_message VARCHAR(512) NOT NULL DEFAULT '',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_by VARCHAR(120) NOT NULL DEFAULT 'seed',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS score_batches (
    id SERIAL PRIMARY KEY,
    batch_no INTEGER NOT NULL,
    label VARCHAR(64) NOT NULL UNIQUE,
    model_run_id INTEGER NOT NULL REFERENCES model_runs(id),
    status VARCHAR(16) NOT NULL DEFAULT 'succeeded',
    lifecycle VARCHAR(16) NOT NULL DEFAULT 'draft',
    policy_version INTEGER,
    superseded_by INTEGER REFERENCES score_batches(id),
    policy_fingerprint VARCHAR(80) NOT NULL DEFAULT '',
    threshold DOUBLE PRECISION NOT NULL,
    budget_total DOUBLE PRECISION NOT NULL,
    cost_per_account DOUBLE PRECISION NOT NULL,
    retention_lift DOUBLE PRECISION NOT NULL,
    bands JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    results JSONB NOT NULL DEFAULT '[]'::jsonb,
    selected_count INTEGER NOT NULL DEFAULT 0,
    published BOOLEAN NOT NULL DEFAULT FALSE,
    published_by VARCHAR(120) NOT NULL DEFAULT '',
    published_at TIMESTAMP,
    created_by VARCHAR(120) NOT NULL DEFAULT 'seed',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 现行策略全局唯一：不可能同时留下两个 active 版本。
CREATE UNIQUE INDEX IF NOT EXISTS uq_score_batches_active_one
    ON score_batches (lifecycle)
    WHERE lifecycle = 'active';
-- 同一策略（同模型同参数）的未归档版本唯一：重复执行复用而非新增版本。
CREATE UNIQUE INDEX IF NOT EXISTS uq_score_batches_fingerprint_open
    ON score_batches (policy_fingerprint)
    WHERE lifecycle <> 'archived';

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    actor_email VARCHAR(120) NOT NULL DEFAULT '',
    actor_role VARCHAR(16) NOT NULL DEFAULT '',
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(32) NOT NULL DEFAULT '',
    resource_id VARCHAR(64) NOT NULL DEFAULT '',
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip VARCHAR(64) NOT NULL DEFAULT '',
    request_id VARCHAR(64) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
