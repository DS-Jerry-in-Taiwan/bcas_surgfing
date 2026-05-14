# Phase 1.3.3 - TPEx 日行情動態下載實作

**階段**: Phase 1.3.3 (Dynamic Download Fix)
**專案**: Project Gamma Surf
**背景**: 嘗試直接下載 `RSta...csv` 失敗 (404)，確認該網站採用動態生成機制。
**目標網址**: `https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day.html`

## 🎯 開發目標
透過瀏覽器開發者工具 (DevTools) 的 Network 分析，找出點擊「下載 CSV」時實際觸發的 **API 請求 (Request)**。並實作 Python 腳本來模擬這個請求。

### 核心產出
1.  **API 規格**: 確認是 POST 還是 GET？URL 是什麼？Payload 包含哪些參數 (如 `input_date`, `type`, `response`)？
2.  **修正後的爬蟲**: `src/crawlers/daily/tpex_daily.py` (v2)。
3.  **驗證檔案**: 成功下載並儲存 `tpex_cb_daily_{date}.csv`。

### 驗收標準
- [ ] 爬蟲不再回傳 404 錯誤。
- [ ] 下載的內容是 CSV 文字格式 (Content-Type: text/csv)，而非 HTML 錯誤頁。
- [ ] 程式能自動處理日期格式轉換 (如網頁要求 `113/01/24`，程式能將 `2024-01-24` 自動轉換)。

