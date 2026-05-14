# Phase 1.3.3 - Agent 執行 Prompts

## @ARCH Prompt
請指導 @CODER 進行 API 模擬：
1. **URL**: 根據網頁結構，API 端點極高機率為 `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php`。
2. **Method**: `POST`。
3. **Payload 建議**:
   - `input_date`: 需將輸入的 `YYYY-MM-DD` 轉為民國年 `YYY/MM/DD` (例如 `115/01/24`)。
   - `type`: `csv`。
   - `response`: `csv` (有時需要此參數)。
4. **Header 建議**:
   - `Referer`: `https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day.html` (必須完全一致)。

## @CODER Prompt
請重寫 `tpex_daily.py` 的 `fetch()` 邏輯：
1. **移除**: 所有關於 `RSta...csv` 的檔名拼接邏輯。
2. **新增**: `_convert_to_minguo_date(date_str)` 輔助函式。
3. **實作**: 使用 `requests.post()` 發送請求。
   - URL: `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php`
   - Data: `{'input_date': minguo_date, 'type': 'csv'}`
   - Headers: 包含 User-Agent 與 Referer。
4. **存檔**: 接收 `response.content`，用 `cp950` 解碼，再寫入 CSV 檔案。

## @ANALYST Prompt
請驗證修復結果：
1. 執行 `python src/main_crawler.py --task daily --date 2024-01-24`。
2. 檢查 Log：Status Code 是否為 200？
3. 檢查檔案：`data/raw/daily/` 下是否有檔案？內容是否為 CSV 格式？

