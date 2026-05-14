# Phase 1.1 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 環境準備 (@INFRA)
- 建立 `data/raw/stock` 和 `data/raw/cb` 目錄。
- 建立 `src/crawlers/prototype` 目錄。
- 安裝 `requests`, `pandas`, `beautifulsoup4`, `plotly` (用於 EDA)。

### Step 2: 架構與介面設計 (@ARCH) -> ⏸️ Checkpoint 1
- 設計 `BaseCrawler` 抽象類別 (定義 `fetch`, `parse`, `save` 介面)。
- 定義 Raw Data 的檔案命名規範 (e.g., `{date}_{asset_type}.json`)。
- 規劃 TWSE 與 TPEx 的請求 Header 與頻率限制策略。

### Step 3: 原型實作 (@CODER)
- 實作 `TwseCrawler` (現股) 與 `TpexCbCrawler` (可轉債)。
- 實作工具函式 `convert_minguo_date()`。
- 撰寫 `run_discovery.py` 腳本，批量抓取測試數據。

### Step 4: 數據驗證與分析 (@ANALYST) -> ⏸️ Checkpoint 2
- 執行爬蟲抓取樣本數據。
- 使用 Pandas 進行 Profiling (檢查 Null, 0 值, 異常跳空)。
- 產出 `data_profile_report.md`。
- 根據數據特徵，修訂 DB Schema 建議。

