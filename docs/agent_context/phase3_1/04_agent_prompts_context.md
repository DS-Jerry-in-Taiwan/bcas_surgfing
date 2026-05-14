# Phase 3.1 - Agent 執行 Prompts

## @ARCH Prompt
請設計 PremiumCalculator API：
```python
class PremiumCalculator:
    @staticmethod
    def calculate_conversion_value(cb_close: float, conversion_price: float, stock_close: float) -> float
    @staticmethod
    def calculate_premium_ratio(cb_close: float, conversion_value: float) -> float
    @staticmethod
    def is_junk(premium_ratio: float, threshold: float = 0.05) -> bool
    def analyze(self, date: str) -> List[AnalysisResult]
```
- 需要時: 從 DB 讀取 stock_daily, tpex_cb_daily, cb_master
- 輸出: daily_analysis_results

## @CODER Prompt - PremiumCalculator
實作溢價率計算：
1. `calculate_conversion_value()`: (cb_close / conversion_price) * 1000 * stock_close
2. `calculate_premium_ratio()`: (cb_close / conversion_value) - 1
3. `is_junk()`: 溢價率 > 5% → True
4. `analyze()`: 從 DB 取得當日資料，逐筆計算，回傳 AnalysisResult 列表

## @CODER Prompt - TechnicalAnalyzer
實作技術面分析：
1. 從 stock_daily 讀取近 20 個交易日資料
2. 計算 MA5, MA20, VMA20 (20日均量)
3. `check_breakout()`: volume > 1.5 * VMA20 AND close > MA20
4. `check_ma_alignment()`: MA5 vs MA20 多頭/空頭/盤整
5. `check_attack_pattern()`: 連 3 紅 K + 量遞增

## @CODER Prompt - AnalysisResult model
```python
@dataclass
class AnalysisResult:
    date: str
    symbol: str
    close_price: float
    conversion_value: float
    premium_ratio: float
    technical_signal: str   # BREAKOUT / BULLISH / NEUTRAL / BEARISH
    is_junk: bool
```

## @ANALYST Prompt
驗證公式正確性：
1. 取家登 (3680) 昨日收盤資料
2. 手動計算溢價率，比對券商軟體
3. 確認誤差 < 0.1%
4. 執行 pytest tests/test_premium_calculator.py
