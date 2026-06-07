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
| 代號 | 名稱 | CB 代號 | CB 名稱 | 收盤價 | 溢價率 | 風險佔比 | 評級 | 信號 |
|------|------|--------|--------|--------|--------|---------|------|------|
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
            # 讀取分析結果（含 CB 代號/名稱 + 股票名稱）
            cursor.execute("""
                SELECT DISTINCT ON (d.symbol)
                       d.symbol,
                       COALESCE(sm.name, '') AS stock_name,
                       COALESCE(cm.cb_code, '') AS cb_code,
                       COALESCE(cm.cb_name, '') AS cb_name,
                       d.close_price, d.premium_ratio,
                       d.broker_risk_pct, d.final_rating,
                       ts.signal_type
                FROM daily_analysis_results d
                LEFT JOIN trading_signals ts
                    ON d.date = ts.date AND d.symbol = ts.symbol
                LEFT JOIN cb_master cm
                    ON d.symbol = cm.underlying_stock
                LEFT JOIN stock_master sm
                    ON d.symbol = sm.symbol
                WHERE d.date = %s
                  AND d.is_junk = false
                  AND (d.final_rating IS NULL OR d.final_rating != 'D')
                ORDER BY d.symbol,
                    CASE ts.signal_type WHEN 'BUY' THEN 1 WHEN 'HOLD' THEN 2 WHEN 'AVOID' THEN 3 ELSE 4 END
            """, (date,))
            rows = cursor.fetchall()

            # 依評級分組
            by_rating: dict = {r: [] for r, _ in self.RATING_CONFIG}
            for row in rows:
                rating = row[7] or "C"  # final_rating index 7
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
                    # row layout:
                    # symbol(0), stock_name(1), cb_code(2), cb_name(3),
                    # close(4), premium(5), risk(6), final_rating(7), signal(8)
                    symbol, stock_name, cb_code, cb_name = row[0], row[1], row[2], row[3]
                    close, premium, risk, signal = row[4], row[5], row[6], row[8]
                    premium_str = f"{float(premium)*100:.2f}%" if premium is not None else "N/A"
                    risk_str = f"{float(risk):.1f}%" if risk is not None else "N/A"
                    close_str = f"{float(close):.2f}" if close is not None else "N/A"
                    signal_str = signal or "HOLD"
                    lines.append(
                        f"| {symbol} | {stock_name} | {cb_code} | {cb_name} "
                        f"| {close_str} | {premium_str} | {risk_str} "
                        f"| {rating} | {signal_str} |\n"
                    )

            return "".join(lines)

        finally:
            cursor.close()
            conn.close()
