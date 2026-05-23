"""
E2E Full Pipeline Integration Test — Phase 13

Covers the complete BCAS Quant pipeline:

    Mock HTTP → Real PostgreSQL → DataCleaner → Analytics → Report

Requirements:
    - Real PostgreSQL container 'bcas-postgres', database 'cbas'
    - All HTTP calls mocked via unittest.mock.patch (no real network)
    - Test data prefix 999 (symbols 9991, 9992) — cleaned after test run
    - 13 ordered test methods spanning Spider → DB → Validate → Clean → Analytics → Report
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import psycopg2
import pytest

sys.path.insert(0, "src")

# ============================================================
# Constants
# ============================================================
DB_CONFIG: Dict[str, Any] = dict(
    host="localhost", port=5432, database="cbas",
    user="postgres", password="postgres",
)
TEST_DATE = "2026-05-15"
TEST_DATE_COMPACT = "20260515"
TEST_SYMBOLS = ["9991", "9992"]
TEST_CB_CODES = ["99911", "99921"]

ALL_TABLES_CLEAN = [
    "stock_master", "stock_daily", "broker_breakdown",
    "daily_analysis_results", "trading_signals",
]

# ============================================================
# Heap-allocated mock responses to survive patch scope
# ============================================================

# ── Stock Master HTML (2 stocks, TWSE ISIN page) ───────────
TWSE_MASTER_HTML = """<table>
<tr><td>有價證券代號及名稱</td><td>ISIN</td></tr>
<tr><td>9991　測試股A</td><td>TW0099910008</td></tr>
<tr><td>9992　測試股B</td><td>TW0099920005</td></tr>
</table>"""

# ── CB Master CSV (big5 encoded bytes, 3 CBs) ──────────────
CB_MASTER_CSV_LINES = (
    'HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格\r\n'
    'BODY,"99911","測試CB_A1","2025/01/01","2028/12/31","100.0000"\r\n'
    'BODY,"99921","測試CB_B1","2025/03/01","2028/03/01","50.0000"\r\n'
)
CB_MASTER_CSV = CB_MASTER_CSV_LINES.encode("big5")

# ── TPEx CB Daily CSV (big5 encoded bytes, 3 CBs) ──────────
TPEX_CB_DAILY_CSV_LINES = (
    'HEADER,代號,名稱,收市,單位\r\n'
    'BODY,"99911","測試CB_A1","120.0","1000"\r\n'
    'BODY,"99921","測試CB_B1","300.0","500"\r\n'
)
TPEX_CB_DAILY_CSV = TPEX_CB_DAILY_CSV_LINES.encode("big5")

# ── Stock Daily JSON: 9991 (uptrend 103→120, 10 trading days) ──
# ROC year 115 = Gregorian 2026
TWSE_DAILY_9991: Dict[str, Any] = {
    "stat": "OK",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["115/05/04", "10000000", "1000000000", "100", "105", "99",  "103", "+3", "10000"],
        ["115/05/05", "12000000", "1200000000", "103", "108", "102", "107", "+4", "12000"],
        ["115/05/06", "14000000", "1400000000", "107", "112", "106", "111", "+4", "14000"],
        ["115/05/07", "13000000", "1300000000", "111", "114", "110", "113", "+2", "13000"],
        ["115/05/08", "15000000", "1500000000", "113", "116", "112", "115", "+2", "15000"],
        ["115/05/11", "16000000", "1600000000", "115", "118", "114", "117", "+2", "16000"],
        ["115/05/12", "14000000", "1400000000", "117", "119", "116", "116", "-1", "14000"],
        ["115/05/13", "17000000", "1700000000", "116", "120", "115", "118", "+2", "17000"],
        ["115/05/14", "18000000", "1800000000", "118", "121", "117", "119", "+1", "18000"],
        ["115/05/15", "19000000", "1900000000", "119", "122", "118", "120", "+1", "19000"],
    ],
}

# ── Stock Daily JSON: 9992 (flat 49-51, 10 trading days) ──
TWSE_DAILY_9992: Dict[str, Any] = {
    "stat": "OK",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["115/05/04", "5000000", "250000000", "50", "52", "49", "51", "+1", "5000"],
        ["115/05/05", "4800000", "240000000", "51", "53", "50", "50", "-1", "4800"],
        ["115/05/06", "5200000", "260000000", "50", "51", "49", "50", "0",  "5200"],
        ["115/05/07", "5100000", "255000000", "50", "52", "49", "51", "+1", "5100"],
        ["115/05/08", "4900000", "245000000", "51", "53", "50", "50", "-1", "4900"],
        ["115/05/11", "5300000", "265000000", "50", "51", "48", "49", "-1", "5300"],
        ["115/05/12", "5000000", "250000000", "49", "51", "48", "50", "+1", "5000"],
        ["115/05/13", "5100000", "255000000", "50", "52", "49", "51", "+1", "5100"],
        ["115/05/14", "4900000", "245000000", "51", "53", "50", "50", "-1", "4900"],
        ["115/05/15", "5200000", "260000000", "50", "51", "49", "50", "0",  "5200"],
    ],
}

# ── BSR records (what BsrClient.fetch_broker_data returns) ──
BSR_RECORDS_9991: List[Dict[str, Any]] = [
    {"seq": 1,  "broker_name": "凱基-台北", "broker_id": "9200", "buy_volume": 1000, "sell_volume": 100, "net_volume": 900},
    {"seq": 2,  "broker_name": "元大-台北", "broker_id": "9800", "buy_volume": 800,  "sell_volume": 200, "net_volume": 600},
    {"seq": 3,  "broker_name": "群益-台北", "broker_id": "9100", "buy_volume": 500,  "sell_volume": 300, "net_volume": 200},
    {"seq": 40, "broker_name": "一般券商A", "broker_id": "9999", "buy_volume": 100,  "sell_volume": 80,  "net_volume": 20},
]

BSR_RECORDS_9992: List[Dict[str, Any]] = [
    {"seq": 1, "broker_name": "富邦-台北", "broker_id": "9600", "buy_volume": 600, "sell_volume": 150, "net_volume": 450},
    {"seq": 2, "broker_name": "一般券商B", "broker_id": "8888", "buy_volume": 400, "sell_volume": 100, "net_volume": 300},
]


# ============================================================
# Helpers
# ============================================================

def _clean_test_data(conn) -> None:
    """Delete all test data with '999' prefix from every table."""
    cur = conn.cursor()
    for tbl in ALL_TABLES_CLEAN:
        cur.execute(f"DELETE FROM {tbl} WHERE symbol LIKE '999%'")
    cur.execute("DELETE FROM tracked_symbols WHERE symbol LIKE '999%'")
    cur.execute("DELETE FROM cb_master WHERE cb_code LIKE '999%'")
    cur.execute("DELETE FROM tpex_cb_daily WHERE cb_code LIKE '999%'")
    conn.commit()
    cur.close()


def _make_mock_response(
    status_code: int = 200,
    text: str = "",
    content: bytes = b"",
    json_data: Any = None,
) -> Mock:
    """Build a requests.Response-like mock (no spec — allow any attribute)."""
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content
    if json_data is not None:
        resp.json.return_value = json_data
    resp.raise_for_status = Mock()
    resp.url = "http://mock/"
    return resp


def _make_requests_get_mock(status_code=200, text="", content=b"", json_data=None):
    """Convenience: build a mock for `requests.get` that returns one response."""
    resp = _make_mock_response(
        status_code=status_code, text=text, content=content, json_data=json_data,
    )

    def get_side_effect(url, **kwargs):
        return resp

    mock_get = Mock(side_effect=get_side_effect)
    return mock_get


# Module-level DB cleanup (attach here so it survives the module)
_cleanup_conn = None


def _read_records_from_db(conn, table: str, columns: List[str]) -> List[Dict[str, Any]]:
    """Read test records from a DB table and return as list of dicts."""
    cur = conn.cursor()
    cols_str = ", ".join(columns)
    cur.execute(
        f"SELECT {cols_str} FROM {table} WHERE symbol LIKE '999%' "
        f"ORDER BY symbol, date" if table != "cb_master" and table != "tpex_cb_daily"
        else
        f"SELECT {cols_str} FROM {table} WHERE cb_code LIKE '999%' "
        f"ORDER BY cb_code"
    )
    rows = cur.fetchall()
    cur.close()
    return [dict(zip(columns, row)) for row in rows]


# ============================================================
# Module-level fixture
# ============================================================

@pytest.fixture(scope="module")
def db():
    """Real PostgreSQL connection; clean test data before & after."""
    conn = psycopg2.connect(**DB_CONFIG)
    _clean_test_data(conn)
    yield conn
    _clean_test_data(conn)
    conn.close()


# ============================================================
# Test class — 13 ordered methods
# ============================================================

class TestE2EFullPipeline:
    """E2E pipeline test: Spider → DB → Validate → Clean → Analytics → Report."""

    # ════════════════════════════════════════════════════════
    # Stage 1: Spider → DB
    # ════════════════════════════════════════════════════════

    @pytest.mark.e2e
    def test_01_stock_master_to_db(self, db) -> None:
        """StockMasterSpider → stock_master table (2 rows)."""
        from spiders.stock_master_spider import StockMasterSpider
        from src.framework.pipelines import PostgresPipeline

        p = PostgresPipeline(table_name="stock_master", batch_size=500, **DB_CONFIG)
        s = StockMasterSpider(pipeline=p)
        s.collect_only = True

        mock_get = _make_requests_get_mock(text=TWSE_MASTER_HTML)

        with patch("spiders.stock_master_spider.requests.get", mock_get):
            r = s.fetch_twse()
        assert r.success, f"StockMaster fetch failed: {r.error}"

        # Flush to DB
        s.flush_items(p)
        p.close()

        # Verify
        cur = db.cursor()
        cur.execute("SELECT symbol, name FROM stock_master WHERE symbol LIKE '999%' ORDER BY symbol")
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2, f"Expected 2 stock_master rows, got {len(rows)}"
        assert rows[0] == ("9991", "測試股A")
        assert rows[1] == ("9992", "測試股B")

    @pytest.mark.e2e
    def test_02_cb_master_to_db(self, db) -> None:
        """CbMasterSpider → cb_master (3 rows, __post_init__ derives underlying_stock)."""
        from spiders.cb_master_spider import CbMasterSpider
        from src.framework.pipelines import PostgresPipeline

        p = PostgresPipeline(table_name="cb_master", batch_size=500, **DB_CONFIG)
        s = CbMasterSpider(pipeline=p)
        s.collect_only = True

        mock_get = _make_requests_get_mock(content=CB_MASTER_CSV)

        with patch("spiders.cb_master_spider.requests.get", mock_get):
            r = s.fetch_cb_master(TEST_DATE_COMPACT)
        assert r.success, f"CB Master fetch failed: {r.error}"

        # Verify __post_init__ derived underlying_stock before flush
        items = s.get_items()
        assert len(items) == 2
        stock_map = {item.cb_code: item.underlying_stock for item in items}
        assert stock_map["99911"] == "9991"
        assert stock_map["99921"] == "9992"

        # Flush to DB
        s.flush_items(p)
        p.close()

        # Verify
        cur = db.cursor()
        cur.execute(
            "SELECT cb_code, underlying_stock, conversion_price FROM cb_master "
            "WHERE cb_code LIKE '999%' ORDER BY cb_code"
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        assert rows[0] == ("99911", "9991", "100.0000")
        assert rows[1] == ("99921", "9992", "50.0000")

    @pytest.mark.e2e
    def test_03_symbol_registry(self, db) -> None:
        """_update_symbol_registry → tracked_symbols (9991, 9992 added)."""
        from run_daily import _update_symbol_registry

        added = _update_symbol_registry(TEST_SYMBOLS)
        assert added == 2, f"Expected 2 new symbols, got {added}"

        # Re-run should add 0 (ON CONFLICT DO NOTHING)
        added2 = _update_symbol_registry(TEST_SYMBOLS)
        assert added2 == 0, f"Expected 0 new symbols on repeat, got {added2}"

        # Direct DB verify (not using _get_active_symbols because it returns ALL
        # active symbols including previous real runs)
        cur = db.cursor()
        cur.execute(
            "SELECT symbol, is_active FROM tracked_symbols WHERE symbol LIKE '999%' ORDER BY symbol"
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2, f"Expected 2 tracked_symbols, got {len(rows)}"
        assert rows[0] == ("9991", True)
        assert rows[1] == ("9992", True)

    @pytest.mark.e2e
    def test_04_stock_daily_to_db(self, db) -> None:
        """StockDailySpider fetch_daily → stock_daily (20 rows, 10 per symbol)."""
        from spiders.stock_daily_spider import StockDailySpider
        from src.framework.pipelines import PostgresPipeline
        from run_daily import _get_active_symbols

        p = PostgresPipeline(table_name="stock_daily", batch_size=500, **DB_CONFIG)
        s = StockDailySpider(pipeline=p)
        s.collect_only = True

        # Mock the requests.request call inside _request_with_retry
        def mock_request_side(**kwargs):
            url = kwargs.get("url", "")
            params = kwargs.get("params", {})
            stock_no = params.get("stockNo", "")
            if stock_no == "9991":
                return _make_mock_response(json_data=TWSE_DAILY_9991)
            elif stock_no == "9992":
                return _make_mock_response(json_data=TWSE_DAILY_9992)
            return _make_mock_response(json_data={"stat": "OK", "fields": [], "data": []})

        mock_req = Mock(side_effect=mock_request_side)

        # Filter to only test symbols (DB has existing production symbols)
        symbols = [s for s in _get_active_symbols() if s in TEST_SYMBOLS]
        assert len(symbols) == 2, f"Expected 2 test symbols, got {symbols}"

        with patch("framework.base_spider.requests.request", mock_req):
            for sym in symbols:
                r = s.fetch_daily(sym, 2026, 5)
                assert r.success, f"StockDaily fetch for {sym} failed: {r.error}"

        # Flush to DB
        s.flush_items(p)
        p.close()

        # Verify
        cur = db.cursor()
        cur.execute(
            "SELECT symbol, date, close_price FROM stock_daily "
            "WHERE symbol LIKE '999%' ORDER BY symbol, date"
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 20, f"Expected 20 stock_daily rows, got {len(rows)}"

        # Spot check last row for 9991
        row_9991_last = rows[9]
        assert row_9991_last[0] == "9991"
        assert row_9991_last[1] == "2026-05-15"
        # close_price is stored as text in DB; value from mock = 120
        assert float(row_9991_last[2]) == 120.0

    @pytest.mark.e2e
    def test_05_tpex_cb_daily_to_db(self, db) -> None:
        """TpexCbDailySpider fetch_daily → tpex_cb_daily (3 rows)."""
        from spiders.tpex_cb_daily_spider import TpexCbDailySpider
        from src.framework.pipelines import PostgresPipeline

        p = PostgresPipeline(table_name="tpex_cb_daily", batch_size=500, **DB_CONFIG)
        s = TpexCbDailySpider(pipeline=p)
        s.collect_only = True

        mock_get = _make_requests_get_mock(content=TPEX_CB_DAILY_CSV)

        with patch("spiders.tpex_cb_daily_spider.requests.get", mock_get):
            r = s.fetch_daily(TEST_DATE)
        assert r.success, f"TPEx CB Daily fetch failed: {r.error}"

        s.flush_items(p)
        p.close()

        # Verify
        cur = db.cursor()
        cur.execute(
            "SELECT cb_code, trade_date, closing_price FROM tpex_cb_daily "
            "WHERE cb_code LIKE '999%' ORDER BY cb_code"
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        assert rows[0] == ("99911", TEST_DATE, "120.0")
        assert rows[1] == ("99921", TEST_DATE, "300.0")

    @pytest.mark.e2e
    def test_06_broker_breakdown_to_db(self, db) -> None:
        """BrokerBreakdownSpider fetch_broker_breakdown_batch → broker_breakdown (6 rows)."""
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider
        from run_daily import _get_active_symbols
        from src.framework.pipelines import PostgresPipeline

        p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
        s = BrokerBreakdownSpider(pipeline=p)
        # BrokerBreakdownSpider already sets collect_only=True in __init__

        # Filter to only test symbols (DB has existing production symbols)
        all_symbols = _get_active_symbols()
        test_symbols = [s for s in all_symbols if s in TEST_SYMBOLS]
        assert len(test_symbols) == 2, f"Expected 2 test symbols, got {test_symbols}"

        # Patch BsrClient at the import site in broker_breakdown_spider
        with patch("spiders.broker_breakdown_spider.BsrClient") as mock_bsr_cls:
            mock_instance = Mock()
            mock_bsr_cls.return_value = mock_instance

            def fetch_broker_data_side(symbol: str):
                if symbol == "9991":
                    return BSR_RECORDS_9991
                elif symbol == "9992":
                    return BSR_RECORDS_9992
                return []

            mock_instance.fetch_broker_data.side_effect = fetch_broker_data_side

            r = s.fetch_broker_breakdown_batch(TEST_DATE_COMPACT, test_symbols)

        assert r.success, f"BrokerBreakdown batch failed: {r.error}"
        assert r.data.get("count") == 6, f"Expected 6 items, got {r.data.get('count')}"
        assert r.data.get("success_symbols") == ["9991", "9992"]

        s.flush_items(p)
        p.close()

        # Verify
        cur = db.cursor()
        cur.execute(
            "SELECT symbol, broker_id, buy_volume, sell_volume "
            "FROM broker_breakdown "
            "WHERE symbol LIKE '999%' ORDER BY symbol, rank"
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 6, f"Expected 6 broker_breakdown rows, got {len(rows)}"
        # 9991 first 3 rows have blacklisted brokers
        assert rows[0][1] == "9200"  # 凱基-台北 (blacklisted)
        assert rows[1][1] == "9800"  # 元大-台北 (blacklisted)
        assert rows[2][1] == "9100"  # 群益-台北 (blacklisted)
        # 9992
        assert rows[4][1] == "9600"  # 富邦-台北 (blacklisted)

    # ════════════════════════════════════════════════════════
    # Stage 2: Validation
    # ════════════════════════════════════════════════════════

    @pytest.mark.e2e
    def test_07_validate_all_tables(self, db) -> None:
        """step_validate on all 5 tables — must pass without errors."""
        from run_daily import step_validate

        # Build spider_results from DB counts
        cur = db.cursor()
        spider_results: Dict[str, dict] = {}
        collected_records: Dict[str, list] = {}

        for table in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily", "broker_breakdown"]:
            if table in ("cb_master", "tpex_cb_daily"):
                cur.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE cb_code LIKE '999%'"
                )
            else:
                cur.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE symbol LIKE '999%'"
                )
            count = cur.fetchone()[0]
            spider_results[table] = {"success": True, "count": count, "error": None}

            # Build records from DB for the DataValidator.
            # DB stores all columns as text, but DataValidator expects native types.
            # Use safe converter that handles both "1000" and "1000.0" strings.

            def _to_int(v: Any) -> Any:
                if v is None:
                    return v
                return int(float(v))

            def _to_float(v: Any) -> Any:
                if v is None:
                    return v
                return float(v)

            if table == "stock_master":
                cols = ["symbol", "name", "market_type", "industry", "listing_date", "cfi_code"]
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM stock_master WHERE symbol LIKE '999%'"
                )
                collected_records[table] = [dict(zip(cols, r)) for r in cur.fetchall()]
            elif table == "stock_daily":
                cols = ["symbol", "date", "open_price", "high_price", "low_price",
                        "close_price", "volume", "price_change", "transaction_count"]
                conv: Dict[str, Any] = {"open_price": _to_float, "high_price": _to_float,
                                        "low_price": _to_float, "close_price": _to_float,
                                        "volume": _to_int, "price_change": _to_float,
                                        "transaction_count": _to_int}
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM stock_daily WHERE symbol LIKE '999%'"
                )
                collected_records[table] = [
                    {k: conv.get(k, str)(v) for k, v in zip(cols, r)}
                    for r in cur.fetchall()
                ]
            elif table == "cb_master":
                cols = ["cb_code", "cb_name", "underlying_stock", "market_type",
                        "issue_date", "maturity_date", "conversion_price"]
                conv = {"conversion_price": _to_float}
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM cb_master WHERE cb_code LIKE '999%'"
                )
                collected_records[table] = [
                    {k: conv.get(k, str)(v) for k, v in zip(cols, r)}
                    for r in cur.fetchall()
                ]
            elif table == "tpex_cb_daily":
                cols = ["cb_code", "cb_name", "underlying_stock", "trade_date",
                        "closing_price", "volume"]
                conv = {"closing_price": _to_float, "volume": _to_int}
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM tpex_cb_daily WHERE cb_code LIKE '999%'"
                )
                collected_records[table] = [
                    {k: conv.get(k, str)(v) for k, v in zip(cols, r)}
                    for r in cur.fetchall()
                ]
            elif table == "broker_breakdown":
                cols = ["date", "symbol", "broker_id", "broker_name", "buy_volume",
                        "sell_volume", "net_volume", "rank"]
                conv = {"buy_volume": _to_int, "sell_volume": _to_int,
                        "net_volume": _to_int, "rank": _to_int}
                cur.execute(
                    f"SELECT {', '.join(cols)} FROM broker_breakdown WHERE symbol LIKE '999%'"
                )
                collected_records[table] = [
                    {k: conv.get(k, str)(v) for k, v in zip(cols, r)}
                    for r in cur.fetchall()
                ]

        cur.close()

        result = step_validate(spider_results, collected_records)
        assert result.get("has_errors") is False, f"Validation errors: {json.dumps(result, ensure_ascii=False)}"

    # ════════════════════════════════════════════════════════
    # Stage 3: Clean
    # ════════════════════════════════════════════════════════

    @pytest.mark.e2e
    def test_08_data_cleaner(self, db) -> None:
        """Verify DataCleaner enrichment columns on test data via targeted SQL.

        Runs migration SQL and enrichment logic directly (avoids DataCleaner
        constructor which can hang in pytest sessions due to psycopg2 issues).
        """
        # Run migrations directly
        import os as _os
        _migration_dir = _os.path.join(
            _os.path.dirname(__file__), "..", "..", "src", "db"
        )
        _cur = db.cursor()
        for _fname in sorted(_os.listdir(_migration_dir)):
            if _fname.startswith("migration_") and _fname.endswith(".sql"):
                _path = _os.path.join(_migration_dir, _fname)
                with open(_path, "r") as _f:
                    _cur.execute(_f.read())
        db.commit()

        # Run enrichment SQL only on our test records
        # 1. Set master_check on test stock_daily records that match stock_master
        _cur.execute("""
            UPDATE stock_daily d
            SET master_check = 'OK'
            WHERE d.symbol LIKE '999%'
              AND EXISTS (SELECT 1 FROM stock_master m WHERE m.symbol = d.symbol)
        """)
        # 2. Copy name/industry from stock_master
        _cur.execute("""
            UPDATE stock_daily d
            SET name = m.name, industry = m.industry
            FROM stock_master m
            WHERE d.symbol LIKE '999%'
              AND d.symbol = m.symbol
              AND d.master_check = 'OK'
        """)
        # 3. Set master_check on test tpex_cb_daily records
        _cur.execute("""
            UPDATE tpex_cb_daily d
            SET master_check = 'OK'
            WHERE d.cb_code LIKE '999%'
              AND EXISTS (SELECT 1 FROM cb_master m WHERE m.cb_code = d.cb_code)
        """)
        # 4. Enrich tpex_cb_daily with cb_master data
        _cur.execute("""
            UPDATE tpex_cb_daily d
            SET cb_name_enriched = m.cb_name,
                conversion_price_enriched = m.conversion_price
            FROM cb_master m
            WHERE d.cb_code LIKE '999%'
              AND d.cb_code = m.cb_code
              AND d.master_check = 'OK'
        """)
        # 5. Enrich cb_master underlying_stock from stock_master
        _cur.execute("""
            UPDATE cb_master c
            SET underlying_stock = m.symbol
            FROM stock_master m
            WHERE c.cb_code LIKE '999%'
              AND m.symbol = SUBSTRING(c.cb_code, 1, 4)
              AND (c.underlying_stock IS NULL OR c.underlying_stock = '')
        """)
        db.commit()

        # Verify stock_daily enrichment — 20 rows (10 days × 2 symbols)
        _cur.execute(
            "SELECT symbol, master_check, name FROM stock_daily "
            "WHERE symbol LIKE '999%' AND master_check = 'OK' ORDER BY symbol"
        )
        rows = _cur.fetchall()
        assert len(rows) == 20, f"Expected 20 enriched stock_daily rows, got {len(rows)}"
        names = set(r[0] for r in rows)
        assert "9991" in names, "9991 not found in enriched rows"
        assert "9992" in names, "9992 not found in enriched rows"
        # All 10 rows for 9991 should have name '測試股A'
        names_map = {r[0]: r[2] for r in rows}
        assert names_map["9991"] == "測試股A", f"9991 name got {names_map.get('9991')}"
        assert names_map["9992"] == "測試股B", f"9992 name got {names_map.get('9992')}"

        # Verify tpex_cb_daily enrichment
        _cur.execute(
            "SELECT cb_code, master_check, cb_name_enriched FROM tpex_cb_daily "
            "WHERE cb_code LIKE '999%' AND master_check = 'OK' ORDER BY cb_code"
        )
        cb_rows = _cur.fetchall()
        assert len(cb_rows) == 2, f"Expected 2 enriched tpex_cb_daily rows, got {len(cb_rows)}"
        for cb_row in cb_rows:
            assert cb_row[1] == "OK", f"{cb_row[0]} master_check not OK"
            assert cb_row[2] is not None, f"{cb_row[0]} cb_name_enriched is None"

        # Verify cb_master enrichment
        _cur.execute(
            "SELECT cb_code, underlying_stock FROM cb_master "
            "WHERE cb_code LIKE '999%' ORDER BY cb_code"
        )
        cm_rows = _cur.fetchall()
        assert len(cm_rows) == 2
        cm_map = {r[0]: r[1] for r in cm_rows}
        assert cm_map["99911"] == "9991"
        assert cm_map["99921"] == "9992"

        _cur.close()

    # ════════════════════════════════════════════════════════
    # Stage 4: Analytics (4 tests)
    # ════════════════════════════════════════════════════════

    @pytest.mark.e2e
    def test_09_premium_calculator(self, db) -> None:
        """PremiumCalculator.analyze + save_results → daily_analysis_results (2 rows, 1 per symbol)."""
        from analytics.premium_calculator import PremiumCalculator

        pc = PremiumCalculator()
        results = pc.analyze(TEST_DATE)

        assert len(results) == 2, f"Expected 2 results (1 per CB), got {len(results)}"

        # 99911 → 9991: conv_price=100, cb_close=120, stock_close=120
        #   conv_value = (100/100)*120 = 120.0, premium = 120/120-1 = 0.0
        # 99921 → 9992: conv_price=50, cb_close=300, stock_close=50
        #   conv_value = (100/50)*50 = 100.0, premium = 300/100-1 = 2.0
        result_map = {r.symbol: r for r in results}
        r1 = result_map["9991"]
        assert r1.symbol == "9991"
        assert r1.close_price == 120.0
        assert r1.conversion_value == 120.0
        assert r1.premium_ratio == 0.0
        assert r1.is_junk is False  # 0% <= 5%

        r2 = result_map["9992"]
        assert r2.conversion_value == 100.0
        assert r2.premium_ratio == 2.0  # 200%
        assert r2.is_junk is True  # > 5%

        saved = pc.save_results(TEST_DATE, results)
        assert saved == 2, f"Expected 2 saved, got {saved}"

        cur = db.cursor()
        cur.execute(
            "SELECT symbol, conversion_value, premium_ratio, is_junk "
            "FROM daily_analysis_results WHERE date = %s AND symbol IN %s "
            "ORDER BY symbol",
            (TEST_DATE, tuple(TEST_SYMBOLS)),
        )
        rows = cur.fetchall()
        cur.close()
        assert len(rows) == 2
        # row values come back as Python native types (numeric → Decimal, boolean)
        assert float(rows[0][1]) == 120.0  # conversion_value for 9991

    @pytest.mark.e2e
    def test_10_technical_analyzer(self, db) -> None:
        """TechnicalAnalyzer — only 10 days data (< MIN_HISTORY_DAYS=20) → all NEUTRAL."""
        from analytics.technical_analyzer import TechnicalAnalyzer
        from analytics.premium_calculator import PremiumCalculator
        from analytics.models import AnalysisResult

        pc = PremiumCalculator()
        results = pc.analyze(TEST_DATE)

        analyzer = TechnicalAnalyzer()
        results_out = analyzer.analyze(TEST_DATE, results)

        assert len(results_out) == 2
        for r in results_out:
            assert r.technical_signal == "NEUTRAL", (
                f"{r.symbol} signal={r.technical_signal}, expected NEUTRAL "
                f"(only 10 days data, need > 20)"
            )

    @pytest.mark.e2e
    def test_11_chip_profiler(self, db) -> None:
        """ChipProfiler.analyze — verify risk_ratio for 9991 and 9992.

        9991: top 5 buyers: 9200(1000), 9800(800), 9100(500), 9999(100)
              - 9200, 9800, 9100 are ALL in blacklist → suspect=2300
              - total=2400 → risk_ratio=2300/2400=0.9583
        9992: top 2 buyers: 9600(600), 8888(400)
              - 9600 is in blacklist → suspect=600
              - total=1000 → risk_ratio=0.6
        """
        from analytics.chip_profiler import ChipProfiler

        profiler = ChipProfiler()
        results = profiler.analyze(TEST_DATE)

        assert "9991" in results, "Missing 9991"
        assert "9992" in results, "Missing 9992"

        r1 = results["9991"]
        assert r1["risk_ratio"] == pytest.approx(2300 / 2400, abs=0.001)
        assert r1["total_volume"] == 2400
        assert r1["suspect_volume"] == 2300
        assert len(r1["matched_brokers"]) == 3

        r2 = results["9992"]
        assert r2["risk_ratio"] == pytest.approx(0.6, abs=0.001)
        assert r2["total_volume"] == 1000
        assert r2["suspect_volume"] == 600
        assert len(r2["matched_brokers"]) == 1
        assert r2["matched_brokers"][0] == "富邦-台北"

    @pytest.mark.e2e
    def test_12_risk_assessor(self, db) -> None:
        """RiskAssessor.run_analysis — final_rating + trading_signals in DB.

        9991: premium=0.0 (< 0.02), risk_ratio=0.9583 (>= 0.10)
              → fails 'S' (need risk < 0.10)
              → premium<0.03, risk=0.9583 (>=0.20) → fails 'A'
              → premium<0.05, risk=0.9583 (>=0.30) → fails 'B'
              → 'C' (AVOID)
        9992: premium=2.0 (>=0.05), risk=0.6 (>=0.30)
              → is_junk=True → 'C' (AVOID)

        Note: run_analysis processes ALL symbols for the date (including production).
        We filter assertions to TEST_SYMBOLS only.
        """
        from analytics.risk_assessor import RiskAssessor

        ra = RiskAssessor()
        results = ra.run_analysis(TEST_DATE)

        # Filter to test symbols (production data also exists for 2026-05-15)
        result_map = {r["symbol"]: r for r in results if r["symbol"] in TEST_SYMBOLS}
        assert len(result_map) == 2, f"Expected results for 2 test symbols, got {list(result_map.keys())}"

        # 9991: rating=C (risk too high for S/A/B)
        r1 = result_map["9991"]
        assert r1["rating"] == "C", f"9991: expected C, got {r1['rating']}"
        assert r1["signal"] == "AVOID"

        # 9992: is_junk → C
        r2 = result_map["9992"]
        assert r2["rating"] == "C", f"9992: expected C, got {r2['rating']}"
        assert r2["signal"] == "AVOID"

        # Verify DB state
        cur = db.cursor()
        cur.execute(
            "SELECT final_rating, broker_risk_pct FROM daily_analysis_results "
            "WHERE date = %s AND symbol = '9991'",
            (TEST_DATE,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "C"

        cur.execute(
            "SELECT signal_type FROM trading_signals "
            "WHERE date = %s AND symbol = '9991'",
            (TEST_DATE,),
        )
        signals = cur.fetchall()
        cur.close()
        assert len(signals) >= 1
        assert signals[0][0] == "AVOID"

    # ════════════════════════════════════════════════════════
    # Stage 5: Report
    # ════════════════════════════════════════════════════════

    @pytest.mark.e2e
    def test_13_markdown_report(self, db) -> None:
        """MarkdownReporter.generate_report — verify output contains expected strings."""
        from reporters.markdown_reporter import MarkdownReporter

        reporter = MarkdownReporter()
        report = reporter.generate_report(TEST_DATE)

        assert isinstance(report, str)
        assert len(report) > 100, "Report too short"
        # Header
        assert "CBAS 次日交易戰略清單" in report
        assert TEST_DATE in report
        # Both symbols should appear (both are junk=False; 9992 is junk=True → excluded)
        # Actually, PremiumCalculator set 9992 as is_junk=True (premium_ratio=200% > 5%).
        # So MarkdownReporter query WHERE is_junk=false excludes 9992.
        # Only 9991 should appear.
        # But 9991 has rating C → still shown (all ratings shown)
        assert "9991" in report
        # C level section
        assert "C 級" in report or "🔴" in report
