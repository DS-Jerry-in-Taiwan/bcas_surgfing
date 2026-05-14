# Phase 3.1 - 核心分析引擎 開發日誌

## 實作摘要
實作 PremiumCalculator (溢價率計算) 與 TechnicalAnalyzer (技術面標記) 核心分析引擎。

## 建立檔案

| 檔案 | 行數 | 說明 |
|------|------|------|
| `src/analytics/models.py` | 23 | AnalysisResult 數據模型 |
| `src/analytics/rules/__init__.py` | 5 | rules package init |
| `src/analytics/rules/technical_rules.py` | 28 | 技術面門檻常數定義 |
| `src/analytics/premium_calculator.py` | 197 | PremiumCalculator 類 (含 CLI) |
| `src/analytics/technical_analyzer.py` | 191 | TechnicalAnalyzer 類 |
| `tests/test_premium_calculator.py` | 368 | 溢價率單元測試 (25 tests) |
| `tests/test_technical_analyzer.py` | 481 | 技術分析單元測試 (33 tests) |

## 驗收標準覆蓋

### PremiumCalculator
- [x] `calculate_conversion_value` 計算正確
- [x] `calculate_premium_ratio` 計算正確
- [x] `is_junk(0.03)` = False, `is_junk(0.07)` = True
- [x] `conversion_price <= 0` 時回傳 0.0 不拋錯
- [x] `analyze()` 從 DB 讀取資料並回傳 `List[AnalysisResult]`
- [x] `save_results()` 使用 upsert 寫入 daily_analysis_results

### TechnicalAnalyzer
- [x] MA5 / MA20 計算正確 (使用 numpy)
- [x] `check_breakout` 判斷準確 (含邊界條件)
- [x] `check_ma_alignment` 三種分類正確 (BULLISH/BEARISH/NEUTRAL)
- [x] `check_attack_pattern` 判斷準確
- [x] 歷史資料不足 20 筆時回傳 NEUTRAL 不拋錯
- [x] junk 標的不標記 BEARISH

### 整合
- [x] `premium_calculator.py` CLI 可正常導入執行
- [x] DB_CONFIG 正確引用 (from src.run_daily)
- [x] psycopg2 模組層級導入 (支援 mock 測試)

## 驗證結果

### 1. 語法檢查
```
models.py OK
rules/__init__.py OK
technical_rules.py OK
premium_calculator.py OK
technical_analyzer.py OK
```

### 2. 單元測試
```
tests/test_premium_calculator.py ... 25 passed
tests/test_technical_analyzer.py ... 33 passed
總計: 58 passed
```

### 3. CLI 執行
```
python -m src.analytics.premium_calculator --date 2026-05-11
→ 成功導入模組、解析參數、連線 DB
→ 預期錯誤: tpex_cb_daily 表不存在 (本地環境未建表)
```

## 遇到的問題與處理

### 問題 1: mock 目標路徑錯誤
- **問題**: `@patch("src.analytics.premium_calculator.psycopg2")` 失敗，因為 `psycopg2` 在函式內部導入
- **處理**: 將 `import psycopg2` 移到模組層級，使 mock 能正確找到目標
- **結果**: 所有 DB mock 測試正常執行

### 問題 2: 邊界測試邏輯錯誤
- **問題**: `test_breakout_exact_at_threshold` 預期 `volume=1500, vma20=1000, 1.5*1000=1500` 為 True，但條件是 `>` (嚴格大於)
- **處理**: 修正斷言為 False，並更新測試註解
- **結果**: 所有邊界條件測試通過

### 問題 3: 浮點數精度差異
- **問題**: `analyze()` 方法對 `premium_ratio` 使用 `round(..., 4)`，但測試直接比較未取整的期望值
- **處理**: 測試中對期望值也套用 `round(..., 4)` 後再比對
- **結果**: 精度比對一致

## Todo 狀態

- [x] 1. models.py — AnalysisResult dataclass
- [x] 2. premium_calculator.py — PremiumCalculator + CLI
- [x] 3. technical_analyzer.py — TechnicalAnalyzer
- [x] 4. rules/technical_rules.py — 技術面常數
- [x] 5. test_premium_calculator.py — 25 個測試案例
- [x] 6. test_technical_analyzer.py — 33 個測試案例
