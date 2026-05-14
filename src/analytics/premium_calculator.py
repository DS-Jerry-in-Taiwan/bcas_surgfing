"""
Premium Calculator - 轉換價值與溢價率計算

公式:
    轉換價值 = (CB收盤價 ÷ 轉換價格) × 1000 × 現股收盤價
    溢價率   = (CB收盤價 ÷ 轉換價值) - 1
    廢棄門檻: 溢價率 > 5% → is_junk = True

用法:
    python -m src.analytics.premium_calculator --date 2026-05-11
"""

from typing import List, Optional

import psycopg2

from src.analytics.models import AnalysisResult
from src.analytics.rules.technical_rules import JUNK_THRESHOLD
from src.run_daily import DB_CONFIG


class PremiumCalculator:
    """轉換價值與溢價率計算器"""

    JUNK_THRESHOLD = JUNK_THRESHOLD  # 溢價率 > 5% 視為廢棄標的

    @staticmethod
    def calculate_conversion_value(
        cb_close: float, conversion_price: float, stock_close: float
    ) -> float:
        """計算轉換價值

        Args:
            cb_close: CB 收盤價
            conversion_price: 轉換價格
            stock_close: 現股收盤價

        Returns:
            轉換價值; conversion_price <= 0 時回傳 0.0
        """
        if conversion_price <= 0:
            return 0.0
        return (cb_close / conversion_price) * 1000 * stock_close

    @staticmethod
    def calculate_premium_ratio(cb_close: float, conversion_value: float) -> float:
        """計算溢價率

        Args:
            cb_close: CB 收盤價
            conversion_value: 轉換價值

        Returns:
            溢價率 (小數, 0.05 = 5%); conversion_value <= 0 時回傳 999.0
        """
        if conversion_value <= 0:
            return 999.0  # 無法計算時給極大值
        return (cb_close / conversion_value) - 1

    @staticmethod
    def is_junk(
        premium_ratio: float, threshold: float = JUNK_THRESHOLD
    ) -> bool:
        """判斷是否為廢棄標的

        Args:
            premium_ratio: 溢價率
            threshold: 門檻值 (預設 0.05 = 5%)

        Returns:
            溢價率 > threshold 時回傳 True
        """
        return premium_ratio > threshold

    def analyze(self, date: str) -> List[AnalysisResult]:
        """執行完整分析

        流程:
            1. 從 DB 讀取 tpex_cb_daily (當日 CB 行情)
            2. 對每筆 CB 查詢對應的 stock_daily (現股收盤價)
            3. 計算轉換價值與溢價率
            4. 標記廢棄標的
            5. 回傳 AnalysisResult 列表

        Args:
            date: 分析日期 (YYYY-MM-DD)

        Returns:
            AnalysisResult 列表
        """
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

            results: List[AnalysisResult] = []
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
        """將分析結果寫入 daily_analysis_results 表

        使用 INSERT ... ON CONFLICT DO UPDATE 實現 upsert。

        Args:
            date: 分析日期
            results: 分析結果列表

        Returns:
            寫入筆數
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        saved = 0
        for r in results:
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


# ─── CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="溢價率分析工具")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    pc = PremiumCalculator()
    results = pc.analyze(args.date)
    print(f"分析 {len(results)} 筆")
    saved = pc.save_results(args.date, results)
    print(f"已寫入 {saved} 筆至 daily_analysis_results")
    for r in results:
        status = "廢棄" if r.is_junk else "正常"
        print(f"  {r.symbol}: 溢價率={r.premium_ratio:.2%} [{status}]")
