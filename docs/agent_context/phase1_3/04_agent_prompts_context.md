# Phase 1.3 - Agent 執行 Prompts

## @ARCH Prompt
請定義 Master Data 的標準 Schema：
1. **Stock List**: `symbol` (str), `name` (str), `industry` (str, optional)。
2. **CB List**: `symbol` (str), `name` (str), `underlying_symbol` (str, 預留), `issue_date` (date), `maturity_date` (date)。
3. 制定「過濾規則」：Stock 僅保留長度=4 的代碼；CB 需確保發行日/到期日格式正確轉為西元。

## @CODER Prompt
請實作主檔爬蟲：
1. **StockCrawler**: 請求 TWSE `STOCK_DAY_ALL` API。
   - 過濾邏輯：`len(symbol) == 4`。
   - 存檔：`data/raw/master/stock_list.csv`。
2. **CBCrawler**: 請求 TPEx `listed.html`。
   - 使用 `BeautifulSoup` 解析表格。
   - 提取 `發行日期` 與 `到期日期`，並用 Phase 1.1 的工具轉為 `YYYY-MM-DD`。
   - 存檔：`data/raw/master/cb_list.csv`。

## @ANALYST Prompt
請執行主檔驗證：
1. 讀取兩個 CSV。
2. 檢查 `2330` (台積電) 是否在 Stock List。
3. 檢查 `52694` (祥碩四) 是否在 CB List，且到期日 > 今天。
4. 隨機挑選 3 檔 CB，呼叫 `TpexHistoryCrawler` (Phase 1.1 產出)，確認能抓到日線。
5. 產出驗證報告。

