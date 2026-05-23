-- ============================================================
-- Migration 002: Create tracked_symbols table
-- Symbol Registry: persistent source of truth for tracked stocks
-- ============================================================

CREATE TABLE IF NOT EXISTS tracked_symbols (
    symbol      VARCHAR(10) PRIMARY KEY,
    source      VARCHAR(32) NOT NULL DEFAULT 'cb_master',
    added_at    DATE NOT NULL DEFAULT CURRENT_DATE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    notes       TEXT
);
