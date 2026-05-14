# Phase 3.3 - 驗證清單

## ✅ ReportFormatter
- [ ] Markdown 報表格式正確 (S/A/B/C 分組)
- [ ] ASCII 表格輸出正確 (Rich Table)
- [ ] S 級綠色 / A 級藍色 / B 級黃色 / C 級紅色
- [ ] 包含所有必要欄位
- [ ] 無資料時輸出合理訊息 (非空白/非錯誤)

## ✅ Notifiers
- [ ] TerminalNotifier 正常輸出至 stdout
- [ ] SlackNotifier 成功推播 (既有 AlertManager)
- [ ] TelegramNotifier 成功推播 (新實作)
- [ ] token 從環境變數讀取 (非寫死在代碼)
- [ ] API 失敗時 log error 不中斷主流程

## ✅ EOD Pipeline
- [ ] `python src/run_eod_analysis.py` 一鍵執行 4 階段成功
- [ ] `--stage 1` 只執行爬蟲階段
- [ ] `--stage 4` 只執行報表階段
- [ ] 階段失敗時不阻斷後續階段
- [ ] 最終報表成功輸出至終端

## ✅ Scheduler
- [ ] Go scheduler 新增 17:00 觸發
- [ ] Go scheduler 新增 17:15 觸發
- [ ] Go scheduler 新增 17:20 觸發
- [ ] Go scheduler 新增 17:30 觸發
- [ ] 既有 10:00 排程不受影響
