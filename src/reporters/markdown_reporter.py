"""
MarkdownReporter - 產出 Markdown 格式報表

從 DB 讀取分析結果，依 S/A/B/C 評級分組，產生戰略清單報表。

用法:
    from src.reporters.markdown_reporter import MarkdownReporter
    report = MarkdownReporter().generate_report("2026-05-11")
    print(report)
"""
from typing import List, Tuple, Any
import psycopg2
from src.run_daily import DB_CONFIG


class MarkdownReporter:
    """Markdown 格式報表產生器"""

    REPORT_HEADER = """# CBAS 次日交易戰略清單
📅 日期: {date}

"""

    SECTION_HEADER = """
## {icon} {title}
| 標的 | 收盤價 | 溢價率 | 風險佔比 | 評級 | 信號 |
|------|--------|--------|---------|------|------|
"""

    RATING_CONFIG: List[Tuple[str, str]] = [
        ("S", "🟢 S 級 (強烈買入)"),
        ("A", "🔵 A 級 (可布局)"),
        ("B", "🟡 B 級 (觀察)"),
        ("C", "🔴 C 級 (避開)"),
    ]

    def generate_report(self, date: str) -> str:
        """
        從 DB 讀取資料，產出完整報表

        Args:
            date: 日期 (YYYY-MM-DD)

        Returns:
            Markdown 報表字串
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
            # 讀取分析結果
            cursor.execute("""
                SELECT d.symbol, d.close_price, d.premium_ratio,
                       d.broker_risk_pct, d.final_rating,
                       t.signal_type
                FROM daily_analysis_results d
                LEFT JOIN trading_signals t
                    ON d.date = t.date AND d.symbol = t.symbol
                WHERE d.date = %s AND d.is_junk = false
                ORDER BY d.final_rating, d.symbol
            """, (date,))
            rows = cursor.fetchall()

            # 依評級分組
            by_rating: dict = {r: [] for r, _ in self.RATING_CONFIG}
            for row in rows:
                rating = row[4] or "C"
                if rating in by_rating:
                    by_rating[rating].append(row)

            # 產生報表
            lines = [self.REPORT_HEADER.format(date=date)]

            for rating, title in self.RATING_CONFIG:
                items = by_rating.get(rating, [])
                if not items:
                    continue
                lines.append(self.SECTION_HEADER.format(icon=rating, title=title))
                for row in items:
                    symbol, close, premium, risk, _, signal = row
                    premium_str = f"{float(premium)*100:.2f}%" if premium else "N/A"
                    risk_str = f"{float(risk):.1f}%" if risk else "N/A"
                    close_str = f"{float(close):.2f}" if close else "N/A"
                    signal_str = signal or "HOLD"
                    lines.append(
                        f"| {symbol} | {close_str} | {premium_str} "
                        f"| {risk_str} | {rating} | {signal_str} |\n"
                    )

            return "".join(lines)

        finally:
            cursor.close()
            conn.close()
