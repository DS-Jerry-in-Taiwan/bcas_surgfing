"""
RiskAssessor 單元測試

測試策略:
  - assess(): 四個評級 + 邊界條件 (使用「小於」比較)
  - generate_signal(): 對應信號 + 未知評級預設值
  - run_analysis(): 透過 mock psycopg2 驗證 DB 讀寫流程
  - _confidence(): 信心度對應
"""

from unittest.mock import MagicMock, patch

import pytest

from src.analytics.risk_assessor import RiskAssessor, _confidence
from src.analytics.rules.risk_rules import RATING_THRESHOLDS, SIGNAL_MAP


class TestRiskAssessorAssess:
    """RiskAssessor.assess() 評級測試"""

    def test_assess_S(self):
        """S: 溢價率 < 2% 且 風險 < 10%"""
        assert RiskAssessor.assess(0.01, 0.05) == "S"

    def test_assess_A(self):
        """A: 溢價率 < 3% 且 風險 < 20% (但不符合 S)"""
        assert RiskAssessor.assess(0.025, 0.15) == "A"

    def test_assess_B(self):
        """B: 溢價率 < 5% 且 風險 < 30% (但不符合 S/A)"""
        assert RiskAssessor.assess(0.04, 0.25) == "B"

    def test_assess_C_premium(self):
        """C: 溢價率 >= 5%"""
        assert RiskAssessor.assess(0.06, 0.05) == "C"

    def test_assess_C_risk(self):
        """C: 風險 >= 30%"""
        assert RiskAssessor.assess(0.01, 0.35) == "C"

    def test_assess_C_both_high(self):
        """C: 溢價率與風險都超標"""
        assert RiskAssessor.assess(0.06, 0.35) == "C"

    def test_assess_zero_values(self):
        """零值：溢價率 0% 且風險 0% → S"""
        assert RiskAssessor.assess(0.0, 0.0) == "S"

    def test_assess_negative_premium(self):
        """負溢價率 (折價) → 可能為 S"""
        assert RiskAssessor.assess(-0.01, 0.05) == "S"

    # ─── 邊界測試 ───────────────────────────────────────

    def test_assess_boundary_S_pass(self):
        """S 邊界內: 0.0199 < 0.02, 0.099 < 0.10 → S"""
        assert RiskAssessor.assess(0.0199, 0.099) == "S"

    def test_assess_boundary_S_fail_premium(self):
        """S 邊界: premium = 0.02 (相等, 不算 <) → 退化為 A"""
        assert RiskAssessor.assess(0.02, 0.05) == "A"

    def test_assess_boundary_S_fail_risk(self):
        """S 邊界: risk = 0.10 (相等, 不算 <) → 退化為 A"""
        assert RiskAssessor.assess(0.01, 0.10) == "A"

    def test_assess_boundary_A_fail_premium(self):
        """A 邊界: premium = 0.03 (相等) → 退化為 B"""
        assert RiskAssessor.assess(0.03, 0.10) == "B"

    def test_assess_boundary_A_fail_risk(self):
        """A 邊界: risk = 0.20 (相等) → 退化為 B"""
        assert RiskAssessor.assess(0.02, 0.20) == "B"

    def test_assess_boundary_B_fail_premium(self):
        """B 邊界: premium = 0.05 (相等) → C"""
        assert RiskAssessor.assess(0.05, 0.20) == "C"

    def test_assess_boundary_B_fail_risk(self):
        """B 邊界: risk = 0.30 (相等) → C"""
        assert RiskAssessor.assess(0.04, 0.30) == "C"


class TestRiskAssessorGenerateSignal:
    """RiskAssessor.generate_signal() 測試"""

    def test_signal_S(self):
        """S → BUY"""
        assert RiskAssessor.generate_signal("S") == "BUY"

    def test_signal_A(self):
        """A → BUY"""
        assert RiskAssessor.generate_signal("A") == "BUY"

    def test_signal_B(self):
        """B → HOLD"""
        assert RiskAssessor.generate_signal("B") == "HOLD"

    def test_signal_C(self):
        """C → AVOID"""
        assert RiskAssessor.generate_signal("C") == "AVOID"

    def test_signal_unknown(self):
        """未知評級 → HOLD (預設值)"""
        assert RiskAssessor.generate_signal("X") == "HOLD"

    def test_signal_empty_string(self):
        """空字串 → HOLD"""
        assert RiskAssessor.generate_signal("") == "HOLD"

    def test_signal_lowercase(self):
        """小寫評級 → HOLD (因 SIGNAL_MAP 用大寫鍵)"""
        assert RiskAssessor.generate_signal("s") == "HOLD"


class TestConfidence:
    """_confidence() 信心度測試"""

    def test_confidence_S(self):
        assert _confidence("S") == 0.9

    def test_confidence_A(self):
        assert _confidence("A") == 0.7

    def test_confidence_B(self):
        assert _confidence("B") == 0.5

    def test_confidence_C(self):
        assert _confidence("C") == 0.3

    def test_confidence_unknown(self):
        assert _confidence("X") == 0.5


class TestThresholdConstants:
    """RATING_THRESHOLDS 常數正確性驗證"""

    def test_S_thresholds(self):
        assert RATING_THRESHOLDS["S"]["max_premium"] == 0.02
        assert RATING_THRESHOLDS["S"]["max_risk"] == 0.10

    def test_A_thresholds(self):
        assert RATING_THRESHOLDS["A"]["max_premium"] == 0.03
        assert RATING_THRESHOLDS["A"]["max_risk"] == 0.20

    def test_B_thresholds(self):
        assert RATING_THRESHOLDS["B"]["max_premium"] == 0.05
        assert RATING_THRESHOLDS["B"]["max_risk"] == 0.30


class TestSignalMapConstants:
    """SIGNAL_MAP 常數正確性驗證"""

    def test_S_signal(self):
        assert SIGNAL_MAP["S"] == "BUY"

    def test_A_signal(self):
        assert SIGNAL_MAP["A"] == "BUY"

    def test_B_signal(self):
        assert SIGNAL_MAP["B"] == "HOLD"

    def test_C_signal(self):
        assert SIGNAL_MAP["C"] == "AVOID"


class TestRunAnalysis:
    """RiskAssessor.run_analysis() 測試 (mock DB)"""

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_run_analysis_normal(self, mock_chip_profiler, mock_psycopg2):
        """正常執行流程"""
        # Mock DB connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock daily_analysis_results query
        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, False),   # symbol, premium_ratio, is_junk
            ("2303", 0.04, False),   # B級
            ("2317", 0.06, False),   # C級 (溢價率超標)
        ]

        # Mock ChipProfiler
        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.05, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 50},
            "2303": {"risk_ratio": 0.25, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 250},
            "2317": {"risk_ratio": 0.02, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 20},
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-11")

        # Verify results
        assert len(results) == 3

        # 2330: premium=0.01, risk=0.05 → S
        r1 = results[0]
        assert r1["symbol"] == "2330"
        assert r1["rating"] == "S"
        assert r1["signal"] == "BUY"
        assert r1["premium_ratio"] == 0.01
        assert r1["risk_ratio"] == 0.05

        # 2303: premium=0.04, risk=0.25 → B
        r2 = results[1]
        assert r2["symbol"] == "2303"
        assert r2["rating"] == "B"
        assert r2["signal"] == "HOLD"

        # 2317: premium=0.06 → C
        r3 = results[2]
        assert r3["symbol"] == "2317"
        assert r3["rating"] == "C"
        assert r3["signal"] == "AVOID"

        # Verify DB writes
        # 3 UPDATE calls + 3 INSERT calls = 6 execute calls
        # But the first execute was the SELECT, so 7 total
        assert mock_cursor.execute.call_count == 7
        assert mock_conn.commit.called
        assert mock_cursor.close.called
        assert mock_conn.close.called

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_run_analysis_with_junk(self, mock_chip_profiler, mock_psycopg2):
        """廢棄標的直接給 C 評級"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # is_junk = True → should get C regardless
        mock_cursor.fetchall.return_value = [
            ("2330", 0.01, True),   # junk
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.05, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 50},
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-11")

        assert len(results) == 1
        assert results[0]["symbol"] == "2330"
        assert results[0]["rating"] == "C"
        assert results[0]["signal"] == "AVOID"
        # Junk items use risk_ratio = 0.0
        assert results[0]["risk_ratio"] == 0.0

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_run_analysis_empty(self, mock_chip_profiler, mock_psycopg2):
        """當日無分析資料"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = []

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {}

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-11")

        assert len(results) == 0
        # Only the SELECT was executed
        assert mock_conn.commit.called  # commit called even with 0 rows

    @patch("src.analytics.risk_assessor.psycopg2")
    @patch("src.analytics.risk_assessor.ChipProfiler")
    def test_run_analysis_null_premium(self, mock_chip_profiler, mock_psycopg2):
        """premium_ratio 為 NULL 時使用 999.0 作為預設值"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("2330", None, False),  # NULL premium_ratio
        ]

        mock_profiler_instance = MagicMock()
        mock_chip_profiler.return_value = mock_profiler_instance
        mock_profiler_instance.analyze.return_value = {
            "2330": {"risk_ratio": 0.05, "matched_brokers": [], "total_volume": 1000, "suspect_volume": 50},
        }

        ra = RiskAssessor()
        results = ra.run_analysis("2026-05-11")

        assert len(results) == 1
        # premium=999.0, risk=0.05
        # S: 999.0 < 0.02? No
        # A: 999.0 < 0.03? No
        # B: 999.0 < 0.05? No
        # → C
        assert results[0]["rating"] == "C"
        assert results[0]["premium_ratio"] == 999.0
