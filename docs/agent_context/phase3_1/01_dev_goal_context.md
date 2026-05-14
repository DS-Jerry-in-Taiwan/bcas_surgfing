# Phase 3.1 - 核心分析引擎 (PremiumCalculator + TechnicalAnalyzer)

**階段**: Phase 3.1 (EOD Analytics Engine)
**專案**: BCAS Quant v3.0.0 → EOD Analytics 擴展

**背景**: 
既有系統已完成資料採集 (Phase 3.0)，需要將生硬的報價轉化為 CBAS 實戰指標。
對應高階規劃的「階段二：價值與型態清洗 (17:15)」。

## 🎯 開發目標

1. **PremiumCalculator**: 計算轉換價值 (Conversion Value) 與溢價率 (Premium Ratio)
2. **TechnicalAnalyzer**: 技術面標記 (帶量突破、站上均線、攻擊型態)
3. **廢棄標的篩選**: 溢價率 > 5% 自動標記，不送入下一關
4. **分析結果持久化**: 寫入 daily_analysis_results 表

### 核心產出

| 產出 | 說明 |
|------|------|
| `src/analytics/premium_calculator.py` | PremiumCalculator 類 |
| `src/analytics/technical_analyzer.py` | TechnicalAnalyzer 類 |
| `src/analytics/models.py` | AnalysisResult 數據模型 |
| `src/analytics/rules/technical_rules.py` | 技術面規則定義 |
| `tests/test_premium_calculator.py` | 溢價率單元測試 |
| `tests/test_technical_analyzer.py` | 技術分析單元測試 |

### 核心公式

```
轉換價值 = (CB 收盤價 ÷ 轉換價格) × 1000 × 現股收盤價
溢價率   = (CB 收盤價 ÷ 轉換價值) - 1
廢棄門檻: 溢價率 > 5% → 直接標記，不送下一關
```

### 驗收標準

- [ ] PremiumCalculator 公式計算誤差 < 0.1% (與券商軟體比對)
- [ ] TechnicalAnalyzer 正確標記帶量突破、站上均線、攻擊型態
- [ ] 溢價率 > 5% 標的確實被標記為廢棄 (is_junk = True)
- [ ] 分析結果正確寫入 daily_analysis_results 表
- [ ] 歷史資料驗證 (家登 3680、聚和 6509) 結果 100% 正確
- [ ] 單元測試覆蓋率 > 85%
