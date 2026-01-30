import argparse
import logging
import os
import sys
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger("crawler")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s")
    fh = logging.FileHandler("logs/crawler.log", encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

def run_pipeline(task, date, logger):
    try:
        if task in ("master", "all"):
            logger.info("Start: Stock Master")
            from crawlers.master import stock_master
            stock_master.run()
            logger.info("Done: Stock Master")
            logger.info("Start: CB Master")
            from crawlers.master import cb_master
            cb_master.run(date)
            logger.info("Done: CB Master")
        if task in ("daily", "all"):
            logger.info(f"Start: TPEx CB Daily ({date})")
            from crawlers import tpex_daily
            tpex_daily.run(target_date=date)
            logger.info("Done: TPEx CB Daily")
            # 整合清洗與入庫
            logger.info("Start: Cleaner (batch_clean)")
            from etl import cleaner
            cleaner.batch_clean()
            logger.info("Done: Cleaner")
            logger.info("Start: Validate & Enrich (daily/master)")
            from etl import validate_and_enrich
            validate_and_enrich.validate_and_enrich(logger)
            logger.info("Done: Validate & Enrich")
            logger.info("Start: Importer (DB ingest)")
            from etl import importer
            importer.main()
            logger.info("Done: Importer")
    except Exception as e:
        logger.critical(f"Pipeline failed: {e}", exc_info=True)
        raise

def run_daily_batch(start_str, end_str, logger):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    current = start
    idx = 1
    total = (end - start).days + 1
    from crawlers import tpex_daily
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        logger.info(f"[Batch] Processing {idx}/{total}: {date_str}")
        try:
            tpex_daily.run(target_date=date_str)
        except Exception as e:
            logger.warning(f"[Batch] Failed {date_str}: {e}")
        sleep_sec = random.uniform(3, 8)
        logger.info(f"[Batch] Sleep {sleep_sec:.1f}s")
        time.sleep(sleep_sec)
        current += timedelta(days=1)
        idx += 1

def main():
    parser = argparse.ArgumentParser(description="Project Gamma Surf - Main Crawler Entry")
    parser.add_argument("--task", choices=["master", "daily", "all"], required=True, help="執行任務類型")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--start-date", type=str, help="批量起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="批量結束日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    logger = setup_logging()
    logger.info(f"Triggered main_crawler.py with task={args.task}, date={args.date}, start={args.start_date}, end={args.end_date}")
    # 批量模式優先
    if args.task == "daily" and args.start_date:
        if not args.end_date:
            logger.error("Batch mode requires --end-date")
            return
        run_daily_batch(args.start_date, args.end_date, logger)
    else:
        run_pipeline(args.task, args.date, logger)

if __name__ == "__main__":
    main()