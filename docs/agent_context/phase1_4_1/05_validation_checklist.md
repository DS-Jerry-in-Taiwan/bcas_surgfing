# Phase 1.4.1 - 驗證清單

## 代碼驗證
- [ ] `importer.py` 使用安全的方式讀取欄位 (不直接用 `[]` 存取可能不存在的 Key)。
- [ ] 執行時 Console 印出的 CSV Columns 符合預期 (只有 symbol, name)。

## 資料庫驗證
- [ ] Schema 中 `issue_date` 欄位允許 NULL。
- [ ] `market_master` 成功寫入資料。
- [ ] 查詢結果顯示缺失欄位為 NULL。

## 流程驗證
- [ ] Master 入庫成功後，Daily Quotes 的入庫流程也能順利執行。

