# Phase 3.2 - 開發流程

## 📅 執行步驟

### Step 1: 黑名單載入器實作 (@CODER)
**動作**: 實作 BrokerBlacklist 載入邏輯
```python
def load_blacklist(path: str = "configs/broker_blacklist.json") -> Dict[str, BrokerInfo]
```
**輸出**: broker_id → BrokerInfo 的 Dict
**重點**: 使用 frozenset / set 加速比對

### Step 2: 實作 ChipProfiler (@CODER) → ⏸️ Checkpoint 1
**檔案**: `src/analytics/chip_profiler.py`
**方法**:
```python
class ChipProfiler:
    def load_blacklist(self, path: str) -> int  # 回傳載入筆數
    def match_top_buyers(self, records: List[BrokerBreakdownItem], date: str) -> List[MatchResult]
    def calculate_risk_ratio(self, suspect_volume: int, total_volume: int) -> float
    def analyze(self, date: str) -> Dict[str, Any]
```

### Step 3: 實作 RiskAssessor (@CODER) → ⏸️ Checkpoint 2
**檔案**: `src/analytics/risk_assessor.py`
```python
class RiskAssessor:
    def assess(self, premium_ratio: float, risk_ratio: float) -> str  # S/A/B/C
    def generate_signal(self, rating: str) -> str  # BUY/HOLD/AVOID
    def run_analysis(self, date: str) -> List[TradingSignal]
```

### Step 4: 撰寫單元測試 (@CODER/@ANALYST)
**測試範圍**:
  - 黑名單比對: 已知匹配案例
  - 風險佔比計算: 正常值、邊界值
  - 評級邏輯: 4 個評級 + 邊界條件 (9.9%, 10.0%, 10.1%)
  - TradingSignal: S→BUY, C→AVOID 等

## ⏰ 預估工時: 20-30 小時
