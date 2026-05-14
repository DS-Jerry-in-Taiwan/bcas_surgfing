# Phase 1.3.2 - Agent 執行 Prompts

## @ARCH Prompt
請協助診斷 TPEx 爬蟲問題：
1. 指導 @CODER 在 `src/crawlers/daily/tpex_daily.py` 加入詳細 Debug Log：印出 URL, Headers, Payload, Status Code, 以及 **Response Raw Text 的前 500 字**。
2. 根據 User 的回報「無法解析 JSON」，極大機率是 Server 回傳了 HTML 錯誤頁。
3. 請重新檢查 TPEx 官網，確認 `Referer` 是否必須完全匹配。

## @CODER Prompt
請修復 `src/crawlers/daily/tpex_daily.py`：
1. **增強 Headers**: 設定真實的 `User-Agent` 和 `Referer`。
   - Referer: `https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day-quotes.html`
2. **日期格式檢查**: TPEx API 通常要求「民國年 (e.g., 113/01/25)」。確認程式是否傳了西元年？
3. **錯誤處理**: 
   - 如果 `response.status_code != 200`，拋出詳細錯誤。
   - 如果 `json.loads()` 失敗，將 `response.text` 寫入 `logs/error_response.html` 以便分析。

## @ANALYST Prompt
請驗證修復狀況：
1. 執行 `python src/main_crawler.py --task daily`。
2. 觀察 Log，確認 API 回傳 200 OK。
3. 檢查 `tpex_cb_daily.csv` 是否有數據。

