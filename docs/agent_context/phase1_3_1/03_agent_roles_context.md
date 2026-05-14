# Phase 1.3.1 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 建立 Log 目錄。
- **重點**: 確保 `logs/` 目錄存在，並設定 `.gitignore` 忽略 `*.log`。

## 📐 @ARCH
- **職責**: 設計 CLI 介面與 Error Handling 策略。
- **重點**: 
    - 決定當 Master 爬取失敗時，是否阻斷 Daily 爬取？(建議：是，因為 Daily 依賴 Master 清單)。
    - 設計 Log 格式：`[Time] [Level] [Module] Message`。

## 💻 @CODER
- **職責**: 撰寫膠水程式碼 (Glue Code) 與重構。
- **重點**:
    - **Refactoring**: 這是本階段最繁瑣的部分，需確保不破壞原有邏輯。
    - **Import**: 使用 Absolute Import (e.g., `from src.crawlers.master import cb_master`)。

## 🧪 @ANALYST
- **職責**: 驗證流程順暢度。
- **重點**:
    - 測試「未來日期」或「假日」，確認程式不會 Crash，而是優雅地 Log Warning。

