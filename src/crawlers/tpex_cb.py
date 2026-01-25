import requests
from .base import BaseCrawler, RateLimiter

class TpexCbCrawler(BaseCrawler):
    def __init__(self):
        self.base_url = "https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @RateLimiter(calls_per_sec=1)
    def fetch(self, date):
        params = {
            "l": "zh-tw",
            "d": date.replace("-", "/")
        }
        response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.content

    def parse(self, response):
        import pandas as pd
        from io import BytesIO
        df = pd.read_csv(BytesIO(response), encoding="utf-8")
        return df

    def save(self, data, filename):
        data.to_csv(filename, index=False, encoding="utf-8")