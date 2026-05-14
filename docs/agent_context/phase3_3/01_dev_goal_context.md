# Phase 3.3 - 報表輸出 & 排程自動化

**階段**: Phase 3.3 (Reporting & Automation)
**專案**: BCAS Quant v3.0.0 → EOD Analytics 擴展

**背景**: 
對應高階規劃的「階段四：戰略輸出 (17:30)」與「Phase 3: 介面輸出與排程自動化」。
需將 Phase 3.1+3.2 的分析結果產出視覺化報表，並透過 Slack/Telegram 推播，
最後整合至 Go scheduler 實現全自動運行。

## 🎯 開發目標

1. **ReportFormatter**: 產出 Markdown / ASCII 報表 (Rich 上色)
2. **Notifiers 擴充**: Telegram 推播 (既有 Slack AlertManager 直接使用)
3. **EOD Pipeline**: 整合 4 階段為一鍵執行 (`src/run_eod_analysis.py`)
4. **Scheduler 整合**: Go scheduler 新增 17:00/15/20/30 多階段觸發

### 核心產出

| 產出 | 說明 |
|------|------|
| `src/reporters/base_reporter.py` | Reporter 基類 |
| `src/reporters/markdown_reporter.py` | Markdown 格式報表 |
| `src/reporters/formatter.py` | Rich 格式化 (顏色/表格) |
| `src/notifiers/telegram_notifier.py` | Telegram 推播 |
| `src/notifiers/terminal_notifier.py` | 終端機輸出 |
| `src/pipeline/eod_pipeline.py` | EOD 主管道編排 |
| `src/run_eod_analysis.py` | EOD 啟動腳本 |

### 報表格式 (Markdown)
```markdown
# CBAS 次日交易戰略清單
📅 日期: 2026-05-11

## 🟢 S 級 (強烈買入)
| 標的 | 現股價 | 溢價率 | 風險 | 進場區間 |
|------|--------|--------|------|---------|

## 🔵 A 級 (可布局)
...

## 🟡 B 級 (觀察)
...

## 🔴 C 級 (避開)
...
```

### 驗收標準
- [ ] ReportFormatter 能正確產出 Markdown/ASCII 報表
- [ ] Slack Notifier 成功推播 (使用既有 AlertManager)
- [ ] Telegram Notifier 成功推播 (新實作)
- [ ] `src/run_eod_analysis.py` 一鍵執行 4 階段成功
- [ ] Go scheduler 新增 EOD 排程 (17:00/15/20/30)
- [ ] 既有 10:00 排程不受影響
