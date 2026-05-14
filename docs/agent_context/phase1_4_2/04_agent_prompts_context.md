# Phase 1.4.2 - Agent 執行 Prompts

## @ARCH Prompt
請為 `market_daily` 資料表設計新增欄位：
1. `convert_price` (NUMERIC): 儲存可轉債轉換價格。
2. `bond_short_name` (VARCHAR): 儲存債券簡稱。
3. 更新 `sql/init.sql` 並提供 `ALTER TABLE` 語句給使用者手動執行（或由 script 自動執行）。

## @CODER Prompt
請升級 `src/etl/importer.py`:
1. 在 `load_daily_quotes` 流程中，確認 DataFrame 包含 `convert_price` 等新欄位。
2. 更新 SQL Insert/Update 邏輯，將新欄位對齊到 DB 欄位。
3. 確保 `NaN` 數值不會導致 SQL 錯誤。

## @ANALYST Prompt
請執行全管線入庫驗證：
1. 執行 `python3 src/main_crawler.py --task all --date {最近交易日}`。
2. 檢查 SQL 查詢結果：
   `SELECT symbol, ts, close, convert_price FROM market_daily WHERE symbol='52694' LIMIT 1;`
3. 確認數據與 `data/clean/` 下的 CSV 一致。

