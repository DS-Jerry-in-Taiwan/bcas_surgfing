-- ============================================================
-- BCAS Quant v3.0.0 - Broker Blacklist Seed Data
-- ============================================================

INSERT INTO broker_blacklist (broker_id, broker_name, category, risk_level, notes) VALUES
    ('9200', '凱基-台北', 'DAY_TRADER', 'HIGH', '知名短線券商，頻繁當沖交易'),
    ('9800', '元大-台北', 'DAY_TRADER', 'HIGH', '短線交易量極大'),
    ('9100', '群益-台北', 'DAY_TRADER', 'HIGH', '當沖比率偏高'),
    ('9600', '富邦-台北', 'SUSPECTED', 'MEDIUM', '疑似集團交易'),
    ('9300', '統一-台北', 'SUSPECTED', 'MEDIUM', '需觀察其買賣模式'),
    ('9700', '永豐-台北', 'SUSPECTED', 'MEDIUM', '異常交易頻率'),
    ('9400', '兆豐-台北', 'SUSPECTED', 'MEDIUM', '需監控'),
    ('9500', '華南-台北', 'FLAGGED', 'LOW', '歷史紀錄異常'),
    ('9900', '國泰-台北', 'FLAGGED', 'LOW', '近期活躍度上升'),
    ('9150', '台新-台北', 'FLAGGED', 'LOW', '觀察清單')
ON CONFLICT (broker_id) DO UPDATE SET
    broker_name = EXCLUDED.broker_name,
    category = EXCLUDED.category,
    risk_level = EXCLUDED.risk_level,
    notes = EXCLUDED.notes;
