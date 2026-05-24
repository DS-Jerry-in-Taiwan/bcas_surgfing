#!/usr/bin/env python3
"""
backfill_eod_range.py — 回填 5/1~5/22 歷史資料到 DB

設計：
  1. stock_master: 非日期相關，執行一次
  2. cb_master: 指定最近交易日 (2026-05-22) 下載一次 (靜態參考資料)
  3. stock_daily: 對每個追蹤標的抓 2026/05 整月 (涵蓋 5/1~5/22 所有交易日)
  4. tpex_cb_daily: 逐日抓取 16 個交易日
  5. broker_breakdown: 一次批次 (BSR 為當下快照，日期僅為 metadata)
  6. 完成後自動呼叫 validate_e2e_real_data.py 做最終驗證

用法:
    source .venv/bin/activate
    python scripts/backfill_eod_range.py
"""
import logging
import os
import sys
import subprocess
import time
from datetime import datetime, date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("backfill")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
# 需要 project root (for 'from src.xxx' imports in spiders)
# 以及 src/ (for 'from framework.xxx' imports in run_daily)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_DIR))

DB_CONFIG = dict(
    host="localhost", port=5432, database="cbas",
    user="postgres", password="postgres",
)

TRADING_DAYS_MAY = [
    "2026-05-04", "2026-05-05", "2026-05-06", "2026-05-07", "2026-05-08",
    "2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15",
    "2026-05-18", "2026-05-19", "2026-05-20", "2026-05-21", "2026-05-22",
]
# 注意 5/1(五) 是勞動節休市 — 只剩 15 個交易日


def _table_count(table: str) -> int:
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    n = cur.fetchone()[0]
    cur.close()
    conn.close()
    return n


def step_stock_master() -> dict:
    """回填 stock_master (非日期相關，執行一次)"""
    logger.info("=" * 60)
    logger.info("Step: stock_master")
    from spiders.stock_master_spider import StockMasterSpider
    from framework.pipelines import PostgresPipeline

    p = PostgresPipeline(table_name="stock_master", batch_size=500, **DB_CONFIG)
    s = StockMasterSpider(pipeline=p)
    s.collect_only = True
    try:
        r1 = s.fetch_twse()
        logger.info("  TWSE: success=%s, count=%s", r1.success,
                     r1.data.get("count", 0) if r1.data else 0)
        r2 = s.fetch_tpex()
        logger.info("  TPEx: success=%s, count=%s", r2.success,
                     r2.data.get("count", 0) if r2.data else 0)
        count = s.get_pending_count()
        if count > 0:
            s.flush_items(p)
            logger.info("  ✅ stock_master: %d records written", count)
        p.close()
        s.close()
        return {"twse": r1.success, "tpex": r2.success, "count": count}
    except Exception as e:
        logger.error("  ❌ stock_master failed: %s", e)
        p.close()
        s.close()
        return {"error": str(e)}


def step_cb_master(target_date: str = "2026-05-22") -> dict:
    """回填 cb_master (靜態參考資料，指定一個最近交易日)"""
    logger.info("=" * 60)
    logger.info("Step: cb_master (date=%s)", target_date)
    from spiders.cb_master_spider import CbMasterSpider
    from framework.pipelines import PostgresPipeline

    p = PostgresPipeline(table_name="cb_master", batch_size=500, **DB_CONFIG)
    s = CbMasterSpider(pipeline=p)
    s.collect_only = True
    try:
        date_str = target_date.replace("-", "")
        r = s.fetch_cb_master(date_str)
        logger.info("  success=%s, count=%s", r.success,
                     r.data.get("count", 0) if r.data else 0)
        count = s.get_pending_count()
        if count > 0:
            s.flush_items(p)
            logger.info("  ✅ cb_master: %d records written", count)
        p.close()
        s.close()
        return {"success": r.success, "count": count}
    except Exception as e:
        logger.error("  ❌ cb_master failed: %s", e)
        p.close()
        s.close()
        return {"error": str(e)}


def step_stock_daily() -> dict:
    """回填 stock_daily: 抓 2026/05 整月 for 所有追蹤標的"""
    logger.info("=" * 60)
    logger.info("Step: stock_daily (2026/05 for all tracked symbols)")
    from spiders.stock_daily_spider import StockDailySpider
    from framework.pipelines import PostgresPipeline

    # 讀取 tracked_symbols
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM tracked_symbols WHERE is_active ORDER BY symbol")
    symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    logger.info("  %d tracked symbols to fetch", len(symbols))

    if not symbols:
        return {"error": "No tracked symbols found", "count": 0}

    p = PostgresPipeline(table_name="stock_daily", batch_size=500, **DB_CONFIG)
    s = StockDailySpider(pipeline=p)
    s.collect_only = True
    success_count = 0
    fail_count = 0
    total_items = 0
    try:
        for i, sym in enumerate(symbols):
            r = s.fetch_daily(sym, 2026, 5)
            if r.success:
                success_count += 1
                total_items += r.data.get("count", 0) if r.data else 0
            else:
                fail_count += 1
                if fail_count <= 5:
                    logger.warning("  stock_daily %s: %s", sym, r.error)
            if (i + 1) % 50 == 0:
                logger.info("  progress: %d/%d symbols, %d items so far",
                            i + 1, len(symbols), total_items)

        logger.info("  done: %d success, %d fail, %d total items",
                    success_count, fail_count, total_items)
        count = s.get_pending_count()
        if count > 0:
            s.flush_items(p)
            logger.info("  ✅ stock_daily: %d records written to DB", count)
        p.close()
        s.close()
        return {"success": success_count, "fail": fail_count, "items": total_items, "written": count}
    except Exception as e:
        logger.error("  ❌ stock_daily failed: %s", e)
        p.close()
        s.close()
        return {"error": str(e)}


def step_tpex_cb_daily(dates: list) -> dict:
    """回填 tpex_cb_daily: 逐日抓取"""
    logger.info("=" * 60)
    logger.info("Step: tpex_cb_daily (%d dates)", len(dates))
    from spiders.tpex_cb_daily_spider import TpexCbDailySpider
    from framework.pipelines import PostgresPipeline

    p = PostgresPipeline(table_name="tpex_cb_daily", batch_size=500, **DB_CONFIG)
    s = TpexCbDailySpider(pipeline=p)
    s.collect_only = True
    results = {}
    try:
        for d in dates:
            r = s.fetch_daily(d)
            results[d] = {"success": r.success, "count": r.data.get("count", 0) if r.data else 0}
            status = "✅" if r.success else "❌"
            logger.info("  %s %s: count=%s", status, d, results[d]["count"])

        count = s.get_pending_count()
        if count > 0:
            s.flush_items(p)
            logger.info("  ✅ tpex_cb_daily: %d records written to DB", count)
        p.close()
        s.close()
        return {"results": results, "total_written": count}
    except Exception as e:
        logger.error("  ❌ tpex_cb_daily failed: %s", e)
        p.close()
        s.close()
        return {"error": str(e)}


def step_broker_breakdown() -> dict:
    """回填 broker_breakdown: BSR 批次 (約 40 分鐘)"""
    logger.info("=" * 60)
    logger.info("Step: broker_breakdown (sequential batch for all symbols)")
    import psycopg2
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM tracked_symbols WHERE is_active ORDER BY symbol")
    symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    logger.info("  %d symbols", len(symbols))

    if not symbols:
        return {"error": "No tracked symbols found", "count": 0}

    from spiders.broker_breakdown_spider import BrokerBreakdownSpider
    from framework.pipelines import PostgresPipeline

    p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
    s = BrokerBreakdownSpider(pipeline=p)
    s.collect_only = True
    today_str = datetime.now().strftime("%Y%m%d")
    try:
        r = s.fetch_broker_breakdown_batch(today_str, symbols)
        logger.info("  batch result: success=%s, count=%s",
                     r.success, r.data.get("count", 0) if r.data else 0)
        count = s.get_pending_count()
        if count > 0:
            s.flush_items(p)
            logger.info("  ✅ broker_breakdown: %d records written to DB", count)
        p.close()
        s.close()
        return {"success": r.success, "written": count}
    except Exception as e:
        logger.error("  ❌ broker_breakdown failed: %s", e)
        p.close()
        s.close()
        return {"error": str(e)}


def run_analysis_stages(dates: list):
    """對每個交易日執行管線 stages 2-4"""
    logger.info("=" * 60)
    logger.info("Running stages 2-4 for %d dates", len(dates))
    python = sys.executable
    runner = str(SRC_DIR / "run_eod_analysis.py")

    results = {}
    for d in dates:
        day_result = {}
        for stage in [2, 3, 4]:
            cmd = [python, "-u", runner, "--stage", str(stage), "--date", d]
            t0 = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            elapsed = time.time() - t0
            ok = proc.returncode == 0
            day_result[f"stage{stage}"] = {"ok": ok, "elapsed": f"{elapsed:.1f}s"}
            if not ok:
                logger.warning("  %s stage %d: exit=%d, stderr=%.200s",
                               d, stage, proc.returncode, proc.stderr.strip())
        results[d] = day_result
        n_ok = sum(1 for v in day_result.values() if v["ok"])
        logger.info("  %s: %d/3 stages OK", d, n_ok)
    return results


def print_summary(steps: dict):
    """印出摘要"""
    logger.info("=" * 60)
    logger.info("Backfill Summary")
    logger.info("=" * 60)
    for step_name, result in steps.items():
        if isinstance(result, dict):
            items = "; ".join(f"{k}={v}" for k, v in result.items() if not isinstance(v, (dict, list)))
            logger.info("  %s: %s", step_name, items)
        else:
            logger.info("  %s: %s", step_name, result)

    logger.info("")
    logger.info("Final DB counts:")
    for tbl in ["stock_master", "cb_master", "stock_daily", "tpex_cb_daily",
                 "broker_breakdown", "daily_analysis_results", "trading_signals",
                 "tracked_symbols"]:
        logger.info("  %s: %d", tbl, _table_count(tbl))


def main():
    t_start = time.time()
    logger.info("🚀 BCAS EOD Backfill - 回填 2026-05-01 ~ 2026-05-22")

    steps = {}

    # 1. stock_master (非日期相關)
    steps["stock_master"] = step_stock_master()

    # 2. cb_master (指定 5/22 為最近交易日)
    steps["cb_master"] = step_cb_master("2026-05-22")

    # 3. stock_daily (2026/05 整月 for 所有標的)
    steps["stock_daily"] = step_stock_daily()

    # 4. tpex_cb_daily (逐日)
    steps["tpex_cb_daily"] = step_tpex_cb_daily(TRADING_DAYS_MAY)

    # 5. broker_breakdown (一次批次, 約 40 min)
    steps["broker_breakdown"] = step_broker_breakdown()

    # 6. 跑 analysis stages 2-4
    steps["analysis_stages"] = run_analysis_stages(TRADING_DAYS_MAY)

    elapsed = time.time() - t_start
    print_summary(steps)
    logger.info("")
    logger.info("🏁 Backfill completed in %.1f minutes", elapsed / 60)
    logger.info("Now run: python scripts/validate_e2e_real_data.py")


if __name__ == "__main__":
    main()
