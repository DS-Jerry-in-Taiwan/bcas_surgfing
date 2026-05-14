# Phase 1.3.2 - TPEx 日行情爬蟲排查與修復

**階段**: Phase 1.3.2 (Debug & Fix)
**專案**: Project Gamma Surf
**背景**: `main_crawler.py` 執行後顯示 `TPEx CB Daily: 無法解析 JSON`，導致 CSV 檔案為空。

## 🎯 開發目標
透過詳細的 Log 與 Raw Response 分析，診斷 TPEx API 請求失敗的根本原因，並修正 `src/crawlers/daily/tpex_daily.py`，確保能穩定抓取 JSON 數據。

### 核心產出
1.  **診斷報告**: 確認是 HTTP 403 (被擋)、格式錯誤 (HTML returned)、還是編碼問題。
2.  **修正後的代碼**: `src/crawlers/daily/tpex_daily.py`。
3.  **驗證結果**: 成功產出非空的 `data/raw/daily/tpex_cb_daily_{date}.csv`。

### 驗收標準
- [ ] 執行爬蟲不再拋出 `JSONDecodeError`。
- [ ] 產出的 CSV 包含 `代碼`, `名稱`, `收盤`, `成交量` 等欄位。
- [ ] 模擬連續請求（如抓取近 3 天）也能成功（驗證 Session 或 Headers 是否正確維持）。

