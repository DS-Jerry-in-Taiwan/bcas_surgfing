import requests
from datetime import date, timedelta

def fetch_tpex_csv_direct(download_url, out_path):
    resp = requests.get(download_url, timeout=10)
    with open(out_path, "wb") as f:
        f.write(resp.content)
    print(f"Downloaded to {out_path}")

def gen_dates(year, month):
    d = date(year, month, 1)
    while d.month == month:
        yield d
        d += timedelta(days=1)

if __name__ == "__main__":
    year, month = 2025, 1
    for d in gen_dates(year, month):
        yyy = d.year - 1911
        mm = f"{d.month:02d}"
        dd = f"{d.day:02d}"
        # 範例檔名格式
        fname = f"RSta0113.{d.year}{mm}{dd}-C.csv"
        url = f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/{d.year}/{d.year}{mm}/{fname}"
        out_path = f"data/raw/daily_samples/{fname}"
        fetch_tpex_csv_direct(url, out_path)