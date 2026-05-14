# Phase 3.1 - 驗證清單

## ✅ PremiumCalculator
- [ ] calculate_conversion_value 計算正確 (驗證 3 組已知資料)
- [ ] calculate_premium_ratio 計算正確
- [ ] is_junk(0.03) = False, is_junk(0.07) = True
- [ ] is_junk(0.05) = False (threshold 預設 >5%, 等於不跳過)
- [ ] analyze() 輸出格式符合 AnalysisResult
- [ ] 無對應 CB 資料時回傳空列表 (非錯誤)

## ✅ TechnicalAnalyzer
- [ ] MA5 / MA20 計算與 pandas 一致
- [ ] check_breakout: 已知突破案例返回 True
- [ ] check_breakout: 已知盤整案例返回 False
- [ ] check_ma_alignment: 多頭/空頭/盤整 3 種分類正確
- [ ] check_attack_pattern: 判斷準確

## ✅ 整合驗證
- [ ] analyze() 結果正確寫入 daily_analysis_results 表
- [ ] 溢價率 > 5% 標的 is_junk = True
- [ ] 既有爬蟲/驗證流程不受影響

## ✅ 單元測試
- [ ] PremiumCalculator 測試覆蓋率 > 90%
- [ ] TechnicalAnalyzer 測試覆蓋率 > 85%
