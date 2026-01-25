import requests
import os
from datetime import datetime

def get_tpex_cb_daily_csv_url(date=None):
    """
    產生 TPEx 可轉債日行情 CSV 下載連結
    :param date: YYYY-MM-DD
    :return: download_url, out_path
    """
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    dt = datetime.strptime(date, "%Y-%m-%d")
    yyyymm = dt.strftime("%Y%m")
    yyyymmdd = dt.strftime("%Y%m%d")
    url = f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/{dt.year}/{yyyymm}/RSta0113.{yyyymmdd}-C.csv"
    out_path = f"data/raw/daily/tpex_cb_daily_{yyyymmdd}.csv"
    return url, out_path

def fetch_tpex_cb_daily_csv(date=None):
    url, out_path = get_tpex_cb_daily_csv_url(date)
    print(f"[DEBUG] Downloading: {url}")
    resp = requests.get(url, timeout=10)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if resp.status_code == 200 and resp.content[:6] != b'<!DOCT':
        try:
            content = resp.content.decode("utf-8")
        except Exception:
            content = resp.content.decode("cp950", errors="replace")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Downloaded to {out_path}")
        return out_path
    else:
        print(f"[ERROR] Download failed, status={resp.status_code}, prefix={resp.content[:100]}")
        with open("logs/error_response.html", "wb") as f:
            f.write(resp.content)
        return None

def run(target_date=None):
    fetch_tpex_cb_daily_csv(target_date)

if __name__ == "__main__":
    run()