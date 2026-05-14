# Phase 3.2 Developer Prompt - 風險評級系統

## 🎯 任務概述
實作 ChipProfiler (籌碼分析) + RiskAssessor (風險評級) + TradingSignal 生成。
對應盤後階段三 (17:20)。

## 📁 參考文件
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_2/01_dev_goal_context.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_2/arch_design.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_2/05_validation_checklist.md`

## 📁 既有結構

```
src/analytics/
├── __init__.py
├── models.py              AnalysisResult dataclass (from Phase 3.1)
├── premium_calculator.py  PremiumCalculator (from Phase 3.1)
├── technical_analyzer.py  TechnicalAnalyzer (from Phase 3.1)
└── rules/
    ├── __init__.py
    ├── technical_rules.py
    └── scoring_rules.py   (this phase)

src/configs/
└── broker_blacklist.json  券商黑名單 (from Phase 3.0)

tests/
├── test_premium_calculator.py    (from Phase 3.1)
├── test_technical_analyzer.py    (from Phase 3.1)
├── test_broker_breakdown_spider.py  (from Phase 3.0)
├── test_phase3_items.py         (from Phase 3.0)
└── test_phase3_integration.py   (from Phase 3.0)
```

### 既有 DB 表 (直接查詢使用)
- `broker_breakdown` — date, symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume (from Phase 3.0)
- `daily_analysis_results` — date, symbol, premium_ratio, technical_signal (from Phase 3.0, written by Phase 3.1)
- `trading_signals` — date, symbol, signal_type, confidence (from Phase 3.0, empty)
- `broker_blacklist` — broker_id, broker_name, risk_level, category (from Phase 3.0)

### 既有 Item 類別
- `DailyAnalysisResultItem` — date, symbol, premium_ratio, final_rating, risk_score, broker_risk_pct
- `TradingSignalItem` — date, symbol, signal_type, confidence

### DB_CONFIG (連線設定)
```python
# 請從 src/run_daily.py 引用
from src.run_daily import DB_CONFIG
```

## 📋 實作項目

### 1. src/analytics/rules/risk_rules.py
```python
"""風險評級規則與門檻定義"""

# 評級門檻
RATING_THRESHOLDS = {
    "S": {"max_premium": 0.02, "max_risk": 0.10},  # 溢價率 < 2%, 風險 < 10%
    "A": {"max_premium": 0.03, "max_risk": 0.20},  # 溢價率 < 3%, 風險 < 20%
    "B": {"max_premium": 0.05, "max_risk": 0.30},  # 溢價率 < 5%, 風險 < 30%
    # C: 其餘情況
}

# 信號對應
SIGNAL_MAP = {
    "S": "BUY",
    "A": "BUY",
    "B": "HOLD",
    "C": "AVOID",
}
```

### 2. src/analytics/chip_profiler.py
```python
"""
ChipProfiler - 籌碼分析

功能:
  - 載入券商黑名單 JSON
  - 比對 broker_breakdown 分點資料
  - 計算隔日沖風險佔比
"""
import json
import os
from typing import List, Dict, Any, Optional


class ChipProfiler:
    """籌碼分析：比對分點與黑名單，計算風險"""
    
    def __init__(self, blacklist_path: str = None):
        if blacklist_path is None:
            blacklist_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "broker_blacklist.json"
            )
        self.blacklist_path = blacklist_path
        self.blacklist: Dict[str, dict] = {}
        self.load_blacklist()
    
    def load_blacklist(self) -> int:
        """載入券商黑名單 JSON，回傳筆數"""
        path = os.path.abspath(self.blacklist_path)
        if not os.path.exists(path):
            self.blacklist = {}
            return 0
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        self.blacklist = {
            r["broker_id"]: r for r in records
        }
        return len(self.blacklist)
    
    def get_risk_level(self, broker_id: str) -> Optional[str]:
        """查詢券商風險等級"""
        broker = self.blacklist.get(broker_id)
        return broker.get("risk_level") if broker else None
    
    def is_suspicious(self, broker_id: str) -> bool:
        """是否為可疑券商"""
        return broker_id in self.blacklist
    
    def analyze(self, date: str) -> Dict[str, dict]:
        """
        執行籌碼分析
        
        從 broker_breakdown 讀取當日資料，
        比對黑名單，計算每檔股票的隔日沖風險佔比。
        
        Returns:
            {symbol: {"risk_ratio": float, "matched_brokers": List[str], "total_volume": int}}
        """
        import psycopg2
        from src.run_daily import DB_CONFIG
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 取得當日所有分點資料
            cursor.execute("""
                SELECT symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume
                FROM broker_breakdown
                WHERE date = %s
                ORDER BY symbol, rank
            """, (date,))
            rows = cursor.fetchall()
            
            # 依 symbol 分組
            from collections import defaultdict
            by_symbol: Dict[str, list] = defaultdict(list)
            for row in rows:
                by_symbol[row[0]].append({
                    "broker_id": row[1],
                    "broker_name": row[2],
                    "buy_volume": row[3] or 0,
                    "sell_volume": row[4] or 0,
                    "net_volume": row[5] or 0,
                })
            
            # 每檔股票計算
            results = {}
            for symbol, brokers in by_symbol.items():
                # 取前 5 大買超
                top_buyers = sorted(brokers, key=lambda x: x["buy_volume"], reverse=True)[:5]
                
                # 比對黑名單
                matched = [b for b in top_buyers if self.is_suspicious(b["broker_id"])]
                suspect_volume = sum(b["buy_volume"] for b in matched)
                total_volume = sum(b["buy_volume"] for b in brokers)
                
                risk_ratio = suspect_volume / total_volume if total_volume > 0 else 0.0
                
                results[symbol] = {
                    "risk_ratio": round(risk_ratio, 4),
                    "matched_brokers": [b["broker_name"] for b in matched],
                    "total_volume": total_volume,
                    "suspect_volume": suspect_volume,
                }
            
            return results
            
        finally:
            cursor.close()
            conn.close()


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    profiler = ChipProfiler()
    print(f"黑名單載入: {len(profiler.blacklist)} 筆")
    results = profiler.analyze(args.date)
    for symbol, info in results.items():
        print(f"{symbol}: 風險佔比={info['risk_ratio']:.1%}, "
              f"匹配={info['matched_brokers']}")
```

### 3. src/analytics/risk_assessor.py
```python
"""
RiskAssessor - 風險評級

綜合溢價率 (Phase 3.1) + 風險佔比 (ChipProfiler)，
給予 S/A/B/C 評級，產生交易信號。
"""
from typing import List, Optional, Dict, Any
from src.analytics.rules.risk_rules import RATING_THRESHOLDS, SIGNAL_MAP


class RiskAssessor:
    """風險評級：S/A/B/C 與交易信號"""
    
    @staticmethod
    def assess(premium_ratio: float, risk_ratio: float) -> str:
        """
        綜合評級
        
        Args:
            premium_ratio: 溢價率 (0.05 = 5%)
            risk_ratio: 風險佔比 (0.10 = 10%)
        
        Returns:
            "S", "A", "B", "C"
        """
        for rating in ["S", "A", "B"]:
            threshold = RATING_THRESHOLDS[rating]
            if premium_ratio < threshold["max_premium"] and risk_ratio < threshold["max_risk"]:
                return rating
        return "C"
    
    @staticmethod
    def generate_signal(rating: str) -> str:
        """根據評級產生交易信號"""
        return SIGNAL_MAP.get(rating, "HOLD")
    
    def run_analysis(self, date: str) -> List[Dict[str, Any]]:
        """
        執行完整風險評級
        
        1. 從 daily_analysis_results 讀取溢價率
        2. 從 ChipProfiler 取得風險佔比
        3. 綜合評級
        4. 寫入 daily_analysis_results.final_rating
        5. 寫入 trading_signals
        
        Returns:
            評級結果列表
        """
        import psycopg2
        from src.run_daily import DB_CONFIG
        from src.analytics.chip_profiler import ChipProfiler
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 讀取當日分析結果 (含 premium_ratio)
            cursor.execute("""
                SELECT symbol, premium_ratio, is_junk
                FROM daily_analysis_results
                WHERE date = %s
            """, (date,))
            analysis_rows = cursor.fetchall()
            
            # 取得籌碼分析結果
            profiler = ChipProfiler()
            chip_results = profiler.analyze(date)
            
            results = []
            for symbol, premium_ratio, is_junk in analysis_rows:
                premium = float(premium_ratio) if premium_ratio else 999.0
                
                # 廢棄標的直接給 C
                if is_junk:
                    rating = "C"
                    risk_ratio = 0.0
                else:
                    chip_info = chip_results.get(symbol, {})
                    risk_ratio = chip_info.get("risk_ratio", 0.0)
                    rating = self.assess(premium, risk_ratio)
                
                signal = self.generate_signal(rating)
                
                # 更新 daily_analysis_results
                cursor.execute("""
                    UPDATE daily_analysis_results
                    SET final_rating = %s,
                        risk_score = %s,
                        broker_risk_pct = %s
                    WHERE date = %s AND symbol = %s
                """, (rating, risk_ratio * 100, risk_ratio * 100, date, symbol))
                
                # 寫入 trading_signals (upsert)
                cursor.execute("""
                    INSERT INTO trading_signals (date, symbol, signal_type, confidence, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (date, symbol, signal_type) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        notes = EXCLUDED.notes
                """, (date, symbol, signal, _confidence(rating), f"溢價率:{premium:.2%},風險:{risk_ratio:.1%}"))
                
                results.append({
                    "symbol": symbol,
                    "premium_ratio": premium,
                    "risk_ratio": risk_ratio,
                    "rating": rating,
                    "signal": signal,
                })
            
            conn.commit()
            return results
            
        finally:
            cursor.close()
            conn.close()


def _confidence(rating: str) -> float:
    """根據評級計算信心度"""
    return {"S": 0.9, "A": 0.7, "B": 0.5, "C": 0.3}.get(rating, 0.5)


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    ra = RiskAssessor()
    results = ra.run_analysis(args.date)
    print(f"評級 {len(results)} 筆")
    for r in results:
        print(f"  {r['symbol']}: {r['rating']} ({r['signal']}) "
              f"溢價率={r['premium_ratio']:.2%} 風險={r['risk_ratio']:.1%}")
```

### 4. tests/test_chip_profiler.py
使用 mock 避免讀取真實檔案與 DB：

```python
"""ChipProfiler 單元測試"""
import sys
sys.path.insert(0, 'src')
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from analytics.chip_profiler import ChipProfiler


class TestChipProfiler:
    
    @patch("analytics.chip_profiler.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps([
        {"broker_id": "9200", "broker_name": "凱基-台北", "risk_level": "HIGH"},
        {"broker_id": "9800", "broker_name": "元大-台北", "risk_level": "HIGH"},
    ]))
    def test_load_blacklist(self, mock_file, mock_exists):
        mock_exists.return_value = True
        profiler = ChipProfiler(blacklist_path="/fake/path.json")
        assert len(profiler.blacklist) == 2
    
    def test_is_suspicious(self):
        profiler = ChipProfiler()
        profiler.blacklist = {"9200": {"risk_level": "HIGH"}}
        assert profiler.is_suspicious("9200") is True
        assert profiler.is_suspicious("9999") is False
    
    def test_get_risk_level(self):
        profiler = ChipProfiler()
        profiler.blacklist = {"9200": {"risk_level": "HIGH", "broker_name": "凱基-台北"}}
        assert profiler.get_risk_level("9200") == "HIGH"
        assert profiler.get_risk_level("9999") is None
```

### 5. tests/test_risk_assessor.py
```python
"""RiskAssessor 單元測試"""
import sys
sys.path.insert(0, 'src')
import pytest
from analytics.risk_assessor import RiskAssessor


class TestRiskAssessor:
    
    def test_assess_S(self):
        assert RiskAssessor.assess(0.01, 0.05) == "S"   # premium < 2%, risk < 10%
    
    def test_assess_A(self):
        assert RiskAssessor.assess(0.025, 0.15) == "A"  # premium < 3%, risk < 20%
    
    def test_assess_B(self):
        assert RiskAssessor.assess(0.04, 0.25) == "B"   # premium < 5%, risk < 30%
    
    def test_assess_C_premium(self):
        assert RiskAssessor.assess(0.06, 0.05) == "C"   # premium >= 5%
    
    def test_assess_C_risk(self):
        assert RiskAssessor.assess(0.01, 0.35) == "C"   # risk >= 30%
    
    def test_assess_boundary_S(self):
        # 邊界: 剛好在門檻上不該過 (相等不算 <)
        assert RiskAssessor.assess(0.0199, 0.099) == "S"
        assert RiskAssessor.assess(0.02, 0.05) == "A"   # premium 等於 2% 不算 < 2%
    
    def test_assess_boundary_A(self):
        assert RiskAssessor.assess(0.03, 0.10) == "B"   # premium 等於 3%
    
    def test_assess_boundary_B(self):
        assert RiskAssessor.assess(0.05, 0.20) == "C"   # premium 等於 5%
    
    def test_generate_signal(self):
        assert RiskAssessor.generate_signal("S") == "BUY"
        assert RiskAssessor.generate_signal("A") == "BUY"
        assert RiskAssessor.generate_signal("B") == "HOLD"
        assert RiskAssessor.generate_signal("C") == "AVOID"
    
    def test_generate_signal_unknown(self):
        assert RiskAssessor.generate_signal("X") == "HOLD"  # 預設值
```

## ✅ 驗收清單

### ChipProfiler
- [ ] 載入黑名單 JSON 正確
- [ ] is_suspicious() 正確判斷已知/未知券商
- [ ] get_risk_level() 正確回傳等級
- [ ] 黑名單檔案不存在時不拋錯 (回傳空字典)

### RiskAssessor
- [ ] assess(0.01, 0.05) → "S"
- [ ] assess(0.025, 0.15) → "A"
- [ ] assess(0.04, 0.25) → "B"
- [ ] assess(0.06, 0.05) → "C" (溢價率超標)
- [ ] assess(0.01, 0.35) → "C" (風險超標)
- [ ] 邊界測試: 0.02 應歸 A 不是 S
- [ ] generate_signal("S") → "BUY"
- [ ] generate_signal("C") → "AVOID"

### 整合
- [ ] run_analysis() 從 DB 讀取/寫入無誤
- [ ] CLI 可執行: `python -m src.analytics.risk_assessor --date 2026-05-11`

## 完成後驗證
```bash
python -m pytest tests/test_chip_profiler.py tests/test_risk_assessor.py -v
python -m pytest tests/ -v  # 全部測試，確認零回歸
```
