"""
RiskAssessor - 風險評級

綜合溢價率 (Phase 3.1 PremiumCalculator) + 風險佔比 (ChipProfiler)，
給予 S/A/B/C 評級，產生交易信號。

評級規則 (使用「小於」比較):
    S (強烈買入): 溢價率 < 2% AND 風險佔比 < 10%
    A (可布局):   溢價率 < 3% AND 風險佔比 < 20%
    B (觀察):     溢價率 < 5% AND 風險佔比 < 30%
    C (避開):     其餘情況 (溢價率 ≥ 5% OR 風險佔比 ≥ 30%)

用法:
    python -m src.analytics.risk_assessor --date 2026-05-11
"""

from typing import Dict, List, Optional, Any

import psycopg2

from src.run_daily import DB_CONFIG
from src.analytics.chip_profiler import ChipProfiler
from src.analytics.rules.risk_rules import RATING_THRESHOLDS, SIGNAL_MAP


class RiskAssessor:
    """風險評級：S/A/B/C 與交易信號"""

    @staticmethod
    def assess(premium_ratio: float, risk_ratio: float) -> str:
        """綜合評級

        溢價率與風險佔比都要小於門檻才給對應評級。
        使用「小於」比較 (相等不算通過)。

        Args:
            premium_ratio: 溢價率 (0.05 = 5%)
            risk_ratio: 風險佔比 (0.10 = 10%)

        Returns:
            "S", "A", "B", "C"
        """
        for rating in ["S", "A", "B"]:
            threshold = RATING_THRESHOLDS[rating]
            if (
                premium_ratio < threshold["max_premium"]
                and risk_ratio < threshold["max_risk"]
            ):
                return rating
        return "C"

    @staticmethod
    def generate_signal(rating: str) -> str:
        """根據評級產生交易信號

        Args:
            rating: 評級 "S"/"A"/"B"/"C"

        Returns:
            "BUY", "HOLD", "AVOID" (預設回傳 "HOLD")
        """
        return SIGNAL_MAP.get(rating, "HOLD")

    def run_analysis(self, date: str) -> List[Dict[str, Any]]:
        """執行完整風險評級

        1. 從 daily_analysis_results 讀取溢價率
        2. 從 ChipProfiler 取得風險佔比
        3. 綜合評級
        4. 寫入 daily_analysis_results.final_rating, risk_score, broker_risk_pct
        5. 寫入 trading_signals (upsert)

        Args:
            date: 分析日期 (YYYY-MM-DD)

        Returns:
            評級結果列表
        """
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
                """, (
                    date, symbol, signal, _confidence(rating),
                    f"溢價率:{premium:.2%},風險:{risk_ratio:.1%}"
                ))

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
    """根據評級計算信心度

    Args:
        rating: 評級 "S"/"A"/"B"/"C"

    Returns:
        信心度數值
    """
    return {"S": 0.9, "A": 0.7, "B": 0.5, "C": 0.3}.get(rating, 0.5)


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="風險評級工具")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    ra = RiskAssessor()
    results = ra.run_analysis(args.date)
    print(f"評級 {len(results)} 筆")
    for r in results:
        print(
            f"  {r['symbol']}: {r['rating']} ({r['signal']}) "
            f"溢價率={r['premium_ratio']:.2%} 風險={r['risk_ratio']:.1%}"
        )
