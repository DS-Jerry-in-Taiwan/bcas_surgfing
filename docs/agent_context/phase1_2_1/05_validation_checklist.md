# Phase 1.2.1 - 驗證清單

## 容錯機制驗證
- [ ] **DNS 錯誤處理**: 當 `isin.tpex.org.tw` 無法解析時，程式不應 Crash 退出。
- [ ] **Timeout 處理**: 請求應設定 Timeout (如 10s)，避免無限等待。
- [ ] **Partial Success**: 即使 TPEX 失敗，程式仍應產出 `data/raw/master/stock_list.csv` (含 TWSE 資料)。

## 流程連續性驗證
- [ ] **下游相容性**: 當 TPEX 清單為空時，`TargetSelector` 嘗試抽取 CB 樣本應優雅地跳過（或回傳空），而不是報錯。
- [ ] **日資料爬蟲**: 確認 TWSE 的標的（如 2330）在 TPEX 失敗後仍被正確爬取並驗證。

