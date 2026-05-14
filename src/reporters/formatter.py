"""
RichFormatter - 使用 Rich 在終端機輸出彩色報表

支援 S/A/B/C 四級評級顏色區分：
  - S 級: 綠色 (bold)
  - A 級: 藍色 (bold)
  - B 級: 黃色 (bold)
  - C 級: 紅色 (bold)

用法:
    from src.reporters.formatter import RichFormatter
    RichFormatter().print_report("2026-05-11")
"""
from collections import defaultdict
from typing import List, Any

import psycopg2
from rich.console import Console
from rich.table import Table
from rich.style import Style

from src.run_daily import DB_CONFIG


class RichFormatter:
    """終端機 Rich 格式化輸出"""

    RATING_STYLES = {
        "S": Style(color="green", bold=True),
        "A": Style(color="blue", bold=True),
        "B": Style(color="yellow", bold=True),
        "C": Style(color="red", bold=True),
    }

    RATING_SECTIONS: List[tuple] = [
        ("S", "強烈買入", "🟢"),
        ("A", "可布局", "🔵"),
        ("B", "觀察", "🟡"),
        ("C", "避開", "🔴"),
    ]

    def __init__(self):
        self.console = Console()

    def print_report(self, date: str):
        """輸出彩色報表至終端

        Args:
            date: 日期 (YYYY-MM-DD)
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
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
            groups: dict = defaultdict(list)
            for row in rows:
                groups[row[4] or "C"].append(row)

            self.console.print(
                f"\n[bold]📅 CBAS 次日交易戰略清單 - {date}[/bold]\n"
            )

            for rating, title, icon in self.RATING_SECTIONS:
                items = groups.get(rating, [])
                if not items:
                    continue

                table = Table(
                    title=f"{icon} {rating} 級 ({title})",
                    style=self.RATING_STYLES.get(rating),
                )
                table.add_column("標的", style="bold")
                table.add_column("收盤價", justify="right")
                table.add_column("溢價率", justify="right")
                table.add_column("風險", justify="right")
                table.add_column("信號")

                for row in items:
                    symbol, close, premium, risk, _, signal = row
                    table.add_row(
                        symbol,
                        f"{float(close):.2f}" if close else "N/A",
                        f"{float(premium)*100:.2f}%" if premium else "N/A",
                        f"{float(risk):.1f}%" if risk else "N/A",
                        signal or "HOLD",
                    )

                self.console.print(table)
                self.console.print()

        finally:
            cursor.close()
            conn.close()
