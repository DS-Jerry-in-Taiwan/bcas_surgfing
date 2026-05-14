"""
Stage 4 整合測試：驗證 S/A/B/C 評級鏈完整性

測試目標:
  1. ChipProfiler 可正確讀取 BSR 格式的 broker_breakdown 資料
  2. RiskAssessor.run_analysis() 正確接收 ChipProfiler 結果
  3. broker_risk_pct 正確寫入 daily_analysis_results
  4. 完整評級鏈 S→A→B→C 通過 premium + risk 組合
  5. BSR 無資料時不拋錯且 risk_ratio=0
  6. BSR spider 寫入欄位與 ChipProfiler 讀取欄位相容
  7. EODPipeline._run_risk() 可正常呼叫 RiskAssessor

測試策略: 全部使用 @patch mock DB 連線
"""

from unittest.mock import MagicMock, patch

import pytest

from src.analytics.chip_profiler import ChipProfiler
from src.analytics.risk_assessor import RiskAssessor


class TestStage4ChipProfilerReadsBSR:
    """Stage 4.1: ChipProfiler 讀取 BSR 資料"""

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_chip_profiler_reads_bsr_data(self, mock_psycopg2):
        """模擬 broker_breakdown 表含 BSR 格式資料，確認 ChipProfiler 正確解析

        BSR spider 寫入 broker_breakdown 的欄位:
          symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume, rank
        ChipProfiler 讀取的欄位:
          symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # BSR 格式資料（模擬 BSR spider 寫入的內容）
        # (symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume)
        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 1000, 100, 900),
            ("2330", "9800", "元大-台北", 800, 200, 600),
            ("2330", "9999", "其他券商", 500, 300, 200),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
            "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-14")

        assert "2330" in results
        info = results["2330"]

        # Top 5 buyers by volume: 9200(1000), 9800(800), 9999(500)
        # Matched in blacklist: 9200, 9800
        # suspect_volume = 1000 + 800 = 1800
        # total_volume = 1000 + 800 + 500 = 2300
        # risk_ratio = 1800 / 2300 ≈ 0.7826
        assert info["suspect_volume"] == 1800
        assert info["total_volume"] == 2300
        assert info["risk_ratio"] == pytest.approx(0.7826, rel=1e-3)
        assert "凱基-台北" in info["matched_brokers"]
        assert "元大-台北" in info["matched_brokers"]
        assert len(info["matched_brokers"]) == 2

        # DB 資源正確釋放
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_chip_profiler_reads_bsr_data_multiple_symbols(self, mock_psycopg2):
        """多檔 BSR 資料時仍可正確分組計算"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", "9200", "凱基-台北", 1000, 100, 900),
            ("2330", "9999", "其他券商", 500, 200, 300),
            ("2303", "9800", "元大-台北", 800, 300, 500),
        ]

        profiler = ChipProfiler()
        profiler.blacklist = {
            "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
            "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
        }

        results = profiler.analyze("2026-05-14")

        assert "2330" in results
        assert "2303" in results
        # 2330: suspect=1000, total=1500 → 0.6667
        assert results["2330"]["risk_ratio"] == pytest.approx(0.6667, rel=1e-3)
        # 2303: suspect=800, total=800 → 1.0
        assert results["2303"]["risk_ratio"] == 1.0


class TestStage4RiskAssessorReceivesChipResults:
    """Stage 4.2: RiskAssessor 接收 ChipProfiler 結果"""

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_risk_assessor_receives_chip_results(self, mock_chip_profiler, mock_psycopg2):
        """驗證 RiskAssessor.run_analysis() 內正確調用 ChipProfiler.analyze() 並使用其結果"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 設定 daily_analysis_results 資料
        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),  # premium=1%, low risk
        ]

        # 設定 ChipProfiler 回傳值（高風險 35%）
        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {
                "risk_ratio": 0.35,
                "matched_brokers": ["凱基-台北"],
                "total_volume": 10000,
                "suspect_volume": 3500,
            }
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-14")

        # 驗證 ChipProfiler 被正確呼叫
        mock_chip_profiler.assert_called_once()
        mock_profiler_instance.analyze.assert_called_once_with("2026-05-14")

        # 2330: premium=0.01, risk=0.35
        # S: 0.01<0.02 ✓, 0.35<0.10 ✗
        # A: 0.01<0.03 ✓, 0.35<0.20 ✗
        # B: 0.01<0.05 ✓, 0.35<0.30 ✗
        # → C
        assert len(results) == 1
        assert results[0]["symbol"] == "2330"
        assert results[0]["rating"] == "C"
        assert results[0]["risk_ratio"] == 0.35
        assert results[0]["signal"] == "AVOID"

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_risk_assessor_uses_chip_risk_ratio_in_rating(self, mock_chip_profiler, mock_psycopg2):
        """確認 risk_ratio 值直接影響評級結果（非僅佔位）"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 相同 premium 但不同 risk_ratio 應得到不同評級
        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        # risk_ratio = 5% → S 評級
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.05, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 50},
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-14")

        assert results[0]["rating"] == "S"
        assert results[0]["risk_ratio"] == 0.05


class TestStage4BrokerRiskPctWritten:
    """Stage 4.3: broker_risk_pct 寫入 DB"""

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_broker_risk_pct_written_to_db(self, mock_chip_profiler, mock_psycopg2):
        """直接驗證 daily_analysis_results 的 UPDATE SQL 語句參數正確

        UPDATE 設定:
          final_rating = %s       → "A"
          risk_score = %s         → risk_ratio * 100 = 15.0
          broker_risk_pct = %s    → risk_ratio * 100 = 15.0
          WHERE date=%s, symbol=%s
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", 0.025, False),  # premium=2.5% → A if risk<20%
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {
                "risk_ratio": 0.15,
                "matched_brokers": ["凱基-台北"],
                "total_volume": 10000,
                "suspect_volume": 1500,
            }
        }

        ra = RiskAssessor()
        ra.run_analysis("2026-05-14")

        # 找到 UPDATE 呼叫
        update_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "UPDATE daily_analysis_results" in str(c.args[0])
        ]
        assert len(update_calls) == 1

        # 提取參數
        sql, params = update_calls[0].args
        # params: (rating, risk_score, broker_risk_pct, date, symbol)
        assert params[0] == "A"         # final_rating
        assert params[1] == 15.0         # risk_score = risk_ratio * 100
        assert params[2] == 15.0         # broker_risk_pct = risk_ratio * 100
        assert params[3] == "2026-05-14"
        assert params[4] == "2330"

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_broker_risk_pct_zero_when_no_risk(self, mock_chip_profiler, mock_psycopg2):
        """broker_risk_pct 在無風險時為 0.0"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.0, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 0},
        }

        ra = RiskAssessor()
        ra.run_analysis("2026-05-14")

        update_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "UPDATE daily_analysis_results" in str(c.args[0])
        ]
        assert len(update_calls) == 1
        _sql, params = update_calls[0].args
        assert params[0] == "S"   # rating (premium=1%, risk=0%)
        assert params[1] == 0.0   # risk_score = 0
        assert params[2] == 0.0   # broker_risk_pct = 0


class TestStage4FullRatingChain:
    """Stage 4.4: 完整評級鏈 S/A/B/C"""

    @pytest.mark.parametrize("premium,risk,expected_rating,expected_signal", [
        (0.01, 0.05, "S", "BUY"),     # S: premium<2%, risk<10%
        (0.025, 0.15, "A", "BUY"),     # A: premium<3%, risk<20% (不滿足S)
        (0.04, 0.25, "B", "HOLD"),     # B: premium<5%, risk<30% (不滿足S/A)
        (0.06, 0.35, "C", "AVOID"),    # C: premium≥5% OR risk≥30%
    ])
    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_full_rating_chain_s_to_c(
        self, mock_chip_profiler, mock_psycopg2,
        premium, risk, expected_rating, expected_signal,
    ):
        """測試所有評級透過完整的 premium + risk 鏈"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", premium, False),
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {
                "risk_ratio": risk,
                "matched_brokers": [],
                "total_volume": 1000,
                "suspect_volume": int(1000 * risk),
            },
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-14")

        assert len(results) == 1
        assert results[0]["rating"] == expected_rating
        assert results[0]["signal"] == expected_signal
        assert results[0]["premium_ratio"] == premium
        assert results[0]["risk_ratio"] == risk

        # 驗證 UPDATE 參數也正確
        update_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "UPDATE daily_analysis_results" in str(c.args[0])
        ]
        assert len(update_calls) == 1
        _sql, params = update_calls[0].args
        assert params[0] == expected_rating


class TestStage4BSRFallback:
    """Stage 4.5: BSR 無資料降級處理"""

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_bsr_fallback_on_empty_data(self, mock_chip_profiler, mock_psycopg2):
        """BSR 無資料時（ChipProfiler 回傳空字典），不拋錯且 risk_ratio=0

        降級路徑: chip_results = {} → chip_results.get("2330", {}) → {}
                  → chip_info.get("risk_ratio", 0.0) → 0.0
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),
        ]

        # ChipProfiler 回傳空字典（無任何 BSR 資料）
        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {}

        ra = RiskAssessor()
        # 不應拋出任何異常
        results = ra.run_analysis("2026-05-14")

        assert len(results) == 1
        assert results[0]["risk_ratio"] == 0.0
        # premium=1%, risk=0% → S
        assert results[0]["rating"] == "S"
        assert results[0]["signal"] == "BUY"

    @patch("src.analytics.chip_profiler.psycopg2")
    def test_chip_profiler_empty_data_no_error(self, mock_psycopg2):
        """ChipProfiler 本身在 broker_breakdown 無資料時回傳空字典不拋錯"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        profiler = ChipProfiler()
        results = profiler.analyze("2026-05-14")

        assert results == {}

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_bsr_fallback_partial_data(self, mock_chip_profiler, mock_psycopg2):
        """部分 symbol 無 BSR 資料時，該 symbol 使用預設 risk_ratio=0"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),   # 有 chip data
            ("2303", 0.02, False),   # 無 chip data
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.05, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 50},
            # 2303 不在 chip_results 中
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-14")

        assert len(results) == 2
        # 2330: premium=1%, risk=5% → S
        assert results[0]["symbol"] == "2330"
        assert results[0]["rating"] == "S"
        assert results[0]["risk_ratio"] == 0.05

        # 2303: premium=2%, risk=0% (fallback)
        # S: 0.02 < 0.02? NO (相等不給過) → 退化為 A
        assert results[1]["symbol"] == "2303"
        assert results[1]["rating"] == "A"
        assert results[1]["risk_ratio"] == 0.0


class TestStage4BSRDataFormat:
    """Stage 4.6: BSR 資料格式相容性"""

    def test_chip_profiler_sql_columns_match_schema(self):
        """ChipProfiler 的 SQL 查詢欄位與 broker_breakdown 表 schema 相容

        ChipProfiler 讀取: symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume
        broker_breakdown 表包含: date, symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume, rank
        """
        import inspect

        # 取得 ChipProfiler.analyze 原始碼
        source = inspect.getsource(ChipProfiler.analyze)

        # 確認查詢包含所有必要的 BSR 欄位
        assert "symbol" in source, "遺漏欄位: symbol"
        assert "broker_id" in source, "遺漏欄位: broker_id"
        assert "broker_name" in source, "遺漏欄位: broker_name"
        assert "buy_volume" in source, "遺漏欄位: buy_volume"
        assert "sell_volume" in source, "遺漏欄位: sell_volume"
        assert "net_volume" in source, "遺漏欄位: net_volume"

    def test_broker_breakdown_item_has_all_chip_profiler_fields(self):
        """BrokerBreakdownItem（BSR spider 寫入用）包含 ChipProfiler 所需所有欄位"""
        from src.framework.base_item import BrokerBreakdownItem

        # BrokerBreakdownItem 的所有欄位
        item_field_names = {
            f.name for f in BrokerBreakdownItem.__dataclass_fields__.values()
        }

        # ChipProfiler 需要的欄位
        required_fields = {
            "symbol", "broker_id", "broker_name",
            "buy_volume", "sell_volume", "net_volume",
        }
        assert required_fields.issubset(item_field_names), (
            f"BrokerBreakdownItem 缺少 ChipProfiler 所需欄位: "
            f"{required_fields - item_field_names}"
        )

    def test_broker_breakdown_table_columns(self):
        """broker_breakdown 表結構支援 BSR spider 寫入與 ChipProfiler 讀取"""
        import inspect
        from src.framework.base_item import BrokerBreakdownItem

        # BrokerBreakdownItem 的 __table_name__ 指向 broker_breakdown
        assert BrokerBreakdownItem.__table_name__ == "broker_breakdown"

        # BrokerBreakdownItem 包含 rank 欄位（BSR spider 寫入用）
        item_field_names = {
            f.name for f in BrokerBreakdownItem.__dataclass_fields__.values()
        }
        assert "rank" in item_field_names, "缺少 rank 欄位（BSR spider 寫入用）"

        # BrokerBreakdownItem 欄位總數 >= ChipProfiler 所需欄位數
        assert len(item_field_names) >= 6, (
            f"BrokerBreakdownItem 應至少有 6 個欄位, 現有 {len(item_field_names)}"
        )


class TestStage4EODPipeline:
    """Stage 4.7: EOD Pipeline Stage 3 整合測試

    _run_risk() 內部使用 from analytics.risk_assessor import RiskAssessor，
    因此需要確保 analytics.risk_assessor 模組路徑可用。
    透過將 src 加入 sys.path，並將 analytics.risk_assessor 模組指向
    src.analytics.risk_assessor，確保 mock 正確生效。
    """

    def _setup_analytics_module(self):
        """確保 analytics.risk_assessor 與 src.analytics.risk_assessor 指向同一模組"""
        import sys
        import os

        test_dir = os.path.dirname(__file__)
        src_path = os.path.abspath(os.path.join(test_dir, "../src"))
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # 先載入 src.analytics.risk_assessor
        import src.analytics.risk_assessor  # noqa: F401

        # 將 analytics.risk_assessor 指向同一個模組物件
        if (
            "analytics.risk_assessor" in sys.modules
            and sys.modules["analytics.risk_assessor"]
            is not sys.modules["src.analytics.risk_assessor"]
        ):
            # 若已存在不同物件，以 src 版本取代
            sys.modules["analytics.risk_assessor"] = sys.modules[
                "src.analytics.risk_assessor"
            ]
        elif "analytics.risk_assessor" not in sys.modules:
            sys.modules["analytics.risk_assessor"] = sys.modules[
                "src.analytics.risk_assessor"
            ]

    def test_eod_pipeline_stage3_calls_risk_assessor(self):
        """EOD Pipeline 的 _run_risk() 可正常呼叫 RiskAssessor.run_analysis()

        直接測試 RiskAssessor 實例化 + 呼叫，無需啟動完整 pipeline。
        """
        self._setup_analytics_module()

        with patch("src.analytics.risk_assessor.psycopg2") as mock_db:
            with patch("src.analytics.risk_assessor.ChipProfiler") as mock_chip:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_db.connect.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchall.return_value = [
                    ("2330", 0.01, False),
                ]

                mock_chip_instance = MagicMock()
                mock_chip.return_value = mock_chip_instance
                mock_chip_instance.analyze.return_value = {
                    "2330": {
                        "risk_ratio": 0.05,
                        "matched_brokers": [],
                        "total_volume": 1000,
                        "suspect_volume": 50,
                    },
                }

                from src.pipeline.eod_pipeline import EODPipeline

                pipeline = EODPipeline()
                pipeline._run_risk("2026-05-14")

                # 驗證 ChipProfiler 被正確呼叫（間接證明 RiskAssessor 被實例化與調用）
                mock_chip.assert_called_once()
                mock_chip_instance.analyze.assert_called_once_with("2026-05-14")
                # 驗證 DB 有 commit
                assert mock_conn.commit.called

    def test_eod_pipeline_stage3_handles_empty_results(self):
        """_run_risk() 在無結果時不拋錯"""
        self._setup_analytics_module()

        with patch("src.analytics.risk_assessor.psycopg2") as mock_db:
            with patch("src.analytics.risk_assessor.ChipProfiler") as mock_chip:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_db.connect.return_value = mock_conn
                mock_conn.cursor.return_value = mock_cursor
                mock_cursor.fetchall.return_value = []

                mock_chip_instance = MagicMock()
                mock_chip.return_value = mock_chip_instance
                mock_chip_instance.analyze.return_value = {}

                from src.pipeline.eod_pipeline import EODPipeline

                pipeline = EODPipeline()
                # 不應拋錯
                pipeline._run_risk("2026-05-14")

                mock_chip.assert_called_once()
                mock_chip_instance.analyze.assert_called_once_with("2026-05-14")
                assert mock_conn.commit.called
