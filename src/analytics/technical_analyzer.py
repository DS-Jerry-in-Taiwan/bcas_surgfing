"""
Technical Analyzer - 技術面標記

功能:
  - 計算 MA5, MA20, 20日均量
  - 帶量突破判斷
  - 多頭排列判斷
  - 攻擊型態判斷

用法:
    from src.analytics.technical_analyzer import TechnicalAnalyzer
    analyzer = TechnicalAnalyzer()
    results = analyzer.analyze("2026-05-11", premium_results)
"""

from typing import List, Optional

import numpy as np
import psycopg2

from src.analytics.models import AnalysisResult
from src.analytics.rules.technical_rules import (
    BREAKOUT_VOLUME_RATIO,
    MA_SHORT_PERIOD,
    MA_LONG_PERIOD,
    MIN_HISTORY_DAYS,
)
from src.run_daily import DB_CONFIG


class TechnicalAnalyzer:
    """技術面分析器"""

    BREAKOUT_VOLUME_RATIO = BREAKOUT_VOLUME_RATIO  # 突破需要 1.5 倍均量

    def get_historical_data(self, symbol: str, date: str, days: int = 20) -> dict:
        """從 stock_daily 取得歷史收盤價與成交量

        Args:
            symbol: 股票代號
            date: 截止日期 (含)
            days: 需要的歷史天數

        Returns:
            dict: {"closes": np.ndarray, "volumes": np.ndarray}
            時間順序為由遠到近 (oldest first)
        """
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
        """計算移動平均線

        Args:
            data: 價格或成交量陣列 (時間順序, oldest first)
            period: 計算期間

        Returns:
            移動平均值; 資料不足時回傳 0.0
        """
        if len(data) < period:
            return 0.0
        return float(np.mean(data[-period:]))

    def check_breakout(
        self, close: float, volume: int, ma20: float, volume_ma20: float
    ) -> bool:
        """帶量突破判斷

        條件: 成交量 > 1.5倍 20日均量 AND 收盤價 > MA20

        Args:
            close: 當日收盤價
            volume: 當日成交量
            ma20: 20日均價
            volume_ma20: 20日均量

        Returns:
            是否為帶量突破
        """
        if ma20 <= 0 or volume_ma20 <= 0:
            return False
        return volume > volume_ma20 * self.BREAKOUT_VOLUME_RATIO and close > ma20

    def check_ma_alignment(self, close: float, ma5: float, ma20: float) -> str:
        """均線排列判斷

        Args:
            close: 當日收盤價
            ma5: 5日均價
            ma20: 20日均價

        Returns:
            "BULLISH" — 多頭排列: close > ma5 > ma20
            "BEARISH" — 空頭排列: close < ma5 < ma20
            "NEUTRAL" — 盤整 or 資料不足
        """
        if ma5 <= 0 or ma20 <= 0:
            return "NEUTRAL"
        if close > ma5 > ma20:
            return "BULLISH"
        if close < ma5 < ma20:
            return "BEARISH"
        return "NEUTRAL"

    def check_attack_pattern(
        self, closes: np.ndarray, volumes: np.ndarray
    ) -> bool:
        """攻擊型態判斷

        條件: 連續 3 日收紅K (收盤價逐日上升) + 成交量遞增

        Args:
            closes: 收盤價陣列 (時間順序, oldest first)
            volumes: 成交量陣列 (時間順序, oldest first)

        Returns:
            是否符合攻擊型態
        """
        if len(closes) < 4 or len(volumes) < 4:
            return False

        recent = closes[-4:]
        recent_v = volumes[-4:]

        # 連 3 日收紅 (收盤價逐日上升)
        price_up = all(recent[i] < recent[i + 1] for i in range(3))
        # 量遞增
        volume_up = all(recent_v[i] < recent_v[i + 1] for i in range(3))

        return price_up and volume_up

    def analyze(
        self, date: str, premium_results: List[AnalysisResult]
    ) -> List[AnalysisResult]:
        """對每筆分析結果加上技術面信號

        流程:
            1. 對每筆結果查詢歷史股價資料
            2. 計算 MA5, MA20, VMA20
            3. 依序判斷: 帶量突破 → 多頭排列 → 空頭排列 → NEUTRAL
            4. 覆蓋 technical_signal 欄位

        Args:
            date: 分析日期
            premium_results: PremiumCalculator.analyze() 的結果

        Returns:
            更新後的 premium_results (in-place + return)
        """
        for r in premium_results:
            hist = self.get_historical_data(r.symbol, date)
            closes, volumes = hist["closes"], hist["volumes"]

            if len(closes) < MIN_HISTORY_DAYS:
                r.technical_signal = "NEUTRAL"
                continue

            ma5 = self.calculate_ma(closes, MA_SHORT_PERIOD)
            ma20 = self.calculate_ma(closes, MA_LONG_PERIOD)
            vma20 = self.calculate_ma(volumes, MA_LONG_PERIOD)

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
