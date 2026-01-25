import pandas as pd
import requests

class CBMasterFetcher:
    CB_URL = "https://www.tpex.org.tw/web/bond/bond_info/convertible_bond/convertible_bond_list.php?l=zh-tw"

    @staticmethod
    def fetch_cb_list():
        import logging
        try:
            resp = requests.get(CBMasterFetcher.CB_URL, timeout=10)
            resp.encoding = "utf-8"
            df = pd.read_html(resp.text)[0]
            # 假設表格有「代號」、「名稱」、「標的證券代號」等欄位
            df = df.rename(columns={
                "代號": "symbol",
                "名稱": "name",
                "標的證券代號": "underlying_stock"
            })
            df["market_type"] = "TPEx"
            return df[["symbol", "name", "market_type", "underlying_stock"]]
        except Exception as e:
            logging.warning(f"TPEX CB source unreachable: {e}，CB 清單為空")
            return pd.DataFrame([])

    @staticmethod
    def get_all_cbs():
        return CBMasterFetcher.fetch_cb_list()