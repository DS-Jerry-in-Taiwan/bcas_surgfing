import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

def minguo_to_ad(date_str):
    # 民國年轉西元年 YYYY-MM-DD
    m = re.match(r"(\d{2,3})/(\d{2})/(\d{2})", date_str)
    if m:
        year = int(m.group(1)) + 1911
        return f"{year}-{m.group(2)}-{m.group(3)}"
    return date_str

def fetch_tpex_cb_master():
    url = "https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html"
    resp = requests.get(url, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    data = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 4:
            code = cols[0].get_text(strip=True)
            name = cols[1].get_text(strip=True)
            issue = minguo_to_ad(cols[2].get_text(strip=True))
            maturity = minguo_to_ad(cols[3].get_text(strip=True))
            data.append({"symbol": code, "name": name, "issue_date": issue, "maturity_date": maturity})
    df = pd.DataFrame(data)
    df.to_csv("data/raw/master/cb_list.csv", index=False, encoding="utf-8")
    print(f"Saved {len(df)} records to data/raw/master/cb_list.csv")

if __name__ == "__main__":
    fetch_tpex_cb_master()