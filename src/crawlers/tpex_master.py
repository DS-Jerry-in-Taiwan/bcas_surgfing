import requests
from bs4 import BeautifulSoup
import pandas as pd

def fetch_tpex_cb_master(url="https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html"):
    resp = requests.get(url, timeout=10)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")
    data = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            code = cols[0].get_text(strip=True)
            name = cols[1].get_text(strip=True)
            data.append({"symbol": code, "name": name})
    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    df = fetch_tpex_cb_master()
    df.to_csv("data/raw/master/cb_list.csv", index=False, encoding="utf-8")
    print(f"Saved {len(df)} records to data/raw/master/cb_list.csv")