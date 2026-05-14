# Phase 3.2 - Agent 執行 Prompts

## @CODER Prompt - ChipProfiler
實作籌碼分析器：
1. `load_blacklist()`: 讀取 broker_blacklist.json，回傳 broker_id → risk_level 的 Dict
2. `match_top_buyers()`: 從 broker_breakdown 取今日買超前 5 名，比對黑名單
3. `calculate_risk_ratio()`: sum(suspect_volumes) / total_volume * 100%
4. `analyze()`: 整合流程，回傳 {symbol: {risk_ratio, matched_brokers, ...}}

## @CODER Prompt - RiskAssessor
實作風險評估器：
1. `assess()`:
   - premium < 2% AND risk < 10% → "S"
   - premium < 3% AND risk < 20% → "A"
   - premium < 5% AND risk < 30% → "B"
   - else → "C"
2. `generate_signal()`: S→BUY, A→BUY, B→HOLD, C→AVOID
3. `run_analysis()`: 從 daily_analysis_results 讀取溢價率，從 ChipProfiler 讀取風險佔比

## @ANALYST Prompt
驗證評級邏輯：
- 準備測試案例:
  - premium=1.5%, risk=5% → S
  - premium=2.5%, risk=15% → A
  - premium=4.0%, risk=25% → B
  - premium=6.0%, risk=5% → C
  - premium=1.5%, risk=35% → C
- 執行 pytest tests/test_risk_assessor.py -v
