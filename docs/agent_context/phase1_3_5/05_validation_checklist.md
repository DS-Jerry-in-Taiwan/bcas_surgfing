# Phase 1.3.5 - 驗證清單

## 清洗功能驗證
- [ ] Processed CSV 第一行為 Header，無上方雜訊。
- [ ] 數值欄位中的千分位逗號已移除。
- [ ] 檔案編碼統一為 UTF-8。

## Importer 強健性驗證
- [ ] 讀取標準 CSV 正常入庫。
- [ ] **防呆測試**: 遇到格式錯誤的檔案，Log 顯示 Error，但程式繼續執行下一檔。

## 資料一致性
- [ ] Raw CSV 的資料筆數 == Processed CSV 的資料筆數。

