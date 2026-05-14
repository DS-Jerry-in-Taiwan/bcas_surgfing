# Phase 1.4.2 - 開發流程

## 📅 執行步驟

### Step 1: 資料庫 Schema 變更 (@ARCH)
- 修改 `sql/init.sql`，為 `market_daily` 表新增欄位。
- 執行 SQL 指令更新現有資料庫結構 (ALTER TABLE)。

### Step 2: Importer 邏輯對齊 (@CODER)
- 更新 `src/etl/importer.py` 的 `load_daily_quotes` 函式。
- 將 `convert_price` 等新欄位納入 Pandas 讀取與 SQL 寫入清單。
- 確保處理 `NaN` 到 `NULL` 的型態轉換。

### Step 3: 全管線回測驗證 (@ANALYST)
- 使用 `main_crawler.py` 跑一個小區間 (如 3 天) 的 `--task all`。
- 檢查資料庫記錄，比對數據與 `validate_and_enrich` 的輸出是否一致。

