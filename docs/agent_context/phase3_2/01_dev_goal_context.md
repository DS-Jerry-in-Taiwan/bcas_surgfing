# Phase 3.2 - 風險評級系統 (ChipProfiler + RiskAssessor)

**階段**: Phase 3.2 (Risk Assessment)
**專案**: BCAS Quant v3.0.0 → EOD Analytics 擴展

**背景**: 
對應高階規劃的「階段三：籌碼透視與風險定價 (17:20)」。
需要將前五大買超券商分點與內建黑名單比對，計算隔日沖風險，並給予 S/A/B/C 評級。

## 🎯 開發目標

1. **ChipProfiler**: 載入黑名單、比對分點買超、計算風險佔比
2. **RiskAssessor**: 綜合溢價率 + 風險佔比，給予 S/A/B/C 評級
3. **BrokerBlacklist 管理**: 載入/查詢/更新券商黑名單
4. **TradingSignal 生成**: 產生 BUY / HOLD / AVOID 交易信號

### 核心產出

| 產出 | 說明 |
|------|------|
| `src/analytics/chip_profiler.py` | ChipProfiler 類 (黑名單比對) |
| `src/analytics/risk_assessor.py` | RiskAssessor 類 (評級 + 信號) |
| `src/analytics/rules/risk_rules.py` | 風險評級規則定義 |
| `tests/test_chip_profiler.py` | 籌碼分析單元測試 |
| `tests/test_risk_assessor.py` | 風險評級單元測試 |

### 評級規則

```
綜合評級 = 溢價率 + 風險佔比:

S (強烈買入): 溢價率 < 2% AND 風險佔比 < 10%
A (可布局):   溢價率 < 3% AND 風險佔比 < 20%
B (觀察):     溢價率 < 5% AND 風險佔比 < 30%
C (避開):     溢價率 ≥ 5% OR  風險佔比 ≥ 30%

TradingSignal:
  S → BUY
  A → BUY (低風險)
  B → HOLD
  C → AVOID
```

### 驗收標準

- [ ] ChipProfiler 能正確載入黑名單並比對分點
- [ ] RiskAssessor 風險佔比計算正確 (短線客買超 ÷ 總成交量)
- [ ] S/A/B/C 評級邏輯正確，邊界條件處理正確
- [ ] TradingSignal 生成合理
- [ ] 評級結果正確寫入 daily_analysis_results.final_rating
- [ ] TradingSignal 正確寫入 trading_signals 表
- [ ] 單元測試覆蓋率 > 85%
