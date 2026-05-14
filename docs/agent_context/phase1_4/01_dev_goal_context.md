# Phase 1.4 - 資料庫建置與數據入庫

**階段**: Phase 1.4 (Database Implementation)
**專案**: Project Gamma Surf
**背景**: Raw Data 目前散落在 CSV 檔案中，不利於跨時間序列分析與策略回測。

## 🎯 開發目標
建立高效的時間序列資料庫環境 (TimescaleDB)，定義標準 Schema，並開發自動化載入腳本 (Loader)，將 Phase 1.3/1.3.4 產出的 CSV 寫入資料庫。

### 核心產出
1.  **DB Environment**: 運行中的 PostgreSQL (含 TimescaleDB 插件) 實例 (Docker Compose)。
2.  **Schema Definition**: `sql/init.sql`，包含：
    - `market_master`: 儲存 Stock 與 CB 的靜態資料 (Symbol, Name, etc.)。
    - `market_daily`: 儲存 OHLCV 行情資料 (Hypertable)。
3.  **ETL Loader**: `src/etl/importer.py`，負責讀取 CSV -> 轉換 -> 寫入 DB。
4.  **Database Client**: `src/database/client.py`，封裝 DB 連線與操作 (SQLAlchemy)。

### 驗收標準
- [ ] `docker-compose up` 能成功啟動 DB，且 Python script 可連線。
- [ ] `market_master` 表中能查詢到 `cb_list_master.csv` 的內容。
- [ ] `market_daily` 表中能查詢到 `data/raw/daily/` 下的行情資料。
- [ ] **冪等性 (Idempotency)**：重複執行 ETL script 不會造成資料重複 (Upsert 機制生效)。

