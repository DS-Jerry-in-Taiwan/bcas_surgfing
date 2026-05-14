# Phase 1.3.3 - 驗證清單

## API 請求驗證
- [ ] 使用 `POST` 方法請求 API Endpoint。
- [ ] Payload 中的日期格式為民國年 (e.g., `113/01/24`)。
- [ ] Headers 包含正確的 Referer。

## 回應驗證
- [ ] HTTP Status 為 200 OK。
- [ ] Content-Type 為 `text/csv` 或 `application/csv`。
- [ ] 內容無亂碼 (已正確從 Big5 轉為 UTF-8)。

## 檔案驗證
- [ ] 檔案大小 > 1KB。
- [ ] 第一列包含 "代碼" 或 "債券名稱" 等關鍵字。

