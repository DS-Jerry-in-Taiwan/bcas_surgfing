-- ============================================================
-- Migration 003: Add instrument filter columns
-- 標的到期日 & 停止轉換期過濾機制
-- ============================================================

ALTER TABLE daily_analysis_results 
  ADD COLUMN IF NOT EXISTS days_to_expiry INTEGER;

ALTER TABLE daily_analysis_results 
  ADD COLUMN IF NOT EXISTS is_stopped BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_dar_filter 
  ON daily_analysis_results(date, days_to_expiry, is_stopped);
