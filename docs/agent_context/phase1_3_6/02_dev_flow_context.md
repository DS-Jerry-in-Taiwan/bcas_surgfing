# Phase 1.3.6 - 開發流程

## 📅 執行步驟

### Step 1: 管線調度架構設計 (@ARCH)
- 定義 `DailyPipeline` 類別，封裝 `sync_master()`, `sync_daily()`, `clean_data()`, `ingest_db()` 四大步驟。
- 設計步驟間的數據傳遞機制 (Data Handoff)，優先使用 DataFrame 以減少 IO 損耗。

### Step 2: 整合腳本實作 (@CODER)
- 實作 `src/pipeline/daily_update.py`。
- 整合 `src.crawlers.master`, `src.crawlers.daily`, `src.etl.cleaner`, `src.etl.importer`。
- 增加「主檔預檢」邏輯：在行情入庫前，掃描當前 Daily CSV 的 Symbol 是否都在 Master 中。

### Step 3: 自動化日誌與錯誤處理 (@CODER)
- 實作全局 Exception Handling。
- 若 Master 同步失敗，立即終止 Daily 流程並發出 Critical Log。

### Step 4: 全管線整合測試 (@ANALYST)
- 模擬「全新環境」與「既有環境」的執行狀況。
- 驗證主檔與行情的 Join 準確度。

