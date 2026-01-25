import requests
import pandas as pd
from io import BytesIO

class TpexCbDailyCrawler:
    BASE_URL = "https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch(self, date):
        params = {
            "l": "zh-tw",
            "d": date.replace("-", "/")
        }
        response = requests.get(self.BASE_URL, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()
        return response.content

    def parse(self, response):
        df = pd.read_csv(BytesIO(response), encoding="utf-8")
        return df

    def save(self, data, filename):
        data.to_csv(filename, index=False, encoding="utf-8")

    def batch_fetch(self, cb_symbols, date, out_dir):
        # 下載當日所有 CB，再依 symbol 過濾
        content = self.fetch(date)
        df = self.parse(content)
        for symbol in cb_symbols:
            filtered = df[df["代號"] == symbol]
            if not filtered.empty:
                filename = f"{out_dir}/{date}_{symbol}_cb.csv"
                self.save(filtered, filename)