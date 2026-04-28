"""
run_cleaner.py - 爬蟲資料清洗與驗證

功能:
- stock_daily vs stock_master 交叉驗證
- tpex_cb_daily vs cb_master 交叉驗證
- 寫入 master_check 欄位
- 輸出清洗報告

不假設執行順序，master 無對應資料時標記 NOT_FOUND 而非失敗。
"""
import json
from typing import Dict, List, Optional
from datetime import datetime


class DataCleaner:
    """爬蟲資料清洗與驗證"""

    def __init__(self, db_config: dict):
        """
        Args:
            db_config: PostgreSQL 連線設定
                       {host, port, database, user, password}
        """
        import psycopg2
        self.conn = psycopg2.connect(**db_config)
        self.cur = self.conn.cursor()

    # ─── stock_daily vs stock_master ────────────────────────────

    def validate_stock_daily(self) -> dict:
        """驗證 stock_daily 所有 symbol 是否存在於 stock_master"""
        self.cur.execute("SELECT COUNT(*) FROM stock_daily")
        total = self.cur.fetchone()[0]

        self.cur.execute("""
            SELECT symbol, date
            FROM stock_daily d
            WHERE NOT EXISTS (
                SELECT 1 FROM stock_master m WHERE m.symbol = d.symbol
            )
        """)
        missing = [{"symbol": r[0], "date": str(r[1])} for r in self.cur.fetchall()]

        ok_count = total - len(missing)

        self.cur.execute("""
            UPDATE stock_daily d
            SET master_check = CASE
                WHEN EXISTS (SELECT 1 FROM stock_master m WHERE m.symbol = d.symbol)
                THEN 'OK' ELSE 'NOT_FOUND'
            END
        """)
        self.conn.commit()

        return {
            "total": total,
            "ok": ok_count,
            "not_found": len(missing),
            "not_found_details": missing,
            "master_check_updated": True,
        }

    # ─── tpex_cb_daily vs cb_master ─────────────────────────────

    def validate_cb_daily(self) -> dict:
        """驗證 tpex_cb_daily 所有 cb_code 是否存在於 cb_master"""
        self.cur.execute("SELECT COUNT(*) FROM tpex_cb_daily")
        total = self.cur.fetchone()[0]

        self.cur.execute("""
            SELECT cb_code, trade_date
            FROM tpex_cb_daily d
            WHERE NOT EXISTS (
                SELECT 1 FROM cb_master m WHERE m.cb_code = d.cb_code
            )
        """)
        missing = [
            {"cb_code": r[0], "trade_date": str(r[1])} for r in self.cur.fetchall()
        ]

        ok_count = total - len(missing)

        self.cur.execute("""
            UPDATE tpex_cb_daily d
            SET master_check = CASE
                WHEN EXISTS (SELECT 1 FROM cb_master m WHERE m.cb_code = d.cb_code)
                THEN 'OK' ELSE 'NOT_FOUND'
            END
        """)
        self.conn.commit()

        return {
            "total": total,
            "ok": ok_count,
            "not_found": len(missing),
            "not_found_details": missing,
            "master_check_updated": True,
        }

    # ─── 全部執行 ──────────────────────────────────────────────

    def run_all(self) -> dict:
        """執行全部驗證，回報統計"""
        start = datetime.now()
        result = {
            "start_time": start.isoformat(),
            "stock_daily": self.validate_stock_daily(),
            "tpex_cb_daily": self.validate_cb_daily(),
        }
        elapsed = (datetime.now() - start).total_seconds()
        result["elapsed_seconds"] = round(elapsed, 2)

        not_found_total = (
            result["stock_daily"]["not_found"]
            + result["tpex_cb_daily"]["not_found"]
        )
        result["not_found_total"] = not_found_total
        result["status"] = "completed" if not_found_total == 0 else "completed_with_not_found"

        return result

    # ─── 資源清理 ──────────────────────────────────────────────

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Data Cleaner")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="cbas")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgres")
    args = parser.parse_args()

    db = dict(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
    )

    cleaner = DataCleaner(db)
    try:
        result = cleaner.run_all()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        cleaner.close()


if __name__ == "__main__":
    main()
