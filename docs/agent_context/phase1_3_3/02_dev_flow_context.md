# Phase 1.3.3 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 逆向分析 (人工/ARCH) -> ⏸️ Checkpoint 1
- **操作**:
    1. 開啟 [TPEx CB 日統計頁](https://www.tpex.org.tw/zh-tw/bond/info/statistics-cb/day.html)。
    2. 按 F12 (Network)。
    3. 點擊畫面上的「下載 CSV」圖示（或查詢按鈕）。
    4. 觀察 Network 中出現的請求。
- **預期發現**:
    - URL 可能是 `https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php` (或類似)。
    - Method 是 `POST`。
    - Payload 含有 `input_date` 和 `type=csv`。

### Step 2: 程式實作 (@CODER)
- **修改 `tpex_daily.py`**:
    - 放棄 URL 拼接 (`.csv`) 的寫法。
    - 改用 `requests.post(api_url, data=payload)`。
    - 必須加上 `Referer` Header，指向 `day.html` 頁面，否則會被擋。

### Step 3: 驗證 (@ANALYST) -> ⏸️ Checkpoint 2
- 執行爬蟲，檢查回傳的 Status Code。
- 如果是 200，檢查內容開頭是否為 CSV Header (如 "代碼","名稱"...)。

