# Phase 3.2 - 驗證清單

## ✅ ChipProfiler
- [ ] load_blacklist() 正確載入 ≥10 筆黑名單
- [ ] match_top_buyers() 能匹配已知短線券商
- [ ] 無匹配時回傳空列表
- [ ] calculate_risk_ratio() 計算正確
- [ ] analyze() 輸出格式完整

## ✅ RiskAssessor
- [ ] assess(1.5%, 5%) → "S"
- [ ] assess(2.5%, 15%) → "A"
- [ ] assess(4.0%, 25%) → "B"
- [ ] assess(6.0%, 5%) → "C" (溢價率超標)
- [ ] assess(1.5%, 35%) → "C" (風險超標)
- [ ] 邊界測試: risk_ratio=9.9% → S, 10.0% → A, 10.1% → A
- [ ] generate_signal(S) → "BUY"
- [ ] generate_signal(C) → "AVOID"

## ✅ DB 寫入
- [ ] daily_analysis_results.final_rating 正確更新
- [ ] trading_signals 表正確寫入

## ✅ 單元測試
- [ ] ChipProfiler 測試覆蓋率 > 85%
- [ ] RiskAssessor 測試覆蓋率 > 90%
