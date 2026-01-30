-- 建立主檔表
CREATE TABLE IF NOT EXISTS cb_master (
    symbol VARCHAR(16) PRIMARY KEY,
    name VARCHAR(64),
    issue_date DATE,
    maturity_date DATE
);

-- 建立日行情表
CREATE TABLE IF NOT EXISTS cb_daily (
    symbol VARCHAR(16),
    date DATE,
    close NUMERIC,
    volume BIGINT,
    PRIMARY KEY (symbol, date)
);

-- 將 cb_daily 設為 hypertable
SELECT create_hypertable('cb_daily', 'date', if_not_exists => TRUE);