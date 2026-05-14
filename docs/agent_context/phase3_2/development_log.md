# Phase 3.2 開發日誌

## 實作摘要

實作風險評級系統，包含 ChipProfiler (籌碼分析)、RiskAssessor (風險評級)、以及對應的單元測試。

## 建立檔案

| 檔案 | 行數 | 說明 |
|------|------|------|
| `src/analytics/rules/risk_rules.py` | 28 | RATING_THRESHOLDS 與 SIGNAL_MAP 常數定義 |
| `src/analytics/chip_profiler.py` | 159 | ChipProfiler 類：黑名單載入/查詢、籌碼分析、CLI |
| `src/analytics/risk_assessor.py` | 174 | RiskAssessor 類：評級/信號生成、DB 讀寫、CLI |
| `tests/test_chip_profiler.py` | 283 | ChipProfiler 單元測試 (16 cases) |
| `tests/test_risk_assessor.py` | 312 | RiskAssessor 單元測試 (38 cases) |

### 檔案詳細說明

#### src/analytics/rules/risk_rules.py
- `RATING_THRESHOLDS`: S/A/B 三級門檻 (使用小於比較)
- `SIGNAL_MAP`: 評級→信號對應 (S→BUY, A→BUY, B→HOLD, C→AVOID)

#### src/analytics/chip_profiler.py
- `ChipProfiler.__init__(blacklist_path)`: 初始化並載入黑名單
- `load_blacklist()`: 讀取 broker_blacklist.json，檔案不存在返回 0 不拋錯
- `is_suspicious(broker_id)`: 檢查是否在黑名單中
- `get_risk_level(broker_id)`: 回傳風險等級 (None 表示不在黑名單)
- `analyze(date)`: 從 DB broker_breakdown 讀取分點資料，取前 5 大買超比對黑名單，計算風險佔比
- CLI: `python -m src.analytics.chip_profiler --date YYYY-MM-DD`

#### src/analytics/risk_assessor.py
- `RiskAssessor.assess(premium_ratio, risk_ratio)`: S/A/B/C 綜合評級 (嚴格小於比較)
- `RiskAssessor.generate_signal(rating)`: 產生 BUY/HOLD/AVOID 信號
- `run_analysis(date)`: 完整流程—讀取 daily_analysis_results → ChipProfiler → 評級 → 寫入 DB
- `_confidence(rating)`: 信心度計算 (S:0.9, A:0.7, B:0.5, C:0.3)
- is_junk 標的直接給 C 評級、risk_ratio=0.0
- CLI: `python -m src.analytics.risk_assessor --date YYYY-MM-DD`

#### tests/test_chip_profiler.py (16 案例)
- load_blacklist: 正常載入、檔案不存在、空 JSON、多等級
- is_suspicious: True/False/空黑名單
- get_risk_level: 已知/未知/空黑名單
- analyze (mock DB): 正常分析、無匹配、全匹配、空資料、多標的、零成交量

#### tests/test_risk_assessor.py (38 案例)
- assess: 4 個評級、零值、負溢價率
- 邊界測試: 8 個邊界案例 (相等門檻不通過)
- generate_signal: 4 個對應 + 未知評級 + 空字串 + 小寫
- _confidence: 5 個等級
- 常數驗證: RATING_THRESHOLDS + SIGNAL_MAP
- run_analysis (mock DB): 正常流程、is_junk 處理、空資料、NULL premium

## 測試結果

### Phase 3.2 測試 (54 cases)
```
54 passed in 0.06s
```

### 全部回歸測試 (524 passed, 13 failed)
```
524 passed, 13 failed in 2.92s
```

13 個失敗為既有問題 (與 Phase 3.2 無關):
- `test_base_item`: 2 個 framework 測試
- `test_pipeline`: 3 個 pipeline 測試
- `test_stage5_e2e_integration`: 6 個 E2E 整合測試
- `test_validate_and_enrich`: 2 個資料驗證測試

## 遇到的問題與處理方式

### 問題 1: mock patch 路徑錯誤
**現象**: `@patch("src.analytics.chip_profiler.psycopg2")` 拋 `AttributeError`，因為 `psycopg2` 是在函式內 `import` 的區域變數 (local scope)。

**原因**: chip_profiler.py 的 `analyze()` 方法內使用 `import psycopg2`，這使 `psycopg2` 成為函式區域變數而非模組層級屬性。mock 框架需要在模組層級找到該屬性才能 patch。

**處理**: 將所有 `import psycopg2` 和 `from src.run_daily import DB_CONFIG` 移至模組層級 (import top of file)，與既有的 `premium_calculator.py` 模式一致。risk_assessor.py 中 `from src.analytics.chip_profiler import ChipProfiler` 也比照辦理。

### 問題 2: 評級門檻比較方向
**注意**: 依 spec 要求使用「小於」比較 (strict less than)，邊界條件如 `premium=0.02` 應歸 A 而非 S。已在邊界測試中驗證。

## 驗收清單狀態

### ChipProfiler
- [x] 載入黑名單 JSON 正確
- [x] is_suspicious() 正確判斷已知/未知券商
- [x] get_risk_level() 正確回傳等級
- [x] 黑名單檔案不存在時不拋錯 (回傳空字典)
- [x] analyze() 從 DB 讀取且計算正確

### RiskAssessor
- [x] assess(0.01, 0.05) → "S"
- [x] assess(0.025, 0.15) → "A"
- [x] assess(0.04, 0.25) → "B"
- [x] assess(0.06, 0.05) → "C" (溢價率超標)
- [x] assess(0.01, 0.35) → "C" (風險超標)
- [x] 邊界測試: 0.02 應歸 A 不是 S
- [x] generate_signal("S") → "BUY"
- [x] generate_signal("C") → "AVOID"

### 整合
- [x] run_analysis() 從 DB 讀取/寫入無誤 (mock 驗證)
- [x] CLI 可執行: `python -m src.analytics.risk_assessor --date 2026-05-11`
- [x] CLI 可執行: `python -m src.analytics.chip_profiler --date 2026-05-11`
