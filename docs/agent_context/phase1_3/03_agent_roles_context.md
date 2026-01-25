# Phase 1.3 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 準備 Master Data 存放目錄。
- **重點**: 確保 `data/raw/master/` 目錄存在且乾淨。

## 📐 @ARCH
- **職責**: 定義 Master Data 的 Schema 標準。
- **重點**:
    - 統一欄位名稱：`symbol` (字串, 補零), `name`, `issue_date` (YYYY-MM-DD), `maturity_date` (YYYY-MM-DD)。
    - 確保 Stock 與 CB 的 `symbol` 格式一致 (如 `2330` vs `23301`)。

## 💻 @CODER
- **職責**: 實作兩個 Master Fetcher。
- **重點**:
    - **Stock**: 需過濾掉 6 碼的權證或 ETF (視策略需求，目前專注普通股)。
    - **CB**: 解析 HTML 時需處理分頁或一次顯示全部 (通常網址參數可控制)。
    - **編碼**: 注意 TPEx 網頁可能為 UTF-8 或 Big5。

## 🧪 @ANALYST
- **職責**: 驗證清單品質。
- **重點**:
    - 檢查是否有「已到期」但還在清單上的 CB (過期資料會導致日線爬取失敗)。
    - 產出 `master_data_report.md`。

