# Phase 1.4 - 驗證清單

## 環境驗證
- [ ] Docker Compose Up 成功，Port 5432 可連線。
- [ ] TimescaleDB Extension 已啟用 (`\dx` 可見)。

## 功能驗證
- [ ] **Master Ingestion**: `cb_list_master.csv` 資料正確入庫。
- [ ] **Daily Ingestion**: 能批次讀取 `data/raw/daily/` 下的所有 CSV 並入庫。
- [ ] **Upsert 機制**: 重複執行 ETL，資料庫不會報 Primary Key Error，且筆數正確。

## 數據完整性
- [ ] `market_master` 筆數與 CSV 行數一致。
- [ ] `market_daily` 中的價格與成交量精度正確。

