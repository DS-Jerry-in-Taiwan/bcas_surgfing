# Phase 1.2.2 - 日行情資料源確認與實作

**階段**: Phase 1.2.2 (Daily Data Discovery)
**專案**: Project Gamma Surf
**背景**: TPEx `day.html` 下載連結為 JS 動態生成，無法直接爬取。

## 🎯 開發目標
利用瀏覽器開發者工具 (DevTools) 找出「每日轉(交)換公司債買賣斷交易行情表」的真實 API URL 與參數，並實作自動化下載腳本。

### 核心產出
1.  **API 規格文件**: 記錄真實的 Request URL, Method (POST/GET), Headers, Payload。
2.  **原型下載器 (`fetch_tpex_csv.py`)**: 能模擬瀏覽器行為，下載指定日期的 CSV。
3.  **欄位驗證報告**: 確認下載的 CSV 包含策略所需的 `Symbol`, `Name`, `Open`, `High`, `Low`, `Close`, `Volume`。

### 驗收標準
- [ ] 成功下載一個非空的 CSV 檔案 (如 `daily_quote_sample.csv`)。
- [ ] 程式能處理常見的編碼問題 (Big5 vs UTF-8)。
- [ ] 確認 CSV 中包含關鍵標的 (如 `52694`) 的交易數據。

