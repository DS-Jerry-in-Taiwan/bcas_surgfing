import requests

def fetch_tpex_csv_direct(download_url, out_path):
    resp = requests.get(download_url, timeout=10)
    with open(out_path, "wb") as f:
        f.write(resp.content)
    print(f"Downloaded to {out_path}")

if __name__ == "__main__":
    url = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202601/RSta0113.20260123-C.csv"
    out_path = "data/raw/daily_samples/test_quote_direct.csv"
    fetch_tpex_csv_direct(url, out_path)