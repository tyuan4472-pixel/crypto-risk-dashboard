-- 币种评分主表
CREATE TABLE IF NOT EXISTS token_scores (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    total_score DECIMAL(5,2) NOT NULL,
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('极高','高','中','低','极低')),

    -- 8 个核心维度 (0-100)
    liquidity_score DECIMAL(5,2),
    volatility_score DECIMAL(5,2),
    concentration_score DECIMAL(5,2),
    fundamental_score DECIMAL(5,2),
    sentiment_score DECIMAL(5,2),
    compliance_score DECIMAL(5,2),
    security_score DECIMAL(5,2),
    macro_score DECIMAL(5,2),

    -- 元数据
    market_cap_usd DECIMAL(20,2),
    volume_24h_usd DECIMAL(20,2),
    price_usd DECIMAL(20,8),

    -- 风险明细 (JSON)
    risk_details JSONB DEFAULT '[]',
    sentiment_summary TEXT,

    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 加速查询
CREATE INDEX IF NOT EXISTS idx_token_scores_symbol ON token_scores(symbol);
CREATE INDEX IF NOT EXISTS idx_token_scores_risk_level ON token_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_token_scores_evaluated_at ON token_scores(evaluated_at);
CREATE INDEX IF NOT EXISTS idx_token_scores_total ON token_scores(total_score DESC);

-- 币种报告表（详细调研报告缓存）
CREATE TABLE IF NOT EXISTS token_reports (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    report_type VARCHAR(20) NOT NULL DEFAULT 'full',  -- full | summary | alert
    title VARCHAR(200),
    content TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trigger_source VARCHAR(20) DEFAULT 'scheduled'  -- scheduled | manual
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_token_reports_unique ON token_reports(symbol, report_type, (generated_at::date));

CREATE INDEX IF NOT EXISTS idx_token_reports_symbol ON token_reports(symbol);
CREATE INDEX IF NOT EXISTS idx_token_reports_generated ON token_reports(generated_at DESC);

-- 调度任务日志
CREATE TABLE IF NOT EXISTS scan_logs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL,
    total_tokens INT NOT NULL,
    completed INT NOT NULL DEFAULT 0,
    failed INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);
