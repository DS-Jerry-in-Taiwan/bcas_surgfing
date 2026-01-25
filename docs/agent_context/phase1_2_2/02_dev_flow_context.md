# Phase 1.2.2 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 逆向工程分析 (@ARCH) -> ⏸️ Checkpoint 1
- **人工/輔助操作**:
    1. 開啟 TPEx `day.html`。
    2. 開啟 Network Tab。
    3. 點擊下載 CSV，捕捉 Request。
- **產出**: 確立 API Endpoint (例如可能是 `cb_daily.php` 或其他) 與必要參數。

### Step 2: 下載器實作 (@CODER)
- 撰寫 `src/crawlers/daily/tpex_csv_fetcher.py`。
- 重點實作：
    - 偽裝 Headers (User-Agent, Referer)。
    - 處理 Response 的編碼 (台灣金融資料常用 `cp950` / `big5`)。
    - 將下載的 Raw Content 存為 `data/raw/daily/sample.csv`。

### Step 3: 數據內容驗證 (@ANALYST) -> ⏸️ Checkpoint 2
- 讀取 `sample.csv`。
- 檢查欄位名稱 (Header) 是否符合預期。
- 檢查數據內容：成交量是否為數值？價格是否正常？
- 判斷這份 CSV 是否就是我們要的「日行情表」。

