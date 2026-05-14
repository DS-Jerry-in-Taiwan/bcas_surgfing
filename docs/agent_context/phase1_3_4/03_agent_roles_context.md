# Phase 1.3.4 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 無。

## 📐 @ARCH
- **職責**: 定義批量爬取的「禮貌策略 (Politeness Policy)」。
- **重點**: 
    - 嚴格要求加入隨機延遲，避免被 WAF (Web Application Firewall) 封鎖 IP。
    - 建議 Log 顯示進度條 (例如 `Processing 1/30: 2024-01-01...`)。

## 💻 @CODER
- **職責**: 修改入口檔案邏輯。
- **重點**:
    - **參數互斥**: 確保 CLI 邏輯清晰 (單日 vs 區間)。
    - **例外處理**: `tpex_daily.run()` 若拋出錯誤 (如連線逾時)，應 Log Warning 並 `continue`，不可 `break`。

## 🧪 @ANALYST
- **職責**: 驗證資料完整性。
- **重點**:
    - 檢查產出的 CSV 數量是否符合交易日天數 (例如 1個月約 20-22 個檔)。

