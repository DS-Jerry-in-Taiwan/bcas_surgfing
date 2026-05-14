# Phase 3.2 - 風險評級系統架構設計

## 概述
Phase 3.2 對應高階規劃的「階段三：籌碼透視與風險定價 (17:20)」。
實作 ChipProfiler (籌碼分析)、RiskAssessor (隔日沖風險)、BrokerBlacklist (黑名單管理)。

## 架構位置
```
src/analytics/
├── chip_profiler.py            ChipProfiler 類
├── risk_assessor.py            RiskAssessor 類
└── rules/
    ├── risk_rules.py           風險評級規則 (門檻定義)
    └── scoring_rules.py        S/A/B/C 評分邏輯

src/configs/
└── broker_blacklist.json       券商黑名單 (from Phase 3.0)
```

## 核心邏輯

### BrokerBlacklist
```json
[
  {"broker_id": "9200", "broker_name": "凱基-台北", "risk_level": "HIGH"},
  {"broker_id": "9800", "broker_name": "元大-台北", "risk_level": "HIGH"},
  ...
]
```

### ChipProfiler 流程
```
broker_breakdown (今日分點明細)
    │
    ├─ 取前 5 大買超分點
    ├─ 比對 broker_blacklist
    └─ 風險佔比 = 短線客買超張數 ÷ 總成交量
```

### RiskAssessor 評級
```
綜合考量:
  - 溢價率 (來自 Phase 3.1 PremiumCalculator)
  - 風險佔比 (來自 ChipProfiler)

S: 溢價率 < 2% + 風險 < 10%  → BUY
A: 溢價率 < 3% + 風險 < 20%  → BUY (低風險)
B: 溢價率 < 5% + 風險 < 30%  → HOLD
C: 溢價率 ≥ 5% 或 風險 ≥ 30% → AVOID
```

## 資料流
```
Phase 3.0: broker_breakdown + broker_blacklist
Phase 3.1: daily_analysis_results (含 premium_ratio)
    │
    ▼
ChipProfiler.analyze(date)
    │  ├─ 載入黑名單
    │  ├─ 比對買超分點
    │  └─ 計算 risk_ratio
    ▼
RiskAssessor.run_analysis(date)
    │  ├─ 讀取 premium_ratio
    │  ├─ 綜合評級 S/A/B/C
    │  └─ 產生 TradingSignal
    ▼
daily_analysis_results (更新 final_rating, risk_score)
trading_signals (新增 BUY/HOLD/AVOID)
```
