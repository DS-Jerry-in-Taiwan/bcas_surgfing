import requests
import pandas as pd
from datetime import datetime

def fetch_tpex_cb_daily(date=None):
    """
    下載 TPEx 可轉債每日行情
    :param date: YYYY-MM-DD (預設為昨日)
    :return: DataFrame
    """
    if date is None:
        date = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y/%m/%d")
    else:
        date = pd.to_datetime(date).strftime("%Y/%m/%d")
    url = "https://www.tpex.org.tw/web/bond/tradeinfo/cb/cb_daily.php"
    params = {
        "l": "zh-tw",
        "d": date
    }
    resp = requests.post(url, data=params, timeout=10)
    resp.encoding = "utf-8"
    # 回傳格式為 JSON，內含 "aaData" 欄位
    data = resp.json()
    df = pd.DataFrame(data.get("aaData", []))
    return df

if __name__ == "__main__":
    df = fetch_tpex_cb_daily()
    out_path = "data/raw/daily/tpex_cb_daily.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Saved {len(df)} records to {out_path}")