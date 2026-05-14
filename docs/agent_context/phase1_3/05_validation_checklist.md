# Phase 1.3 - 驗證清單

## 檔案產出驗證
- [ ] `data/raw/master/stock_list.csv` 存在且大小 > 10KB。
- [ ] `data/raw/master/cb_list.csv` 存在且大小 > 5KB。

## 數據內容驗證
- [ ] **Stock**: 筆數 > 1,500，無 6 碼代號 (如 0050)。
- [ ] **CB**: 筆數 > 200，包含 [發行日, 到期日] 欄位。
- [ ] **日期格式**: 所有日期欄位皆為 `YYYY-MM-DD`，無 `113/` 開頭。

## 系統整合驗證
- [ ] **抽樣測試**: 從 CB List 抽出的代碼，能成功組出 TPEx 日行情 API 的查詢參數，且 API 回傳 200 OK。

