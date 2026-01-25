# Phase 1.2.1 - Agent 執行 Prompts

## @ARCH Prompt
請重新設計爬蟲架構，利用使用者提供的 TPEx 官網資源：
1. **Master Source**: `https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html`。這是一個 Server-Side Render 的 HTML 頁面，需解析 Table。
2. **Daily Source**: `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php`。這是一個回傳 JSON/CSV 的 API。
3. 設計 `CrawlerStrategy`：
   - `MasterCrawler`: 每日跑一次，更新靜態表 (是否有新發行)。
   - `DailyCrawler`: 每日收盤後跑一次，抓取當日行情。

## @CODER Prompt
請實作基於 TPEx 官網的爬蟲：
1. **Task A (Master)**: 撰寫 `src/crawlers/tpex_master.py`。
   - Target: `listed.html`。
   - Logic: 抓取表格中所有 `tr`，提取第 1 欄(代碼)與第 2 欄(名稱)。
   - Output: `data/raw/master/cb_list.csv`。

2. **Task B (Daily)**: 撰寫 `src/crawlers/tpex_daily.py`。
   - Target: `cb_daily.php` (參考 Network Request)。
   - Params: `l=zh-tw`, `d={YYYY/MM/DD}` (注意民國年/西元年格式)。
   - Output: `data/raw/daily/{date}_quotes.csv`。

## @ANALYST Prompt
請驗證新數據源的可靠性：
1. 執行 `tpex_master.py`，檢查 `cb_list.csv` 筆數是否合理 (>200)。
2. 執行 `tpex_daily.py` 抓取最近一個交易日。
3. 檢查關鍵標的 `52694` (祥碩四) 是否同時出現在 List 與 Daily Quote 中。
4. 產出 `docs/data_source_validation.md` 報告。

