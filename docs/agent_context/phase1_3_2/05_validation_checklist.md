# Phase 1.3.2 - 驗證清單

## Debug 資訊驗證
- [ ] 執行時能看到 HTTP Status Code (應為 200)。
- [ ] 若失敗，能看到 Server 回傳的原始文字 (HTML/Text)。

## API 行為驗證
- [ ] **Referer Check**: 確認 Header 中包含正確的 Referer。
- [ ] **Date Format**: 確認 Payload 發送的是民國年 (若 API 要求)。

## 結果驗證
- [ ] `tpex_cb_daily.csv` 大小 > 1KB。
- [ ] JSON 解析成功，無 `JSONDecodeError`。

