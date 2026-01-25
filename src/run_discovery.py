import os
from crawlers.twse import TwseCrawler
from crawlers.tpex_cb import TpexCbCrawler
from utils.date_converter import convert_minguo_date
from datetime import datetime

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def fetch_twse_sample():
    crawler = TwseCrawler()
    stock_id = "2330"
    now = datetime.now()
    year = now.year
    month = now.month
    data = crawler.fetch(stock_id, year, month)
    parsed = crawler.parse(data)
    filename = f"data/raw/stock/{year}-{month:02d}_stock.json"
    crawler.save(parsed, filename)
    print(f"TWSE data saved: {filename}")

def fetch_tpex_cb_sample():
    crawler = TpexCbCrawler()
    today = datetime.now().strftime("%Y-%m-%d")
    data = crawler.fetch(today)
    parsed = crawler.parse(data)
    filename = f"data/raw/cb/{today}_cb.csv"
    crawler.save(parsed, filename)
    print(f"TPEx CB data saved: {filename}")

if __name__ == "__main__":
    ensure_dir("data/raw/stock")
    ensure_dir("data/raw/cb")
    fetch_twse_sample()
    fetch_tpex_cb_sample()