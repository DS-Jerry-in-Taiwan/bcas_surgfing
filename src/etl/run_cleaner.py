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
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


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
        self._run_pending_migrations()

    # ─── auto migration ────────────────────────────────────────

    def _run_pending_migrations(self) -> None:
        """自動執行未執行的 DB migration

        掃描 src/db/migration_*.sql 並依序執行。
        使用 IF NOT EXISTS 確保冪等，可安全重複執行。
        """
        import os
        migration_dir = os.path.join(
            os.path.dirname(__file__), "..", "db"
        )
        if not os.path.isdir(migration_dir):
            return

        migration_files = sorted([
            f for f in os.listdir(migration_dir)
            if f.startswith("migration_") and f.endswith(".sql")
        ])

        for filename in migration_files:
            filepath = os.path.join(migration_dir, filename)
            logger.info("Running migration: %s", filename)
            with open(filepath, "r") as f:
                sql = f.read()
            try:
                self.cur.execute(sql)
                self.conn.commit()
                logger.info("Migration %s applied successfully", filename)
            except Exception as e:
                self.conn.rollback()
                logger.error("Migration %s failed: %s", filename, e)
                raise

    # ─── stock_daily vs stock_master ────────────────────────────

    def validate_stock_daily(self) -> dict:
        """驗證 stock_daily + 合併 stock_master 名稱與產業"""
        self.cur.execute("SELECT COUNT(*) FROM stock_daily")
        total = self.cur.fetchone()[0]

        self.cur.execute("""
            SELECT d.symbol, d.date
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

        self.cur.execute("""
            UPDATE stock_daily d
            SET name = m.name,
                industry = m.industry
            FROM stock_master m
            WHERE d.symbol = m.symbol
              AND d.master_check = 'OK'
        """)
        self.conn.commit()

        return {
            "total": total,
            "ok": ok_count,
            "not_found": len(missing),
            "not_found_details": missing,
            "master_check_updated": True,
        }

    # ─── enirch cb_master (GAP-01) ─────────────────────────────

    def enrich_cb_master(self) -> dict:
        """從 cb_code 前4碼推導 underlying_stock（標的股票代號）"""
        self.cur.execute("""
            UPDATE cb_master c
            SET underlying_stock = m.symbol
            FROM stock_master m
            WHERE m.symbol = SUBSTRING(c.cb_code, 1, 4)
              AND (c.underlying_stock IS NULL OR c.underlying_stock = '')
        """)
        matched = self.cur.rowcount
        self.conn.commit()

        self.cur.execute("""
            SELECT cb_code, cb_name FROM cb_master
            WHERE underlying_stock IS NULL OR underlying_stock = ''
            LIMIT 10
        """)
        unmatched = [f"{r[0]} ({r[1]})" for r in self.cur.fetchall()]

        return {
            "cb_master_total_matched": matched,
            "cb_master_unmatched_samples": unmatched,
        }

    # ─── tpex_cb_daily vs cb_master ─────────────────────────────

    def validate_cb_daily(self) -> dict:
        """驗證 tpex_cb_daily + 合併 cb_master 名稱與轉換價格"""
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

        self.cur.execute("""
            UPDATE tpex_cb_daily d
            SET cb_name_enriched = m.cb_name,
                conversion_price_enriched = m.conversion_price
            FROM cb_master m
            WHERE d.cb_code = m.cb_code
              AND d.master_check = 'OK'
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
            "cb_master_enrich": self.enrich_cb_master(),
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
