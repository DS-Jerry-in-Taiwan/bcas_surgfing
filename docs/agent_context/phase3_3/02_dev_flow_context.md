# Phase 3.3 - 開發流程

## 📅 執行步驟

### Step 1: 報表格式設計 (@ARCH) → ⏸️ Checkpoint 1
**動作**: 
  - 設計 Markdown 報表範本 (S/A/B/C 分組、顏色、表格欄位)
  - 設計 Rich ASCII 表格佈局
**產出**: 報表設計稿 (Markdown 範例)

### Step 2: 實作 ReportFormatter (@CODER)
**檔案**: `src/reporters/`
**功能**:
  - `MarkdownReporter`: 讀取 daily_analysis_results + trading_signals → Markdown 字串
  - `RichFormatter`: Rich Table + Style (S 綠/A 藍/B 黃/C 紅)
  - `generate_report(date)` → str

### Step 3: 實作 Notifiers (@CODER)
**動作**:
  - `TelegramNotifier`: 使用 python-telegram-bot，token/chat_id 從環境變數讀取
  - `TerminalNotifier`: 直接 print 至 stdout
  - Slack: 直接使用既有 `framework/alerts.py` 的 SlackAlertBackend，不需重寫

### Step 4: 實作 EOD Pipeline (@CODER) → ⏸️ Checkpoint 2
**檔案**: `src/pipeline/eod_pipeline.py` + `src/run_eod_analysis.py`
```python
def run_eod(date: str):
    # Stage 1 (17:00): 爬蟲階段
    step_spiders()
    # Stage 2 (17:15): 分析階段
    PremiumCalculator.analyze(date)
    TechnicalAnalyzer.analyze(date)
    # Stage 3 (17:20): 風險階段
    ChipProfiler.analyze(date)
    RiskAssessor.run_analysis(date)
    # Stage 4 (17:30): 報表階段
    report = ReportFormatter.generate_report(date)
    Notifiers.broadcast(report)
```

### Step 5: 排程器整合 (@CODER/@INFRA)
**動作**: 更新 Go scheduler 配置
  - 新增 17:00 觸發 → `python src/run_eod_analysis.py --stage 1`
  - 新增 17:15 觸發 → `python src/run_eod_analysis.py --stage 2`
  - 新增 17:20 觸發 → `python src/run_eod_analysis.py --stage 3`
  - 新增 17:30 觸發 → `python src/run_eod_analysis.py --stage 4`

### Step 6: 端到端測試 (@ANALYST)
**測試**:
  - 完整 EOD 流程一鍵執行
  - Slack/Telegram 推播送達確認

## ⏰ 預估工時: 15-25 小時
