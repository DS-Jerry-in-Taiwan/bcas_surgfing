# Phase 1.4 - Agent 執行 Prompts

## @ARCH Prompt
請設計 PostgreSQL (TimescaleDB) 架構：
1. 建立 `sql/init.sql`：
   - 定義 `market_master` 表：`symbol` (VARCHAR, PK), `asset_type` (VARCHAR), `name` (VARCHAR), `meta_data` (JSONB)。
   - 定義 `market_daily` 表：`ts` (TIMESTAMPTZ, PK), `symbol` (VARCHAR, PK), `open`, `high`, `low`, `close` (NUMERIC), `volume` (BIGINT)。
   - 啟用 TimescaleDB：`SELECT create_hypertable('market_daily', 'ts');`。
2. 建立 `docker-compose.yml`：
   - Image: `timescale/timescaledb:latest-pg14`。
   - Ports: `5432:5432`。
   - Volume: `./data/pgdata:/var/lib/postgresql/data`。

## @CODER Prompt
請實作 ETL Importer：
1. `src/database/client.py`: 使用 SQLAlchemy 建立 Engine 與 Session。
2. `src/etl/importer.py`:
   - `load_cb_master()`: 讀取 `data/raw/master/cb_list_master.csv`，寫入 `market_master`。
   - `load_daily_quotes()`: 讀取 `data/raw/daily/*.csv`。注意 CSV 檔名可能包含日期，或需從內容解析日期。
   - 使用 Upsert 語法 (`INSERT ... ON CONFLICT (ts, symbol) DO UPDATE ...`)。
3. 加入 `tqdm` 顯示匯入進度。

## @ANALYST Prompt
請驗證 DB 建置成果：
1. 確保 Container 正常運行。
2. 執行 `python -m src.etl.importer` (或對應入口)。
3. 連線 DB 執行驗證 SQL：
   - `SELECT count(*) FROM market_master WHERE asset_type='CB';`
   - `SELECT * FROM market_daily ORDER BY ts DESC LIMIT 5;`
4. 測試重複匯入，確認資料庫筆數不變。

