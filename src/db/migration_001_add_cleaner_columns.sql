-- ============================================================
-- Migration 001: Add DataCleaner enrichment columns
-- GAP-02: DataCleaner writes to master_check/name/industry
--         but columns never existed in DB
-- ============================================================

-- stock_daily: enrichment from stock_master
ALTER TABLE stock_daily ADD COLUMN IF NOT EXISTS master_check VARCHAR(16);
ALTER TABLE stock_daily ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE stock_daily ADD COLUMN IF NOT EXISTS industry TEXT;

-- tpex_cb_daily: enrichment from cb_master
ALTER TABLE tpex_cb_daily ADD COLUMN IF NOT EXISTS master_check VARCHAR(16);
ALTER TABLE tpex_cb_daily ADD COLUMN IF NOT EXISTS cb_name_enriched TEXT;
ALTER TABLE tpex_cb_daily ADD COLUMN IF NOT EXISTS conversion_price_enriched TEXT;
