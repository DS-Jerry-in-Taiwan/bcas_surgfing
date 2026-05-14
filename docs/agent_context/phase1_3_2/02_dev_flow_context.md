# Phase 1.3.2 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 診斷與重現 (@ARCH) -> ⏸️ Checkpoint 1
- **行動**: 修改爬蟲，暫時將 `try-except` 中的 `response.text` 印出來（或寫入 debug log）。
- **分析**: 
    - 如果看到 `<html...>`：代表被導向錯誤頁面 (參數錯) 或被擋 (缺 Headers)。
    - 如果看到亂碼：代表 Encoding 錯誤 (需用 CP950/Big5)。
    - 如果 Status Code 不是 200：代表被 Firewall 攔截。

### Step 2: 修正實作 (@CODER)
- **修正 Headers**: 確保 `User-Agent` 與 `Referer` (`https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day-quotes.html`) 設定正確。
- **修正 Payload**: 檢查 `input_date` 格式 (民國年 `113/01/24` vs 西元年 `2024/01/24`)。
- **修正解析邏輯**: 確保正確處理 JSON 層級 (如 `result` vs `aaData`)。

### Step 3: 驗證修復 (@ANALYST) -> ⏸️ Checkpoint 2
- 執行 `python src/main_crawler.py --task daily`。
- 檢查 `data/raw/daily/` 下的檔案內容。

