"""
ChipProfiler 單元測試

測試策略:
  - load_blacklist: 透過 mock_open 模擬 JSON 檔案
  - is_suspicious / get_risk_level: 直接設定 blacklist 字典測試
  - analyze: 透過 mock psycopg2 驗證 DB 查詢邏輯
"""

import json
from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.analytics.chip_profiler import ChipProfiler


class TestChipProfiler:
    """ChipProfiler 單元測試"""

    # ─── load_blacklist ─────────────────────────────────────

    @patch("src.analytics.chip_profiler.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps([
        {"broker_id": "9200", "broker_name": "凱基-台北", "risk_level": "HIGH"},
        {"broker_id": "9800", "broker_name": "元大-台北", "risk_level": "HIGH"},
    ]))
    def test_load_blacklist_normal(self, mock_file, mock_exists):
        """正常載入黑名單 JSON"""
        mock_exists.return_value = True
        profiler = ChipProfiler(blacklist_path="/fake/path.json")
        assert len(profiler.blacklist) == 2
        assert "9200" in profiler.blacklist
        assert "9800" in profiler.blacklist
        assert profiler.blacklist["9200"]["broker_name"] == "凱基-台北"

    @patch("src.analytics.chip_profiler.os.path.exists")
    def test_load_blacklist_file_not_found(self, mock_exists):
        """黑名單檔案不存在時不拋錯，回傳空字典"""
        mock_exists.return_value = False
        profiler = ChipProfiler(blacklist_path="/nonexistent/path.json")
        assert len(profiler.blacklist) == 0
        assert profiler.blacklist == {}

    @patch("src.analytics.chip_profiler.os.path.exists")
    def test_load_blacklist_empty_file(self, mock_exists):
        """空 JSON 陣列"""
        mock_exists.return_value = True
        with patch("builtins.open", new_callable=mock_open, read_data="[]"):
            profiler = ChipProfiler(blacklist_path="/fake/path.json")
            assert len(profiler.blacklist) == 0

    @patch("src.analytics.chip_profiler.os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps([
        {"broker_id": "9200", "broker_name": "凱基-台北", "risk_level": "HIGH"},
        {"broker_id": "9100", "broker_name": "群益-台北", "risk_level": "HIGH"},
        {"broker_id": "9600", "broker_name": "富邦-台北", "risk_level": "MEDIUM"},
    ]))
    def test_load_blacklist_multiple_levels(self, mock_file, mock_exists):
        """多筆黑名單包含不同風險等級"""
        mock_exists.return_value = True
        profiler = ChipProfiler(blacklist_path="/fake/path.json")
        assert len(profiler.blacklist) == 3
        assert profiler.blacklist["9200"]["risk_level"] == "HIGH"
        assert profiler.blacklist["9600"]["risk_level"] == "MEDIUM"

    # ─── is_suspicious ─────────────────────────────────────

    def test_is_suspicious_true(self):
        """已知黑名單券商回傳 True"""
        profiler = ChipProfiler()
        profiler.blacklist = {"9200": {"risk_level": "HIGH"}}
        assert profiler.is_suspicious("9200") is True

    def test_is_suspicious_false(self):
        """非黑名單券商回傳 False"""
        profiler = ChipProfiler()
        profiler.blacklist = {"9200": {"risk_level": "HIGH"}}
        assert profiler.is_suspicious("9999") is False

    def test_is_suspicious_empty_blacklist(self):
        """黑名單為空時全部回傳 False"""
        profiler = ChipProfiler()
        profiler.blacklist = {}
        assert profiler.is_suspicious("9200") is False
        assert profiler.is_suspicious("9999") is False

    # ─── get_risk_level ───────────────────────────────────

    def test_get_risk_level_known(self):
        """已知黑名單券商回傳正確等級"""
        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"risk_level": "HIGH", "broker_name": "凱基-台北"}
        }
        assert profiler.get_risk_level("9200") == "HIGH"

    def test_get_risk_level_unknown(self):
        """非黑名單券商回傳 None"""
        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"risk_level": "HIGH", "broker_name": "凱基-台北"}
        }
        assert profiler.get_risk_level("9999") is None

    def test_get_risk_level_empty(self):
        """黑名單為空時回傳 None"""
        profiler = ChipProfiler()
        profiler.blacklist = {}
        assert profiler.get_risk_level("9200") is None

    # ─── analyze (mock DB) ─────────────────────────────────

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_with_data(self, mock_psycopg2):
        """正常分析流程：有分點資料且部分匹配黑名單"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock broker_breakdown rows:
        # (symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume)
        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 1000, 100, 900),
            ("2330", "9800", "元大-台北", 800, 200, 600),
            ("2330", "9100", "群益-台北", 500, 300, 200),
            ("2330", "9600", "富邦-台北", 300, 100, 200),
            ("2330", "9300", "統一-台北", 200, 50, 150),
            ("2330", "9999", "其他券商", 100, 80, 20),
        ]

        profiler = ChipProfiler()
        # Set a small blacklist for testing
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
            "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-11")

        # Should analyze symbol 2330
        assert "2330" in results
        info = results["2330"]

        # Top 5 buyers by volume: 9200(1000), 9800(800), 9100(500), 9600(300), 9300(200)
        # Matched: 9200, 9800 (both in blacklist)
        # suspect_volume = 1000 + 800 = 1800
        # total_volume = 1000 + 800 + 500 + 300 + 200 + 100 = 2900
        # risk_ratio = 1800 / 2900 ≈ 0.6207
        assert info["suspect_volume"] == 1800
        assert info["total_volume"] == 2900
        assert info["risk_ratio"] == pytest.approx(0.6207, rel=1e-3)
        assert "凱基-台北" in info["matched_brokers"]
        assert "元大-台北" in info["matched_brokers"]
        assert len(info["matched_brokers"]) == 2

        # Verify DB connection
        mock_cursor.execute.assert_called_once()
        assert mock_psycopg2.connect.called
        assert mock_cursor.close.called
        assert mock_conn.close.called

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_no_matches(self, mock_psycopg2):
        """沒有分點匹配黑名單"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", "1111", "一般券商A", 500, 100, 400),
            ("2330", "2222", "一般券商B", 400, 200, 200),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-11")

        assert "2330" in results
        info = results["2330"]
        assert info["risk_ratio"] == 0.0
        assert info["matched_brokers"] == []
        assert info["suspect_volume"] == 0

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_all_matched(self, mock_psycopg2):
        """所有前五大買超都匹配黑名單"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 1000, 100, 900),
            ("2330", "9800", "元大-台北", 800, 200, 600),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
            "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-11")

        info = results["2330"]
        assert info["risk_ratio"] == 1.0  # 100%
        assert info["suspect_volume"] == 1800
        assert info["total_volume"] == 1800

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_empty_data(self, mock_psycopg2):
        """當日無分點資料"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        profiler = ChipProfiler()
        results = profiler.analyze("2026-05-11")

        assert results == {}

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_multiple_symbols(self, mock_psycopg2):
        """多檔股票分析"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 1000, 100, 900),
            ("2330", "9999", "其他券商", 500, 200, 300),
            ("2303", "9800", "元大-台北", 800, 300, 500),
            ("2303", "8888", "一般券商", 600, 100, 500),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
            "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-11")

        assert "2330" in results
        assert "2303" in results
        # 2330: 1000/1500 ≈ 0.6667
        assert results["2330"]["risk_ratio"] == pytest.approx(0.6667, rel=1e-3)
        # 2303: 800/1400 ≈ 0.5714
        assert results["2303"]["risk_ratio"] == pytest.approx(0.5714, rel=1e-3)

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_analyze_zero_volume(self, mock_psycopg2):
        """所有分點買量為 0 時不拋錯"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 0, 0, 0),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-11")

        assert "2330" in results
        info = results["2330"]
        assert info["risk_ratio"] == 0.0
        assert info["total_volume"] == 0
        assert info["suspect_volume"] == 0
