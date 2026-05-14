# Phase 1.3.5 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 準備 Processed 目錄。
- **重點**: 建立 `data/processed/daily/`。

## 📐 @ARCH
- **職責**: 定義「乾淨數據」的標準。
- **重點**: 
    - 確定清洗後的欄位名稱是否需要重命名 (Map to DB Schema)？還是留給 Importer 做？
    - 建議：Cleaner 只負責「去雜訊」與「數值格式化」，欄位 Mapping 留給 Importer。

## 💻 @CODER
- **職責**: 撰寫清洗邏輯與防呆機制。
- **重點**:
    - **關鍵字定位**: 使用 `代碼` 或 `Code` 作為錨點尋找表頭。
    - **數值清洗**: 移除數字中的 `,` (逗號)，避免 CSV 解析混淆。
    - **Logging**: 確保錯誤訊息包含「檔名」與「錯誤原因」。

## 🧪 @ANALYST
- **職責**: 驗證資料品質。
- **重點**:
    - 確保清洗後沒有遺失資料 (Row Count check)。
    - 測試 Importer 面對「空檔案」或「全亂碼檔案」時的反應 (應 Log 並 Skip)。

