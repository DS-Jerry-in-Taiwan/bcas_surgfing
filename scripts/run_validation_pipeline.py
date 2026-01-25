import os
import random
from datetime import datetime
from crawlers.master.stock_crawler import StockMasterFetcher
from crawlers.master.cb_crawler import CBMasterFetcher
from crawlers.daily.twse_daily import TwseDailyCrawler
from crawlers.daily.tpex_cb_daily import TpexCbDailyCrawler

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    # Step 1: 抓全清單
    import logging

    stock_df = StockMasterFetcher.get_all_stocks()
    cb_df = CBMasterFetcher.get_all_cbs()
    ensure_dir("data/raw/master")
    stock_df.to_csv("data/raw/master/stock_list.csv", index=False, encoding="utf-8")
    cb_df.to_csv("data/raw/master/cb_list.csv", index=False, encoding="utf-8")

    # Step 2: 挑選 [2330, 52694] + 隨機 3 檔
    stock_symbols = stock_df["symbol"].tolist()
    cb_symbols = cb_df["symbol"].tolist() if not cb_df.empty and "symbol" in cb_df.columns else []
    targets = set()
    if "2330" in stock_symbols:
        targets.add("2330")
    if "52694" in cb_symbols:
        targets.add("52694")
    # 隨機抽樣時需檢查 list 是否足夠
    if len(stock_symbols) > 2:
        targets.update(random.sample(stock_symbols, 2))
    elif len(stock_symbols) > 0:
        targets.update(stock_symbols)
    if len(cb_symbols) > 0:
        targets.update(random.sample(cb_symbols, min(1, len(cb_symbols))))
    targets = list(targets)

    # Step 3: 爬取這些標的的日資料
    now = datetime.now()
    year, month = now.year, now.month
    today = now.strftime("%Y-%m-%d")
    ensure_dir("data/raw/stock")
    ensure_dir("data/raw/cb")

    twse_targets = [s for s in targets if s in stock_symbols]
    cb_targets = [s for s in targets if s in cb_symbols]

    if twse_targets:
        twse_crawler = TwseDailyCrawler()
        twse_crawler.batch_fetch(twse_targets, year, month, "data/raw/stock")
    if cb_targets:
        tpex_cb_crawler = TpexCbDailyCrawler()
        tpex_cb_crawler.batch_fetch(cb_targets, today, "data/raw/cb")

    # Step 4: 驗證檔案存在且非空
    for s in twse_targets:
        f = f"data/raw/stock/{year}-{month:02d}_{s}_stock.json"
        assert os.path.exists(f) and os.path.getsize(f) > 0, f"Stock file missing or empty: {f}"
    for s in cb_targets:
        f = f"data/raw/cb/{today}_{s}_cb.csv"
        assert os.path.exists(f) and os.path.getsize(f) > 0, f"CB file missing or empty: {f}"

    if len(cb_symbols) == 0:
        logging.warning("⚠️ TPEX source unreachable or CB list empty, proceeding with TWSE only. [Partial Success]")
        print("Validation pipeline completed with warnings (Partial Success).")
    else:
        print("Validation pipeline completed successfully.")

if __name__ == "__main__":
    main()