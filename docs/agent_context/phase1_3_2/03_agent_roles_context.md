# Phase 1.3.2 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 無。

## 📐 @ARCH
- **職責**: 分析錯誤日誌 (Error Log Analysis)。
- **重點**: 
    - 判斷是否為 Cloudflare 或 WAF 攔截 (通常會回傳 403 或 JavaScript Challenge)。
    - 確認 TPEx API 是否更換了 URL (需重新比對 DevTools)。

## 💻 @CODER
- **職責**: 修改爬蟲代碼。
- **重點**:
    - **Debug Mode**: 在 `fetch()` 函式中加入 `print(f"Status: {response.status_code}, Body prefix: {response.text[:200]}")` 以便除錯。
    - **強健性**: 加入 Retry 機制 (使用 `requests.adapters.HTTPAdapter`)。

## 🧪 @ANALYST
- **職責**: 驗證修復結果。
- **重點**:
    - 確認 CSV 資料筆數合理 (例如 > 200 筆)，而非只有檔頭。

