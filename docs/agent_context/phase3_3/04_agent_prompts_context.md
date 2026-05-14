# Phase 3.3 - Agent 執行 Prompts

## @ARCH Prompt
請設計報表格式：
輸入: daily_analysis_results (含 premium_ratio, risk_score, final_rating) + trading_signals
輸出: 以下 Markdown 格式
```markdown
# CBAS 次日交易戰略清單
📅 日期: 2026-05-11

## 🟢 S 級 (強烈買入)
| 標的 | 現股價 | 溢價率 | 風險佔比 | 進場區間 |
|------|--------|--------|---------|---------|

## 🔴 C 級 (避開)
...
```
Rich 配色: S=green, A=blue, B=yellow, C=red

## @CODER Prompt - ReportFormatter
實作報表產生器：
1. `MarkdownReporter`: 讀取 DB → f-string 模板 → Markdown
2. `RichFormatter`: 使用 rich.table.Table + rich.style 上色
3. `generate_report(date)`: 整合流程 → 回傳報表字串 + 同時輸出至終端

## @CODER Prompt - TelegramNotifier
實作 Telegram 推播：
1. 使用 python-telegram-bot
2. 初始化: bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
3. send(message): await bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=message)
4. 錯誤處理: try-except → log error, 不拋出

## @CODER Prompt - EOD Pipeline
實作 eod_pipeline.py：
```python
def run_eod(date: str, stage: int = None):
    stages = {
        1: ("爬蟲階段", run_spiders),
        2: ("分析階段", run_analytics),
        3: ("風險階段", run_risk_assessment),
        4: ("報表階段", run_reporting),
    }
    for s, (name, func) in stages.items():
        if stage and s != stage:
            continue
        logger.info(f"[{s}/4] {name} 開始")
        try:
            func(date)
            logger.info(f"[{s}/4] {name} 完成 ✅")
        except Exception as e:
            logger.error(f"[{s}/4] {name} 失敗 ❌: {e}")
```

## @INFRA Prompt - Scheduler 更新
更新 Go scheduler 配置：
1. 複製既有 cron 模式，新增 EOD 時間
2. 環境變數新增 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
3. 更新 docker-compose.yml 傳遞新環境變數
