# Phase 3.1 - 開發流程

## 📅 執行步驟

### Step 1: 核心公式驗證 (@ANALYST) → ⏸️ Checkpoint 1
**動作**: 使用已知歷史資料手動驗證公式
**輸入**: 
  - 家登 (3680) 昨日 CB 收盤價、轉換價格、現股收盤價
  - 聚和 (6509) 同上
**驗證**: 計算結果與券商軟體 (元大/群益等) 顯示的溢價率比對
**通過標準**: 誤差 < 0.1%

### Step 2: 實作 PremiumCalculator (@CODER)
**檔案**: `src/analytics/premium_calculator.py`
**方法**:
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
**重點**: 純數學函數，無側效應，可單獨測試

### Step 3: 實作 TechnicalAnalyzer (@CODER)
**檔案**: `src/analytics/technical_analyzer.py`
**功能**:
  - 從 stock_daily 讀取近 20 日資料
  - numpy 計算 MA5, MA20, 20日均量
  - `check_breakout()`: 成交量 > 1.5倍20日均量 + 收盤價 > MA20
  - `check_ma_alignment()`: 多頭排列 (MA5 > MA20) / 空頭 / 盤整
  - `check_attack_pattern()`: 連續 3 日收紅K + 成交量遞增

### Step 4: 實作 models.py (@CODER)
**檔案**: `src/analytics/models.py`
**類別**: `AnalysisResult` (dataclass, 對應 daily_analysis_results 表)

### Step 5: 整合測試 (@CODER/@ANALYST) → ⏸️ Checkpoint 2
**測試**:
  - 單元測試: PremiumCalculator (各種邊界條件)
  - 單元測試: TechnicalAnalyzer (已知突破案例)
  - 整合測試: analyze() 完整流程 + DB 寫入

## ⏰ 預估工時: 20-30 小時
