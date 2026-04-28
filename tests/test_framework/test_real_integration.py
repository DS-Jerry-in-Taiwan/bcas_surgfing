"""
真實 E2E 整合測試（非 Mock）

使用 pytest-httpserver 提供假的 HTTP 回應
使用真實 PostgreSQL 驗證資料寫入與去重
"""
import json
import re
from unittest.mock import Mock, patch

import pytest
import psycopg2

import sys
sys.path.insert(0, "src")

from framework.exceptions import DatabaseError
from framework.pipelines import PostgresPipeline
from spiders.stock_master_spider import StockMasterSpider
from spiders.cb_master_spider import CbMasterSpider
from spiders.stock_daily_spider import StockDailySpider
from spiders.tpex_cb_daily_spider import TpexCbDailySpider


TWSE_MASTER_HTML = """<table><tr><td>有價證券代號及名稱</td><td>ISIN</td></tr>
<tr><td>2330　台積電</td><td>TW0002330008</td></tr>
<tr><td>2317　鴻海</td><td>TW0002317005</td></tr></table>"""

TWSE_DAILY_JSON = {
    "stat": "OK",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["113/01/15", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"],
        ["113/01/16", "6,123,456", "138,901,234", "103", "108", "102", "107", "+4", "1,456"],
    ],
}

TPEX_CB_MASTER_CSV = """HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格
BODY,"35031A","TestCB","2025/01/01","2028/12/31","100.0000"
BODY,"35032B","TestCB2","2025/06/01","2029/05/31","200.0000"
""".encode("big5")

TPEX_CB_DAILY_CSV = """HEADER,代號,名稱,收市,單位
BODY,"35031A","TestCB","105.5","1000"
""".encode("big5")

DB_CONFIG = {"host": "localhost", "port": 5432, "database": "cbas", "user": "postgres", "password": "postgres"}
TABLES = ["stock_master", "stock_daily", "tpex_cb_daily", "cb_master"]


def _all_text_table(conn, table_name, columns, unique_key_col="unique_key"):
    """建立包含指定 TEXT 欄位的資料表（不含 created_at/updated_at）"""
    cur = conn.cursor()
    skip = {unique_key_col, "updated_at", "created_at"}
    data_cols = [c for c in columns if c not in skip]
    sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
      {', '.join(f'{c} TEXT' for c in data_cols)},
      {unique_key_col} TEXT UNIQUE NOT NULL,
      created_at TEXT,
      updated_at TEXT
    )"""
    cur.execute(sql)
    conn.commit()
    cur.close()


def create_tables(conn):
    cur = conn.cursor()
    for t in TABLES:
        cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    cur.close()

    _all_text_table(conn, "stock_master", ["symbol", "name", "market_type", "industry", "listing_date", "cfi_code", "source_url", "source_type", "metadata"])
    _all_text_table(conn, "stock_daily", ["symbol", "date", "open_price", "high_price", "low_price", "close_price", "volume", "turnover_rate", "price_change", "transaction_count", "source_url", "source_type", "metadata"])
    _all_text_table(conn, "cb_master", ["cb_code", "cb_name", "underlying_stock", "market_type", "issue_date", "maturity_date", "conversion_price", "coupon_rate", "source_url", "source_type", "metadata"])
    _all_text_table(conn, "tpex_cb_daily", ["cb_code", "cb_name", "underlying_stock", "trade_date", "closing_price", "volume", "turnover_rate", "premium_rate", "conversion_price", "remaining_balance", "source_url", "source_type", "metadata"])


class SafePostgresPipeline(PostgresPipeline):
    """將 item_to_dict 處理為 psycopg2 相容格式（dict→JSON，移除 auto 欄位）"""

    def item_to_dict(self, item):
        d = super().item_to_dict(item)
        skip = {"created_at", "updated_at"}
        cleaned = {}
        for k, v in d.items():
            if k in skip:
                continue
            cleaned[k] = json.dumps(v) if isinstance(v, dict) else v
        return cleaned


@pytest.fixture
def db():
    conn = psycopg2.connect(**DB_CONFIG)
    create_tables(conn)
    yield conn
    conn.close()


class TestRealHttpAndDbIntegration:

    def test_stock_master_http_and_db(self, httpserver, db):
        httpserver.expect_request("/twse").respond_with_data(TWSE_MASTER_HTML.encode("big5"), content_type="text/html")
        StockMasterSpider.TWSE_URL = httpserver.url_for("/twse")

        pipeline = SafePostgresPipeline(**DB_CONFIG)
        spider = StockMasterSpider(pipeline=pipeline)
        assert spider.fetch_twse().success is True
        spider.close()

        cur = db.cursor()
        cur.execute("SELECT symbol, name FROM stock_master ORDER BY symbol")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        assert rows[0] == ("2317", "鴻海")
        assert rows[1] == ("2330", "台積電")

    def test_stock_daily_http_and_db(self, httpserver, db):
        httpserver.expect_request("/daily").respond_with_json(TWSE_DAILY_JSON)
        StockDailySpider.TWSE_URL = httpserver.url_for("/daily")

        pipeline = SafePostgresPipeline(**DB_CONFIG)
        spider = StockDailySpider(pipeline=pipeline)
        assert spider.fetch_daily("2330", 2024, 1).success is True
        spider.close()

        cur = db.cursor()
        cur.execute("SELECT symbol, close_price FROM stock_daily ORDER BY date")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        assert rows[0][0] == "2330"

    def test_cb_master_http_and_db(self, httpserver, db):
        cb_url = re.compile(r"/2024/202401/RSdrs001\.20240115-C\.csv$")
        httpserver.expect_request(cb_url, method="GET").respond_with_data(TPEX_CB_MASTER_CSV, content_type="text/csv")
        CbMasterSpider.BASE_URL = httpserver.url_for("")

        pipeline = SafePostgresPipeline(**DB_CONFIG)
        spider = CbMasterSpider(pipeline=pipeline)
        assert spider.fetch_cb_master("20240115").success is True
        spider.close()

        cur = db.cursor()
        cur.execute("SELECT cb_code, underlying_stock FROM cb_master ORDER BY cb_code")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        assert rows[0] == ("35031A", "")
        assert rows[1] == ("35032B", "")

    def test_tpex_cb_daily_http_and_db(self, httpserver, db):
        httpserver.expect_request(re.compile(r"/tpex_cb_daily/.*"), method="GET").respond_with_data(TPEX_CB_DAILY_CSV, content_type="text/csv")
        TpexCbDailySpider.BASE_URL = httpserver.url_for("/tpex_cb_daily")

        pipeline = SafePostgresPipeline(**DB_CONFIG)
        spider = TpexCbDailySpider(pipeline=pipeline)
        assert spider.fetch_daily("2024-01-15").success is True
        spider.close()

        cur = db.cursor()
        cur.execute("SELECT cb_code, closing_price FROM tpex_cb_daily")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 1
        assert rows[0][0] == "35031A"

    def test_full_pipeline_stock_chain(self, httpserver, db):
        httpserver.expect_request("/twse").respond_with_data(TWSE_MASTER_HTML.encode("big5"), content_type="text/html")
        httpserver.expect_request("/daily").respond_with_json(TWSE_DAILY_JSON)
        StockMasterSpider.TWSE_URL = httpserver.url_for("/twse")
        StockDailySpider.TWSE_URL = httpserver.url_for("/daily")

        pipeline = SafePostgresPipeline(**DB_CONFIG)

        master = StockMasterSpider(pipeline=pipeline)
        assert master.fetch_twse().success is True
        master.close()

        daily = StockDailySpider(pipeline=pipeline)
        assert daily.fetch_daily("2330", 2024, 1).success is True
        daily.close()

        cur = db.cursor()
        cur.execute("SELECT symbol FROM stock_master ORDER BY symbol")
        symbols = [r[0] for r in cur.fetchall()]
        assert "2330" in symbols and "2317" in symbols

        cur.execute("SELECT COUNT(*) FROM stock_daily WHERE symbol='2330'")
        assert cur.fetchone()[0] == 2
        cur.close()

    def test_dedup_via_upsert(self, httpserver, db):
        httpserver.expect_request("/daily").respond_with_json(TWSE_DAILY_JSON)
        StockDailySpider.TWSE_URL = httpserver.url_for("/daily")

        pipeline = SafePostgresPipeline(unique_key="unique_key", **DB_CONFIG)
        spider = StockDailySpider(pipeline=pipeline)
        spider.fetch_daily("2330", 2024, 1)
        spider.fetch_daily("2330", 2024, 1)
        spider.close()

        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM stock_daily WHERE symbol='2330'")
        count = cur.fetchone()[0]
        cur.close()
        assert count == 2, f"upsert 後應為 2 筆，實際 {count} 筆"
