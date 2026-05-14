# Phase 1.2.1 - 開發流程 (基於官網直連)

## 📅 執行步驟

### Step 1: 靜態清單爬取 (@CODER)
- **目標**: 建立 `cb_master.csv`。
- **來源**: `https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html`
- **實作**:
    - 使用 `requests` + `BeautifulSoup` 解析 HTML Table。
    - 提取：`代碼`, `名稱`, `發行日`, `到期日`。
    - 存檔：`data/raw/master/cb_master_tpex.csv`。

### Step 2: 歷史行情爬取 (@CODER)
- **目標**: 建立 `data/raw/daily/{symbol}.csv`。
- **來源**: `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php` (API Endpoint)。
- **實作**:
    - 觀察 Network Tab，確認發送 `POST` 請求的參數 (input_date, etc.)。
    - 實作 `fetch_daily_quotes(date)` 函式，支援下載指定日期的全市場 CSV。

### Step 3: 整合與驗證 (@ANALYST) -> ⏸️ Checkpoint 1
- **驗證**:
    1. 執行 Step 1，確認抓到 > 200 筆可轉債。
    2. 執行 Step 2，抓取「昨日」的行情。
    3. **關聯檢查**: 確認 Step 1 清單中的 `52694` 在 Step 2 的行情表中存在。

