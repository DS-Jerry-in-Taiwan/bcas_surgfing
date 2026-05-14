# Phase 1.4 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 負責 Docker 環境配置。
- **重點**: `docker-compose.yml` 需設定 Volume Persistence (資料持久化)，確保 Container 重啟後資料還在。

## 📐 @ARCH
- **職責**: 設計資料庫正規化結構。
- **重點**: 
    - 使用 `TimescaleDB` 優化時間序列查詢。
    - 價格欄位使用 `DECIMAL` 或 `NUMERIC` 以確保精度。

## 💻 @CODER
- **職責**: 撰寫 Python ETL 邏輯。
- **重點**:
    - **批次寫入**: 使用 `executemany` 或 SQLAlchemy 的 batch insert，避免逐筆寫入導致效能低落。
    - **日期處理**: 確保 CSV 中的日期字串正確轉換為 Python `datetime` 物件再入庫。
    - **錯誤容忍**: 單一 CSV 損壞不應中斷整個匯入流程。

## 🧪 @ANALYST
- **職責**: 擔任 DBA 進行驗收。
- **重點**:
    - 驗證 `ts` 欄位時區是否正確 (建議統一為 UTC 或 +8，需一致)。
    - 檢查 Master 與 Daily 之間的關聯 (Symbol 是否對應)。

