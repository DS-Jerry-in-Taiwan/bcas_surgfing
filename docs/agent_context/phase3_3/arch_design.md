# Phase 3.3 - 報表輸出 & 排程自動化架構設計

## 概述
Phase 3.3 對應高階規劃的「階段四：戰略輸出 (17:30)」與「Phase 3: 介面輸出與排程自動化」。
包含 ReportFormatter (視覺化報表)、Notifiers (推播通知)、EOD Pipeline (全自動編排)。

## 既有資源
- `framework/alerts.py`: AlertManager + **SlackAlertBackend** ✅ (直接使用，不需重寫)
- Go scheduler: Cron-based 排程 ✅ (擴充 EOD 時間)

## 新增架構
```
src/
├── reporters/               [NEW]
│   ├── base_reporter.py     基類
│   ├── markdown_reporter.py  Markdown 格式
│   └── formatter.py          Rich 格式化
├── notifiers/               [NEW]
│   ├── telegram_notifier.py  Telegram 推播
│   └── terminal_notifier.py  終端輸出
├── pipeline/
│   └── eod_pipeline.py      [NEW] EOD 主管道
└── run_eod_analysis.py      [NEW] EOD 啟動腳本
```

## 報表格式

```markdown
# CBAS 次日交易戰略清單
📅 日期: 2026-05-11

## 🟢 S 級 (強烈買入)
| 標的 | 收盤價 | 溢價率 | 風險佔比 | 信號 |
|------|--------|--------|---------|------|
| 3680 | 452.0  | 1.2%   | 5.3%    | BUY  |

## 🔴 C 級 (避開)
| 標的 | 收盤價 | 溢價率 | 風險佔比 | 信號 |
|------|--------|--------|---------|------|
| 6509 | 78.5   | 6.8%   | 12.1%   | AVOID|
```

## Pipeline 流程

```
17:00 ─ Stage 1: 爬蟲 (Phase 3.0 spiders)
                      │ collect_only + validate + flush
17:15 ─ Stage 2: 分析 (Phase 3.1)
                      │ PremiumCalculator + TechnicalAnalyzer
17:20 ─ Stage 3: 風險 (Phase 3.2)
                      │ ChipProfiler + RiskAssessor
17:30 ─ Stage 4: 報表 (Phase 3.3)
                      │ ReportFormatter + Notifiers
                      │
                      ▼
                Slack / Telegram / Terminal
```

## 排程器配置

```yaml
# 既有 (10:00 排程)
- cron: "0 10 * * 1-5"
  command: "python src/run_daily.py"

# 新增 EOD 排程
- cron: "0 17 * * 1-5"
  command: "python src/run_eod_analysis.py --stage 1"  # 爬蟲
- cron: "15 17 * * 1-5"
  command: "python src/run_eod_analysis.py --stage 2"  # 分析
- cron: "20 17 * * 1-5"
  command: "python src/run_eod_analysis.py --stage 3"  # 風險
- cron: "30 17 * * 1-5"
  command: "python src/run_eod_analysis.py --stage 4"  # 報表
```
