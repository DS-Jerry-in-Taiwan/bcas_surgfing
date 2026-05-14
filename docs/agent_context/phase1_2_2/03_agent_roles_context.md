# Phase 1.2.2 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 準備存放下載樣本的目錄。
- **重點**: 建立 `data/raw/daily_samples/`。

## 📐 @ARCH
- **職責**: 指導 @CODER 如何進行 API 偽裝。
- **重點**: 
    - 根據使用者提供的線索，判斷這是一個 Form Data POST 請求。
    - 定義「正確資料」的標準：必須包含 OHLCV。

## 💻 @CODER
- **職責**: 撰寫 Python `requests` 程式碼。
- **重點**:
    - **編碼地獄**: TPEx CSV 99% 是 Big5 編碼，直接用 UTF-8 開啟會亂碼。需實作 `response.content.decode('big5')`。
    - **參數構建**: 確保 `input_date` 格式正確 (民國年 vs 西元年)。

## 🧪 @ANALYST
- **職責**: 擔任「品管員」。
- **重點**:
    - 下載下來的檔案可能有好幾種 (行情表、統計表)，必須確認哪一個才是對的。
    - 檢查關鍵字：需包含「轉換公司債」、「代碼」、「收盤」。

