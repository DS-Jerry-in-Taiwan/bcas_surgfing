-- ============================================================
-- BCAS Quant v3.0.0 - EOD Analysis Tables DDL
-- 4 PostgreSQL tables for EOD analysis pipeline
-- ============================================================

-- 1. 券商買賣超明細
CREATE TABLE IF NOT EXISTS broker_breakdown (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    broker_id VARCHAR(16) NOT NULL,
    broker_name VARCHAR(64),
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    net_volume BIGINT DEFAULT 0,
    rank INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, broker_id)
);

-- 2. 盤後分析結果
CREATE TABLE IF NOT EXISTS daily_analysis_results (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    close_price NUMERIC(10,2),
    conversion_value NUMERIC(10,2),
    premium_ratio NUMERIC(6,4),
    technical_signal VARCHAR(32),
    risk_score NUMERIC(3,1),
    risk_level VARCHAR(16),
    broker_risk_pct NUMERIC(5,2),
    final_rating VARCHAR(16),
    is_junk BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol)
);

-- 3. 交易信號
CREATE TABLE IF NOT EXISTS trading_signals (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    signal_type VARCHAR(32) NOT NULL,  -- BUY / HOLD / AVOID
    confidence NUMERIC(3,2),
    entry_range TEXT,
    stop_loss NUMERIC(10,2),
    target_price NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, signal_type)
);

-- 4. 券商黑名單
CREATE TABLE IF NOT EXISTS broker_blacklist (
    broker_id VARCHAR(16) PRIMARY KEY,
    broker_name VARCHAR(64) NOT NULL,
    category VARCHAR(32),  -- DAY_TRADER / SUSPECTED / FLAGGED
    risk_level VARCHAR(16) DEFAULT 'HIGH',
    notes TEXT,
    added_date DATE DEFAULT CURRENT_DATE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_broker_breakdown_date ON broker_breakdown(date);
CREATE INDEX IF NOT EXISTS idx_broker_breakdown_symbol ON broker_breakdown(symbol);
CREATE INDEX IF NOT EXISTS idx_daily_analysis_date ON daily_analysis_results(date);
CREATE INDEX IF NOT EXISTS idx_trading_signals_date ON trading_signals(date);
