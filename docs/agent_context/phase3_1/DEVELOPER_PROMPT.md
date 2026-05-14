# Phase 3.1 Developer Prompt - 核心分析引擎

## 🎯 任務概述
實作 EOD Analytics 的核心分析引擎：PremiumCalculator (溢價率計算) + TechnicalAnalyzer (技術面標記)。
對應盤後階段二 (17:15)。

## 📁 參考文件
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_1/01_dev_goal_context.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_1/arch_design.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_1/05_validation_checklist.md`

## 📁 既有結構

```
src/
├── analytics/          ← 已建立 (from Phase 3.0)
│   └── __init__.py
├── framework/
│   ├── base_item.py    ← 已有 daily_analysis_results 的 Item
│   └── base_spider.py
└── ...
```

### 既有 DB 表 (直接查詢使用)
- `stock_daily` — symbol, date, close_price, volume
- `tpex_cb_daily` — cb_code, closing_price, volume, premium_rate, conversion_price
- `cb_master` — cb_code, underlying_stock, conversion_price
- `daily_analysis_results` — 結果寫入 (from Phase 3.0)

### 既有 Item 類別 (直接使用)
- `DailyAnalysisResultItem` — 對應 daily_analysis_results 表
- `get_item_class("daily_analysis_results")` — 取得 Item 類別

## 📋 實作項目

### 1. src/analytics/models.py — 共用數據模型

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AnalysisResult:
    """分析結果數據模型 (對應 daily_analysis_results 表)"""
    date: str
    symbol: str
    close_price: float = 0.0
    conversion_value: float = 0.0
    premium_ratio: float = 0.0
    technical_signal: str = "NEUTRAL"  # BREAKOUT / BULLISH / NEUTRAL / BEARISH
    is_junk: bool = False
    notes: str = ""
```

### 2. src/analytics/premium_calculator.py

```python
"""
Premium Calculator - 轉換價值與溢價率計算

公式:
    轉換價值 = (CB收盤價 ÷ 轉換價格) × 1000 × 現股收盤價
    溢價率   = (CB收盤價 ÷ 轉換價值) - 1
    廢棄門檻: 溢價率 > 5% → is_junk = True
"""
from typing import List, Optional
from src.analytics.models import AnalysisResult


class PremiumCalculator:
    """轉換價值與溢價率計算器"""
    
    JUNK_THRESHOLD = 0.05  # 溢價率 > 5% 視為廢棄標的
    
    @staticmethod
    def calculate_conversion_value(cb_close: float, conversion_price: float, stock_close: float) -> float:
        """計算轉換價值"""
        if conversion_price <= 0:
            return 0.0
        return (cb_close / conversion_price) * 1000 * stock_close
    
    @staticmethod
    def calculate_premium_ratio(cb_close: float, conversion_value: float) -> float:
        """計算溢價率"""
        if conversion_value <= 0:
            return 999.0  # 無法計算時給極大值
        return (cb_close / conversion_value) - 1
    
    @staticmethod
    def is_junk(premium_ratio: float, threshold: float = JUNK_THRESHOLD) -> bool:
        """判斷是否為廢棄標的"""
        return premium_ratio > threshold
    
    def analyze(self, date: str) -> List[AnalysisResult]:
        """
        執行完整分析
        
        1. 從 DB 讀取 stock_daily + tpex_cb_daily + cb_master
        2. 配對 CB 與對應現股
        3. 計算轉換價值與溢價率
        4. 回傳 AnalysisResult 列表
        """
        import psycopg2
        from src.framework.base_item import DB_CONFIG
        
        # 連線 DB (使用 run_daily.py 中的 DB_CONFIG)
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 讀取 tpex_cb_daily (當日 CB 日行情)
            cursor.execute("""
                SELECT t.cb_code, t.closing_price, t.conversion_price, 
                       t.underlying_stock, t.premium_rate
                FROM tpex_cb_daily t
                WHERE t.trade_date = %s
            """, (date,))
            cb_records = cursor.fetchall()
            
            results = []
            for cb_code, cb_close, conv_price, under_stock, _ in cb_records:
                if not cb_close or not conv_price or not under_stock:
                    continue
                
                # 讀取對應現股收盤價
                cursor.execute("""
                    SELECT close_price FROM stock_daily
                    WHERE symbol = %s AND date = %s
                """, (under_stock, date))
                stock_row = cursor.fetchone()
                if not stock_row:
                    continue
                stock_close = float(stock_row[0])
                
                # 計算
                conv_value = self.calculate_conversion_value(
                    float(cb_close), float(conv_price), stock_close
                )
                prem_ratio = self.calculate_premium_ratio(
                    float(cb_close), conv_value
                )
                
                results.append(AnalysisResult(
                    date=date,
                    symbol=under_stock,
                    close_price=stock_close,
                    conversion_value=round(conv_value, 2),
                    premium_ratio=round(prem_ratio, 4),
                    is_junk=self.is_junk(prem_ratio),
                ))
            
            return results
            
        finally:
            cursor.close()
            conn.close()
    
    def save_results(self, date: str, results: List[AnalysisResult]) -> int:
        """將分析結果寫入 daily_analysis_results 表"""
        import psycopg2
        from src.framework.base_item import DailyAnalysisResultItem
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        saved = 0
        for r in results:
            item = DailyAnalysisResultItem(
                date=r.date,
                symbol=r.symbol,
                close_price=r.close_price,
                conversion_value=r.conversion_value,
                premium_ratio=r.premium_ratio,
                technical_signal=r.technical_signal,
                is_junk=r.is_junk,
                notes=r.notes,
            )
            cursor.execute("""
                INSERT INTO daily_analysis_results
                (date, symbol, close_price, conversion_value, premium_ratio, 
                 technical_signal, is_junk, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, symbol) DO UPDATE SET
                    close_price = EXCLUDED.close_price,
                    conversion_value = EXCLUDED.conversion_value,
                    premium_ratio = EXCLUDED.premium_ratio,
                    technical_signal = EXCLUDED.technical_signal,
                    is_junk = EXCLUDED.is_junk
            """, (
                r.date, r.symbol, r.close_price, r.conversion_value,
                r.premium_ratio, r.technical_signal, r.is_junk, r.notes
            ))
            saved += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        return saved


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    pc = PremiumCalculator()
    results = pc.analyze(args.date)
    print(f"分析 {len(results)} 筆")
    saved = pc.save_results(args.date, results)
    print(f"已寫入 {saved} 筆至 daily_analysis_results")
    for r in results:
        status = "❌ 廢棄" if r.is_junk else "✅"
        print(f"  {r.symbol}: 溢價率={r.premiun_ratio:.2%} {status}")
```

### 3. src/analytics/technical_analyzer.py

```python
"""
Technical Analyzer - 技術面標記

功能:
  - 計算 MA5, MA20, 20日均量
  - 帶量突破判斷
  - 多頭排列判斷
  - 攻擊型態判斷
"""
from typing import List, Optional
import numpy as np
from src.analytics.models import AnalysisResult


class TechnicalAnalyzer:
    """技術面分析器"""
    
    BREAKOUT_VOLUME_RATIO = 1.5  # 突破需要 1.5 倍均量
    
    def get_historical_data(self, symbol: str, date: str, days: int = 20) -> dict:
        """從 stock_daily 取得歷史收盤價與成交量"""
        import psycopg2
        from src.framework.base_item import DB_CONFIG
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT close_price, volume 
            FROM stock_daily
            WHERE symbol = %s AND date <= %s
            ORDER BY date DESC
            LIMIT %s
        """, (symbol, date, days + 5))  # 多取幾筆確保夠用
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 反轉為時間順序 (oldest first)
        closes = np.array([float(r[0]) for r in reversed(rows)])
        volumes = np.array([int(r[1]) for r in reversed(rows)])
        return {"closes": closes, "volumes": volumes}
    
    def calculate_ma(self, data: np.ndarray, period: int) -> float:
        """計算移動平均線"""
        if len(data) < period:
            return 0.0
        return float(np.mean(data[-period:]))
    
    def check_breakout(self, close: float, volume: int, 
                       ma20: float, volume_ma20: float) -> bool:
        """帶量突破: 量 > 1.5倍均量 AND 價 > MA20"""
        if ma20 <= 0 or volume_ma20 <= 0:
            return False
        return volume > volume_ma20 * self.BREAKOUT_VOLUME_RATIO and close > ma20
    
    def check_ma_alignment(self, close: float, ma5: float, ma20: float) -> str:
        """均線排列: 多頭/空頭/盤整"""
        if ma5 <= 0 or ma20 <= 0:
            return "NEUTRAL"
        if close > ma5 > ma20:
            return "BULLISH"
        if close < ma5 < ma20:
            return "BEARISH"
        return "NEUTRAL"
    
    def check_attack_pattern(self, closes: np.ndarray, volumes: np.ndarray) -> bool:
        """攻擊型態: 連續 3 日收紅K + 成交量遞增"""
        if len(closes) < 4:
            return False
        
        recent = closes[-4:]
        recent_v = volumes[-4:]
        
        # 連 3 日收紅 (收盤價逐日上升)
        price_up = all(recent[i] < recent[i+1] for i in range(3))
        # 量遞增
        volume_up = all(recent_v[i] < recent_v[i+1] for i in range(3))
        
        return price_up and volume_up
    
    def analyze(self, date: str, premium_results: List[AnalysisResult]) -> List[AnalysisResult]:
        """對每筆分析結果加上技術面信號"""
        for r in premium_results:
            hist = self.get_historical_data(r.symbol, date)
            closes, volumes = hist["closes"], hist["volumes"]
            
            if len(closes) < 20:
                r.technical_signal = "NEUTRAL"
                continue
            
            ma5 = self.calculate_ma(closes, 5)
            ma20 = self.calculate_ma(closes, 20)
            vma20 = self.calculate_ma(volumes, 20)
            
            breakout = self.check_breakout(r.close_price, 0, ma20, vma20)
            alignment = self.check_ma_alignment(r.close_price, ma5, ma20)
            attack = self.check_attack_pattern(closes, volumes)
            
            if breakout or attack:
                r.technical_signal = "BREAKOUT"
            elif alignment == "BULLISH":
                r.technical_signal = "BULLISH"
            elif alignment == "BEARISH" and not r.is_junk:
                r.technical_signal = "BEARISH"
            else:
                r.technical_signal = "NEUTRAL"
        
        return premium_results
```

### 4. src/analytics/rules/technical_rules.py
定義技術面判斷的門檻常數，供 TechnicalAnalyzer 使用。

### 5. tests/test_premium_calculator.py 與 tests/test_technical_analyzer.py

## ✅ 驗收清單

### PremiumCalculator
- [ ] calculate_conversion_value 計算正確
- [ ] calculate_premium_ratio 計算正確
- [ ] is_junk(0.03) = False, is_junk(0.07) = True
- [ ] conversion_price <= 0 時回傳 0.0 不拋錯
- [ ] analyze() 從 DB 讀取資料並回傳 List[AnalysisResult]

### TechnicalAnalyzer
- [ ] MA5 / MA20 計算正確 (使用 numpy)
- [ ] check_breakout 判斷準確
- [ ] check_ma_alignment 三種分類正確
- [ ] check_attack_pattern 判斷準確
- [ ] 歷史資料不足 20 筆時回傳 NEUTRAL 不拋錯

### 整合
- [ ] premium_calculator.py CLI 可執行: `python -m src.analytics.premium_calculator --date 2026-05-11`
- [ ] 分析結果正確寫入 daily_analysis_results 表
- [ ] DB_CONFIG 正確 (與 run_daily.py 共用連線設定)

## ⚠️ 注意事項
1. DB_CONFIG 請從 `src/run_daily.py` 中引用（已定義 `DB_CONFIG` dict）
2. 使用的 DB 表: stock_daily, tpex_cb_daily, cb_master（皆已存在）
3. 寫入的表: daily_analysis_results（Phase 3.0 已建立）
4. 溢價率建議用小數表示 (如 0.05 = 5%)，DB 中 premium_ratio 為 NUMERIC(6,4)
5. 注意既有 `TpexCbDailyItem` 已有 `premium_rate` 欄位，但本階段仍自行計算以確保公式可控
