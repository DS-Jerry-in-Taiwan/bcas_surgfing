# Phase 1.4.1 - 資料入庫除錯與欄位對齊

**階段**: Phase 1.4.1 (Debug Ingestion)
**專案**: Project Gamma Surf
**背景**: `importer.py` 在讀取 `cb_list_master.csv` 時發生 `KeyError: 'issue_date'`，因為該 CSV 是由日行情反推生成，天然缺乏發行/到期日資訊。

## 🎯 開發目標
增強 ETL Loader 的健壯性 (Robustness)，使其能夠容忍缺失的非關鍵欄位 (Optional Fields)，並將這些欄位在資料庫中設為 `NULL`。

### 核心產出
1.  **診斷資訊**: 確認目前 CSV 到底有哪些欄位。
2.  **修正後的 Loader**: `src/etl/importer.py` (v2)。
    - 使用 `.get()` 或 `if column in df` 的方式讀取欄位。
    - 確保資料庫 Schema (`init.sql`) 允許這些日期欄位為 `NULL`。
3.  **驗證結果**: 成功執行 Importer，且 DB 中 `market_master` 表有資料 (日期欄位為空)。

### 驗收標準
- [ ] 執行 `python -m src.etl.importer` 不再報錯。
- [ ] 資料庫查詢 `SELECT * FROM market_master WHERE asset_type='CB'` 能看到數據。
- [ ] 若 CSV 缺 `issue_date`，DB 中該欄位應顯示為 `NULL` (None)。

