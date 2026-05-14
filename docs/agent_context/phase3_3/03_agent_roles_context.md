# Phase 3.3 - Agent 角色職責

## 📐 @ARCH
- **職責**: 設計報表格式 + Pipeline 階段劃分
- **重點**: 
  - Markdown 報表欄位定義 (S/A/B/C 分組、價格、溢價率、評級)
  - Rich 顏色配置 (S 綠/A 藍/B 黃/C 紅)
  - Pipeline 階段間錯誤傳遞策略

## 💻 @CODER
- **職責**: 實作報表 + 推播 + Pipeline
- **重點**:
  - **ReportFormatter**: 
    - MarkdownReporter: f-string 模板，無外部依賴
    - RichFormatter: 使用 rich.table + rich.style
  - **TelegramNotifier**: 
    - 使用 python-telegram-bot 非同步發送
    - token/chat_id 從環境變數讀取
    - 錯誤處理: API 失敗不阻塞主流程
  - **EOD Pipeline**:
    - 階段間非阻斷錯誤傳遞 (fail → log → continue)
    - 支援 --stage 參數 (1~4 單獨執行)

## 🧪 @ANALYST
- **職責**: 驗證報表可讀性 + 推播送達
- **重點**: 
  - 確認報表格式清晰 (顏色、分組、欄位)
  - 確認 Slack 與 Telegram 皆成功送達

## 🏗️ @INFRA
- **職責**: Go scheduler 排程配置更新
- **重點**: 
  - 新增 4 個 EOD cron 時間 (17:00/15/20/30)
  - 確定既有 10:00 排程不受影響
  - 環境變數: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
