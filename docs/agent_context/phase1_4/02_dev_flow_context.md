# Phase 1.4 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 環境與 Schema 設計 (@ARCH) -> ⏸️ Checkpoint 1
- **DB 選型**: PostgreSQL 14+ with TimescaleDB。
- **Schema 設計**:
    - `market_master`: `symbol` (PK), `asset_type` ('STOCK', 'CB'), `name`, `meta_data` (JSONB)。
    - `market_daily`: `ts` (PK, TIMESTAMPTZ), `symbol` (PK), `open`, `high`, `low`, `close`, `volume`。
    - **TimescaleDB**: 對 `market_daily` 執行 `create_hypertable`。
- **產出**: `docker-compose.yml` 與 `sql/init.sql`。

### Step 2: 資料庫連線與 Loader 實作 (@CODER)
- **Task A**: 實作 `src/database/client.py` (DB 連線管理)。
- **Task B**: 實作 `src/etl/importer.py`。
    - 功能 1 `import_master()`: 讀取 `cb_list_master.csv`，標記 `asset_type='CB'` 入庫。
    - 功能 2 `import_daily()`: 遍歷 `data/raw/daily/*.csv`，解析日期與數值，批次寫入 `market_daily`。
    - **關鍵**: 必須使用 `ON CONFLICT DO UPDATE` (Upsert) 處理重複資料。

### Step 3: 整合測試與查詢驗證 (@ANALYST) -> ⏸️ Checkpoint 2
- **執行**: 啟動 Docker -> 執行 ETL Importer。
- **驗證**:
    1. SQL 統計 `market_master` 筆數是否等於 CSV 行數。
    2. SQL 查詢特定 CB 的 K 線資料，比對 CSV 是否一致。
    3. 驗證 Upsert：重複執行 ETL，確認 DB 筆數未異常增加。

