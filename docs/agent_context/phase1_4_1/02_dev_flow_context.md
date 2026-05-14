# Phase 1.4.1 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 診斷 CSV 結構 (@ARCH) -> ⏸️ Checkpoint 1
- **行動**: 寫一個臨時腳本或使用 Pandas 讀取 `data/raw/master/cb_list_master.csv` 並印出 `df.columns`。
- **決策**: 確認欄位名稱是否為 `symbol`, `name` (可能沒有 issue_date)。

### Step 2: 修正 Importer 邏輯 (@CODER)
- **修改 `src/etl/importer.py`**:
    - 在讀取 CSV 後，檢查缺失欄位。
    - 若 `issue_date` 不存在，則補上 `None` 或 `NaT`。
    - 修改 Upsert 邏輯，確保 SQL 語句能處理 NULL 值。

### Step 3: 檢查 DB Schema 限制 (@ARCH)
- **確認 `sql/init.sql`**:
    - `issue_date` 和 `maturity_date` 是否被設為 `NOT NULL`？
    - 如果是，必須修改 Schema 移除 `NOT NULL` 限制，因為我們的資料源暫時無法提供這些資訊。

### Step 4: 驗證修復 (@ANALYST) -> ⏸️ Checkpoint 2
- 重新執行 ETL。
- 查詢 DB 確認入庫成功。

