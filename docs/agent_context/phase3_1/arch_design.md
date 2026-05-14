# Phase 3.1 - 核心分析引擎架構設計

## 概述
Phase 3.1 對應高階規劃的「階段二：價值與型態清洗 (17:15)」。
包含 PremiumCalculator (溢價率計算) 與 TechnicalAnalyzer (技術面標記)。

## 架構位置
```
src/analytics/                         [NEW]
├── __init__.py
├── models.py                          AnalysisResult 數據模型
├── premium_calculator.py              PremiumCalculator 類
├── technical_analyzer.py              TechnicalAnalyzer 類
└── rules/
    ├── __init__.py
    ├── technical_rules.py             技術面規則 (breakout/MA)
    └── scoring_rules.py               評分規則門檻定義
```

## 核心公式

```
PremiumCalculator:
  轉換價值 = (CB收盤價 ÷ 轉換價格) × 1000 × 現股收盤價
  溢價率   = (CB收盤價 ÷ 轉換價值) - 1
  廢棄門檻: 溢價率 > 5% → is_junk = True

TechnicalAnalyzer:
  帶量突破: volume > 1.5 × VMA20 AND close > MA20
  站上均線: close > MA5 > MA20 (多頭排列)
  攻擊型態: 連續 3 日收紅K + 成交量遞增
```

## 資料流
```
Phase 3.0 DB (stock_daily + tpex_cb_daily + cb_master)
    │
    ▼
PremiumCalculator.analyze(date)
    │  ├─ 逐筆計算轉換價值與溢價率
    │  └─ 標記廢棄標的 (is_junk)
    ▼
TechnicalAnalyzer.analyze(date)
    │  ├─ 計算 MA5, MA20, VMA20
    │  ├─ 判斷 breakout/ma_alignment/attack
    │  └─ 標記 technical_signal
    ▼
daily_analysis_results (DB 寫入)
```

## 依賴
- numpy (MA 計算, Phase 3.0 新增)
- 既有: stock_daily, tpex_cb_daily, cb_master 資料表
