import requests
import pandas as pd

def fetch_twse_stock_master():
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json"
    resp = requests.get(url, timeout=10)
    data = resp.json().get("data", [])
    # 欄位順序: [代號, 名稱, ...]
    df = pd.DataFrame(data, columns=["symbol", "name"] + [f"col{i}" for i in range(len(data[0])-2)])
    # 僅保留4碼普通股
    df = df[df["symbol"].str.len() == 4]
    df = df[["symbol", "name"]].reset_index(drop=True)
    df.to_csv("data/raw/master/stock_list.csv", index=False, encoding="utf-8")
    print(f"Saved {len(df)} records to data/raw/master/stock_list.csv")

def run(target_date=None):
    fetch_twse_stock_master()

if __name__ == "__main__":
    run()
