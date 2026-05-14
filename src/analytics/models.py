"""
BCAS Quant - 共用數據模型

AnalysisResult: 盤後分析結果數據模型
對應 daily_analysis_results 表欄位
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AnalysisResult:
    """分析結果數據模型 (對應 daily_analysis_results 表)"""

    date: str  # 分析日期 (YYYY-MM-DD)
    symbol: str  # 證券代號
    close_price: float = 0.0  # 收盤價
    conversion_value: float = 0.0  # 轉換價值
    premium_ratio: float = 0.0  # 溢價率 (小數, 0.05 = 5%)
    technical_signal: str = "NEUTRAL"  # BREAKOUT / BULLISH / NEUTRAL / BEARISH
    is_junk: bool = False  # 是否為廢棄標的 (溢價率 > 5%)
    notes: str = ""  # 備註
