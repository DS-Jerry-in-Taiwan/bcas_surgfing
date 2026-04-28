"""
run_daily.py - 每日自動化流程

依序執行：
  1. 爬蟲（spiders）
  2. 清洗（run_cleaner.py）
  3. 輸出報告

用法：
  python3 src/run_daily.py                   # 執行全部
  python3 src/run_daily.py --skip-clean      # 只跑爬蟲
  python3 src/run_daily.py --clean-only      # 只跑清洗
"""
import argparse
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

DB_CONFIG = dict(
    host="localhost", port=5432, database="cbas",
    user="postgres", password="postgres",
)


def step_spiders() -> dict:
    """Step 1: 執行爬蟲"""
    from framework.pipelines import PostgresPipeline
    from spiders.stock_master_spider import StockMasterSpider
    from spiders.cb_master_spider import CbMasterSpider
    from spiders.stock_daily_spider import StockDailySpider
    from spiders.tpex_cb_daily_spider import TpexCbDailySpider

    results = {}

    # Stock Master
    p = PostgresPipeline(table_name="stock_master", batch_size=500, **DB_CONFIG)
    s = StockMasterSpider(pipeline=p)
    try:
        r = s.fetch_twse()
        results["stock_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
    finally:
        s.close()

    # CB Master
    p = PostgresPipeline(table_name="cb_master", batch_size=500, **DB_CONFIG)
    s = CbMasterSpider(pipeline=p)
    try:
        today = datetime.now().strftime("%Y%m%d")
        r = s.fetch_cb_master(today)
        results["cb_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
    finally:
        s.close()

    # Stock Daily（單一 symbol 示範）
    p = PostgresPipeline(table_name="stock_daily", batch_size=500, **DB_CONFIG)
    s = StockDailySpider(pipeline=p)
    try:
        now = datetime.now()
        r = s.fetch_daily("2330", now.year, now.month)
        results["stock_daily"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
    except Exception as e:
        results["stock_daily"] = {"success": False, "error": str(e)}
    finally:
        s.close()

    # TPEx CB Daily
    p = PostgresPipeline(
        table_name="tpex_cb_daily", batch_size=500, **DB_CONFIG
    )
    s = TpexCbDailySpider(pipeline=p)
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        r = s.fetch_daily(today_str)
        results["tpex_cb_daily"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
    finally:
        s.close()

    return results


def step_clean() -> dict:
    """Step 2: 執行清洗"""
    from etl.run_cleaner import DataCleaner
    cleaner = DataCleaner(DB_CONFIG)
    try:
        return cleaner.run_all()
    finally:
        cleaner.close()


def main():
    parser = argparse.ArgumentParser(description="BCAS 每日自動化流程")
    parser.add_argument("--skip-clean", action="store_true", help="只跑爬蟲")
    parser.add_argument("--clean-only", action="store_true", help="只跑清洗")
    args = parser.parse_args()

    report = {"timestamp": datetime.now().isoformat()}

    if not args.clean_only:
        print("=" * 60)
        print("Step 1: 爬蟲")
        print("=" * 60)
        spider_result = step_spiders()
        report["spiders"] = spider_result
        for name, r in spider_result.items():
            status = "✅" if r.get("success") else "❌"
            count = r.get("count", r.get("error", "?"))
            print(f"  {status} {name}: {count}")

    if not args.skip_clean:
        print()
        print("=" * 60)
        print("Step 2: 清洗")
        print("=" * 60)
        clean_result = step_clean()
        report["clean"] = {
            "stock_daily": {
                "ok": clean_result["stock_daily"]["ok"],
                "not_found": clean_result["stock_daily"]["not_found"],
            },
            "tpex_cb_daily": {
                "ok": clean_result["tpex_cb_daily"]["ok"],
                "not_found": clean_result["tpex_cb_daily"]["not_found"],
            },
        }
        print(
            f"  ✅ stock_daily:    {clean_result['stock_daily']['ok']} OK / "
            f"{clean_result['stock_daily']['not_found']} NOT_FOUND"
        )
        print(
            f"  ✅ tpex_cb_daily:  {clean_result['tpex_cb_daily']['ok']} OK / "
            f"{clean_result['tpex_cb_daily']['not_found']} NOT_FOUND"
        )

    print()
    print("=" * 60)
    print("完成")
    print("=" * 60)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
