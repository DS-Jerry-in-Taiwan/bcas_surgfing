import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from io import BytesIO
import os

def minguo_to_ad(date_str):
    # 民國年轉西元年 YYYY-MM-DD
    m = re.match(r"(\d{2,3})/(\d{2})/(\d{2})", date_str)
    if m:
        year = int(m.group(1)) + 1911
        return f"{year}-{m.group(2)}-{m.group(3)}"
    return date_str

def fetch_tpex_cb_master(target_date=None):
    # 下載 TPEx CB Master 靜態 CSV
    # 範例網址: https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2025/202501/RSdrs001.20250102-C.csv
    if target_date is None:
        target_date = datetime.now().strftime("%Y%m%d")
    elif isinstance(target_date, datetime):
        target_date = target_date.strftime("%Y%m%d")
    elif isinstance(target_date, str) and "-" in target_date:
        target_date = target_date.replace("-", "")
    year = target_date[:4]
    year_month = target_date[:6]
    url = f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/{year}/{year_month}/RSdrs001.{target_date}-C.csv"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        print(f"[WARNING] TPEx CB Master: 下載失敗 {url}")
        return
    try:
        # 先以 Big5 讀取原始內容，過濾掉 TITLE, DATADATE, GLOSS 開頭行
        raw_lines = BytesIO(resp.content).read().decode("big5", errors="ignore").splitlines()
        data_lines = [line for line in raw_lines if not (line.startswith("TITLE") or line.startswith("DATADATE") or line.startswith("GLOSS"))]
        # 將過濾後內容組回字串給 pandas
        from io import StringIO
        clean_csv = StringIO("\n".join(data_lines))
        df = pd.read_csv(clean_csv)
    except Exception as e:
        print(f"[ERROR] 讀取 CSV 失敗: {e}")
        with open(f"data/raw/master/cb_master_raw_{target_date}.bin", "wb") as f:
            f.write(resp.content)
        return
    os.makedirs("data/raw/master", exist_ok=True)
    out_path = f"data/raw/master/cb_list_{target_date}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Downloaded {len(df)} records to {out_path}")

def run(target_date=None):
    if isinstance(target_date, str) and target_date.count(",") > 0:
        # 批次下載，格式如 "20240307,20240308,20240309"
        for d in target_date.split(","):
            fetch_tpex_cb_master(d.strip())
    else:
        fetch_tpex_cb_master(target_date)

if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    run(arg)
