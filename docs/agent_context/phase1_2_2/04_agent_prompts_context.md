# Phase 1.2.2 - Agent 執行 Prompts

## @ARCH Prompt
請分析 TPEx 日行情下載機制：
1. 根據使用者的觀察，這是一個動態請求。
2. 目標 URL 極可能是 `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php` (或其他類似)。
3. 請制定「Header 偽裝策略」，特別是 `Referer` 必須設定為 `https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day-quotes.html` (或 day.html)。

## @CODER Prompt
請實作 `fetch_tpex_csv.py`：
1. 使用 `requests.post()`。
2. URL 設定為分析出的 Endpoint。
3. Payload 需包含日期 (嘗試 `113/01/25` 格式) 與 `type=csv`。
4. **關鍵**: 處理 Response Encoding。嘗試 `response.encoding = 'cp950'` 或 `big5`，然後寫入檔案。
5. 存檔至 `data/raw/daily_samples/test_quote.csv`。

## @ANALYST Prompt
請驗證 CSV 內容：
1. 使用 Pandas 讀取 `test_quote.csv` (注意 encoding='cp950')。
2. 列印所有欄位名稱 (Columns)。
3. 檢查是否有 `代碼`, `名稱`, `收盤`, `成交量` 等欄位。
4. 檢查是否有 `52694` 這類代碼。
5. 產出驗證報告：這份檔案是否可用？缺什麼欄位？

