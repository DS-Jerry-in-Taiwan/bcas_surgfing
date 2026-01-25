# Phase 1.3 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: Stock Master 實作 (@CODER)
- **來源**: `https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json`
- **邏輯**: 下載 JSON -> 提取 `data` 欄位 -> 過濾出代碼長度為 4 的普通股 -> 存檔。

### Step 2: CB Master 實作 (@CODER)
- **來源**: `https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html`
- **邏輯**:
    1. 使用 `requests` 獲取 HTML。
    2. 使用 `BeautifulSoup` 尋找 Table (通常 class 包含 `table`)。
    3. 遍歷 `tr`，提取 [代碼, 名稱, 發行日, 到期日]。
    4. 清洗日期格式 (民國轉西元) -> 存檔。

### Step 3: 整合驗證 (@ANALYST) -> ⏸️ Checkpoint 1
- **完整性檢查**: 統計 CSV 筆數是否合理 (Stock > 1000, CB > 200)。
- **關鍵標的檢查**: 確認 `2330` 與 `52694` 在清單內。
- **連通性測試**: 拿 `52694` 去呼叫 Phase 1.1 的 `fetch_daily`，確認能抓到資料。

