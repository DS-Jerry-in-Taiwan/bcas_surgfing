import requests
import json
from utils.date_converter import convert_minguo_date

class TwseDailyCrawler:
    BASE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(self, stock_id, year, month):
        params = {
            "response": "json",
            "date": f"{year}{month:02d}01",
            "stockNo": stock_id
        }
        response = requests.get(self.BASE_URL, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def parse(self, response):
        return response.get("data", [])

    def save(self, data, filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def batch_fetch(self, stock_ids, year, month, out_dir):
        for stock_id in stock_ids:
            data = self.fetch(stock_id, year, month)
            parsed = self.parse(data)
            filename = f"{out_dir}/{year}-{month:02d}_{stock_id}_stock.json"
            self.save(parsed, filename)