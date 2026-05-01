"""
run_daily.py - 每日自動化流程

依序執行：
  1. 爬蟲（spiders）
  2. 驗證（validators）- NEW in Phase 2
  3. 清洗（run_cleaner.py）
  4. 輸出報告

用法：
  python3 src/run_daily.py                        # 執行全部
  python3 src/run_daily.py --skip-clean           # 只跑爬蟲
  python3 src/run_daily.py --clean-only           # 只跑清洗
  python3 src/run_daily.py --validate-only        # 只跑爬蟲+驗證
  python3 src/run_daily.py --force-validation     # 驗證失敗也繼續
"""
import argparse
import json
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_CONFIG = dict(
    host="localhost", port=5432, database="cbas",
    user="postgres", password="postgres",
)


def step_spiders() -> tuple:
    """Step 1: 執行爬蟲（collect_only 模式，不寫入 DB）
    
    Returns:
        (metadata_results, collected_records, pipelines)
        - metadata_results: dict {table: {success, count, error}}
        - collected_records: dict {table: [{...}, ...]}
        - pipelines: dict {table: (PostgresPipeline, spider)} for later flush
    """
    from framework.pipelines import PostgresPipeline
    from spiders.stock_master_spider import StockMasterSpider
    from spiders.cb_master_spider import CbMasterSpider
    from spiders.stock_daily_spider import StockDailySpider
    from spiders.tpex_cb_daily_spider import TpexCbDailySpider

    results = {}
    records = {}
    pipelines = {}

    # Stock Master
    p = PostgresPipeline(table_name="stock_master", batch_size=500, **DB_CONFIG)
    s = StockMasterSpider(pipeline=p)
    s.collect_only = True
    try:
        r = s.fetch_twse()
        results["stock_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["stock_master"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["stock_master"] = (p, s)
    except:
        s.close()
        raise

    # CB Master
    p = PostgresPipeline(table_name="cb_master", batch_size=500, **DB_CONFIG)
    s = CbMasterSpider(pipeline=p)
    s.collect_only = True
    try:
        today = datetime.now().strftime("%Y%m%d")
        r = s.fetch_cb_master(today)
        results["cb_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["cb_master"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["cb_master"] = (p, s)
    except:
        s.close()
        raise

    # Stock Daily（單一 symbol 示範）
    p = PostgresPipeline(table_name="stock_daily", batch_size=500, **DB_CONFIG)
    s = StockDailySpider(pipeline=p)
    s.collect_only = True
    try:
        now = datetime.now()
        r = s.fetch_daily("2330", now.year, now.month)
        results["stock_daily"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["stock_daily"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["stock_daily"] = (p, s)
    except Exception as e:
        results["stock_daily"] = {"success": False, "error": str(e)}
        records["stock_daily"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["stock_daily"] = (p, s)

    # TPEx CB Daily
    p = PostgresPipeline(
        table_name="tpex_cb_daily", batch_size=500, **DB_CONFIG
    )
    s = TpexCbDailySpider(pipeline=p)
    s.collect_only = True
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        r = s.fetch_daily(today_str)
        results["tpex_cb_daily"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["tpex_cb_daily"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["tpex_cb_daily"] = (p, s)
    except:
        s.close()
        raise

    return results, records, pipelines


def flush_pipelines(pipelines: dict) -> None:
    """將暫存的 items 寫入 DB（驗證通過後呼叫）"""
    for table_name, (pipeline, spider) in pipelines.items():
        try:
            count = spider.get_pending_count()
            if count > 0:
                logger.info(f"Flushing {count} items to {table_name}...")
                spider.flush_items(pipeline)
            pipeline.close()
            logger.info(f"  ✅ {table_name}: {count} records written")
        except Exception as e:
            logger.error(f"  ❌ {table_name} flush failed: {e}")


def save_failed_records(spider_records: dict, validation_reports: dict) -> str:
    """驗證失敗時，將失敗的 records 寫入 logs/validation/failed/（不污染 DB）
    
    Args:
        spider_records: {table: [{...}, ...]} 原始 records
        validation_reports: {table: {...}} 驗證報告（含 failed_rules）
    
    Returns:
        寫入的檔案路徑
    """
    from datetime import datetime as dt
    import json

    out_dir = Path("logs/validation/failed")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.now().strftime("%Y-%m-%d_%H%M%S")

    failed_data = {
        "timestamp": timestamp,
        "summary": {
            "total_tables": len(spider_records),
            "failed_tables": [],
            "total_records": sum(len(v) for v in spider_records.values()),
        },
        "tables": {},
    }

    for table_name, records in spider_records.items():
        report = validation_reports.get(table_name, {})
        if isinstance(report, dict) and report.get("failed_rules"):
            failed_data["summary"]["failed_tables"].append(table_name)
            failed_data["tables"][table_name] = {
                "total_records": len(records),
                "failed_rules": [
                    {"rule_id": r["rule_id"], "detail": r["detail"]}
                    for r in report["failed_rules"]
                ],
                "records": records,
            }

    filepath = out_dir / f"{timestamp}_failed.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(failed_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Failed records saved to {filepath}")
    return str(filepath)


def step_validate(spider_results: dict, collected_records: dict = None) -> dict:
    """Step 2: 執行驗證
    
    Args:
        spider_results: From step_spiders() — metadata per table
        collected_records: Raw record dicts per table, e.g.
            {"stock_master": [{"symbol": "2330", ...}, ...]}
    
    Returns:
        Validation report dict with actual rule-level results
    """
    try:
        from validators.checker import DataValidator
        from validators.report_writer import ReportWriter
    except ImportError:
        DataValidator = None
        ReportWriter = None

    validation_dir = Path("logs/validation")
    validation_dir.mkdir(parents=True, exist_ok=True)

    validation_reports = {}
    validated_objects = {}
    global_has_errors = False

    try:
        for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
            spider_result = spider_results.get(table_name, {})

            if not spider_result.get("success"):
                logger.warning(f"Skipping validation for {table_name}: spider failed")
                validation_reports[table_name] = {
                    "skipped": True,
                    "reason": "spider failed"
                }
                continue

            records = (collected_records or {}).get(table_name, [])
            if not records:
                logger.warning(f"Skipping validation for {table_name}: no records")
                validation_reports[table_name] = {
                    "skipped": True,
                    "reason": "no records"
                }
                continue

            if not DataValidator:
                logger.warning(f"Cannot validate {table_name}: validators not available")
                validation_reports[table_name] = {
                    "validated": True,
                    "count": len(records),
                    "status": "pending",
                    "reason": "DataValidator not available"
                }
                continue

            # Build cross-reference parameters for consistency checks
            master_symbols = [
                r["symbol"] for r in (collected_records or {}).get("stock_master", [])
                if r.get("symbol")
            ] if collected_records else None

            master_cb_codes = [
                r["cb_code"] for r in (collected_records or {}).get("cb_master", [])
                if r.get("cb_code")
            ] if collected_records else None

            logger.info(f"Running DataValidator on {table_name} ({len(records)} records)...")
            validator = DataValidator(
                table_name=table_name,
                records=records,
                expected_symbols=master_symbols if table_name == "stock_daily" else None,
                expected_cb_codes=master_cb_codes if table_name == "tpex_cb_daily" else None,
            )
            report = validator.run()

            table_has_errors = report.has_errors()
            if table_has_errors:
                global_has_errors = True

            # Store both the object (for saving) and dict (for return)
            validated_objects[table_name] = report
            validation_reports[table_name] = report.to_dict()

            status_icon = "✅" if not table_has_errors else "❌"
            summary = report.summary
            logger.info(
                f"  {status_icon} {table_name}: "
                f"{summary['passed']} passed / "
                f"{summary['failed']} failed / "
                f"{summary['warnings']} warnings / "
                f"{summary['skipped']} skipped"
            )

        # Save validated reports
        if ReportWriter and validated_objects:
            try:
                report_path = ReportWriter.save_summary(validated_objects, str(validation_dir))
                logger.info(f"Validation reports saved to {report_path}")
                for table_name, report_obj in validated_objects.items():
                    try:
                        ReportWriter.save_report(report_obj, str(validation_dir))
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Could not save validation reports: {e}")

        return {
            "validation_dir": str(validation_dir),
            "reports": validation_reports,
            "has_errors": global_has_errors,
        }

    except Exception as e:
        logger.error(f"Validation step failed: {e}")
        return {
            "validation_dir": str(validation_dir),
            "reports": validation_reports,
            "has_errors": True,
            "error": str(e),
        }


def step_clean() -> dict:
    """Step 3: 執行清洗"""
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
    parser.add_argument("--validate-only", action="store_true", 
                        help="只跑爬蟲+驗證（不寫入DB或清洗）")
    parser.add_argument("--force-validation", action="store_true",
                        help="驗證失敗也繼續（跳過中止）")
    args = parser.parse_args()

    report = {"timestamp": datetime.now().isoformat()}

    if not args.clean_only:
        print("=" * 60)
        print("Step 1: 爬蟲（collect only，暫不寫入 DB）")
        print("=" * 60)
        spider_result, spider_records, spider_pipelines = step_spiders()
        report["spiders"] = spider_result
        for name, r in spider_result.items():
            status = "✅" if r.get("success") else "❌"
            count = r.get("count", r.get("error", "?"))
            print(f"  {status} {name}: {count}")

        # Step 2: Validation
        if not args.clean_only:
            print()
            print("=" * 60)
            print("Step 2: 驗證")
            print("=" * 60)
            validation_result = step_validate(spider_result, spider_records)
            report["validation"] = validation_result

            validation_dir = validation_result.get("validation_dir")
            has_errors = validation_result.get("has_errors", False)

            if has_errors:
                print(f"  ❌ 驗證失敗")
                print(f"  報告位置: {validation_dir}")

                if not args.force_validation:
                    # Save failed records to quarantine before clearing
                    failed_path = save_failed_records(spider_records, validation_result["reports"])
                    print(f"  失敗資料已保留: {failed_path}")
                    # Close pipelines without flushing
                    for _, (p, s) in spider_pipelines.items():
                        s._pending_items.clear()
                        p.close()
                    print()
                    print("=" * 60)
                    print("中止執行（使用 --force-validation 跳過）")
                    print("=" * 60)
                    print(json.dumps(report, indent=2, ensure_ascii=False))
                    sys.exit(1)
                else:
                    print(f"  ⚠️  強制繼續（--force-validation）")
            else:
                print(f"  ✅ 驗證通過")
                print(f"  報告位置: {validation_dir}")

            # Step 2.5: Write to DB (after validation passes or force, unless --validate-only)
            if not args.validate_only:
                print()
                print("=" * 60)
                print("Step 2.5: 寫入 DB")
                print("=" * 60)
                flush_pipelines(spider_pipelines)
            else:
                # --validate-only: clear pending items without writing
                for _, (p, s) in spider_pipelines.items():
                    s._pending_items.clear()
                    p.close()
                print()
                print("=" * 60)
                print("完成（--validate-only）")
                print("=" * 60)
                print(json.dumps(report, indent=2, ensure_ascii=False))
                sys.exit(0 if not has_errors else 1)

    if not args.skip_clean:
        print()
        print("=" * 60)
        print("Step 3: 清洗")
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
