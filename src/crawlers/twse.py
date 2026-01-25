import requests
from .base import BaseCrawler, RateLimiter

class TwseCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @RateLimiter(calls_per_sec=1)
    def fetch(self, stock_id, year, month):
        params = {
            "response": "json",
            "date": f"{year}{month:02d}01",
            "stockNo": stock_id
        }
        response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    def parse(self, response):
        # 只回傳日成交資訊
        return response.get("data", [])

    def save(self, data, filename):
        import json
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)