import pandas as pd
import requests

class StockMasterFetcher:
    TWSE_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    TPEX_URL = "https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4"

    @staticmethod
    def fetch_twse():
        resp = requests.get(StockMasterFetcher.TWSE_URL)
        resp.encoding = "big5"
        df = pd.read_html(resp.text, encoding="big5")[0]
        df.columns = df.iloc[0]
        df = df[1:]
        # 取得正確欄位名稱
        col_name = [c for c in df.columns if "代號" in str(c) and "名稱" in str(c)][0]
        df = df[df[col_name].notnull()]
        df = df[df[col_name].str.contains("　")]
        df["symbol"] = df[col_name].str.split("　").str[0]
        df["name"] = df[col_name].str.split("　").str[1]
        df["market_type"] = "TWSE"
        return df[["symbol", "name", "market_type"]]

    @staticmethod
    def fetch_tpex():
        import logging
        try:
            resp = requests.get(StockMasterFetcher.TPEX_URL, timeout=10)
            resp.encoding = "utf-8"
            df = pd.read_html(resp.text)[0]
            df.columns = df.iloc[0]
            df = df[1:]
            df = df[df["有價證券代號及名稱"].notnull()]
            df = df[df["有價證券代號及名稱"].str.contains("　")]
            df["symbol"] = df["有價證券代號及名稱"].str.split("　").str[0]
            df["name"] = df["有價證券代號及名稱"].str.split("　").str[1]
            df["market_type"] = "TPEx"
            return df[["symbol", "name", "market_type"]]
        except Exception as e:
            logging.warning(f"TPEX source unreachable: {e}，僅執行 TWSE")
            return pd.DataFrame([])

    @staticmethod
    def get_all_stocks():
        twse = StockMasterFetcher.fetch_twse()
        tpex = StockMasterFetcher.fetch_tpex()
        return pd.concat([twse, tpex], ignore_index=True)