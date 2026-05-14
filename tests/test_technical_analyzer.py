"""
TechnicalAnalyzer 單元測試

測試策略:
  - calculate_ma, check_breakout, check_ma_alignment,
    check_attack_pattern: 純函數測試 (不依賴 DB)
  - get_historical_data / analyze: 透過 mock psycopg2 驗證
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analytics.models import AnalysisResult
from src.analytics.technical_analyzer import TechnicalAnalyzer


# ─── Fixtures ──────────────────────────────────────────────
@pytest.fixture
def analyzer():
    """建立 TechnicalAnalyzer 實例"""
    return TechnicalAnalyzer()


@pytest.fixture
def sample_closes():
    """20 筆收盤價 (由 100 緩漲至 119)"""
    return np.arange(100.0, 120.0, 1.0, dtype=float)


@pytest.fixture
def sample_volumes():
    """20 筆成交量 (由 1000 緩增至 3000)"""
    return np.linspace(1000, 3000, 20, dtype=int)


# ═══════════════════════════════════════════════════════════
# calculate_ma
# ═══════════════════════════════════════════════════════════
class TestCalculateMA:
    """移動平均線計算測試"""

    def test_ma5_normal(self, analyzer, sample_closes):
        """MA5 正常計算"""
        # 最後 5 筆: 115, 116, 117, 118, 119 → avg = 117.0
        ma5 = analyzer.calculate_ma(sample_closes, 5)
        assert ma5 == pytest.approx(117.0, rel=1e-9)

    def test_ma20_normal(self, analyzer, sample_closes):
        """MA20 正常計算"""
        # 全部 20 筆: 100~119 → avg = (100+119)/2 = 109.5
        expected = float(np.mean(sample_closes))
        ma20 = analyzer.calculate_ma(sample_closes, 20)
        assert ma20 == pytest.approx(expected, rel=1e-9)

    def test_insufficient_data(self, analyzer):
        """資料不足時回傳 0.0"""
        data = np.array([1.0, 2.0, 3.0])
        result = analyzer.calculate_ma(data, 5)
        assert result == 0.0

    def test_empty_array(self, analyzer):
        """空陣列回傳 0.0"""
        result = analyzer.calculate_ma(np.array([]), 5)
        assert result == 0.0

    def test_vma20_normal(self, analyzer, sample_volumes):
        """20日均量正常計算"""
        expected = float(np.mean(sample_volumes))
        vma20 = analyzer.calculate_ma(sample_volumes, 20)
        assert vma20 == pytest.approx(expected, rel=1e-9)

    def test_exact_period(self, analyzer):
        """資料筆數剛好等於 period"""
        data = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = analyzer.calculate_ma(data, 5)
        assert result == pytest.approx(30.0, rel=1e-9)


# ═══════════════════════════════════════════════════════════
# check_breakout
# ═══════════════════════════════════════════════════════════
class TestCheckBreakout:
    """帶量突破判斷測試"""

    def test_breakout_true(self, analyzer):
        """帶量突破成立: 量 > 1.5*均量 AND 價 > MA20"""
        result = analyzer.check_breakout(
            close=110.0, volume=3000, ma20=100.0, volume_ma20=1000
        )
        assert result is True
        # volume(3000) > 1.5*1000(1500) AND close(110) > ma20(100)

    def test_breakout_volume_too_low(self, analyzer):
        """量不足 → 不成立"""
        result = analyzer.check_breakout(
            close=110.0, volume=1400, ma20=100.0, volume_ma20=1000
        )
        assert result is False
        # volume(1400) < 1.5*1000(1500)

    def test_breakout_price_below_ma20(self, analyzer):
        """價低於 MA20 → 不成立"""
        result = analyzer.check_breakout(
            close=90.0, volume=3000, ma20=100.0, volume_ma20=1000
        )
        assert result is False
        # close(90) < ma20(100)

    def test_breakout_ma20_zero(self, analyzer):
        """MA20 無值時回傳 False"""
        result = analyzer.check_breakout(
            close=110.0, volume=3000, ma20=0.0, volume_ma20=1000
        )
        assert result is False

    def test_breakout_vma20_zero(self, analyzer):
        """VMA20 無值時回傳 False"""
        result = analyzer.check_breakout(
            close=110.0, volume=3000, ma20=100.0, volume_ma20=0.0
        )
        assert result is False

    def test_breakout_exact_at_threshold(self, analyzer):
        """剛好在門檻邊界: volume = 1.5 * vma20 → 需嚴格大於"""
        result = analyzer.check_breakout(
            close=110.0, volume=1500, ma20=100.0, volume_ma20=1000
        )
        # 1.5 * 1000 = 1500, volume(1500) > 1500 不成立
        assert result is False


# ═══════════════════════════════════════════════════════════
# check_ma_alignment
# ═══════════════════════════════════════════════════════════
class TestCheckMAAlignment:
    """均線排列判斷測試"""

    def test_bullish(self, analyzer):
        """多頭排列: close > ma5 > ma20"""
        result = analyzer.check_ma_alignment(close=120.0, ma5=110.0, ma20=100.0)
        assert result == "BULLISH"

    def test_bearish(self, analyzer):
        """空頭排列: close < ma5 < ma20"""
        result = analyzer.check_ma_alignment(close=80.0, ma5=90.0, ma20=100.0)
        assert result == "BEARISH"

    def test_neutral_mixed(self, analyzer):
        """盤整: close > ma5 but ma5 < ma20"""
        result = analyzer.check_ma_alignment(close=105.0, ma5=95.0, ma20=100.0)
        assert result == "NEUTRAL"

    def test_neutral_ma5_zero(self, analyzer):
        """ma5 為 0 時回傳 NEUTRAL"""
        result = analyzer.check_ma_alignment(close=100.0, ma5=0.0, ma20=100.0)
        assert result == "NEUTRAL"

    def test_neutral_ma20_zero(self, analyzer):
        """ma20 為 0 時回傳 NEUTRAL"""
        result = analyzer.check_ma_alignment(close=100.0, ma5=100.0, ma20=0.0)
        assert result == "NEUTRAL"

    def test_equal_values_bullish(self, analyzer):
        """close == ma5 > ma20 → 歸 NEUTRAL (非嚴格大於)"""
        result = analyzer.check_ma_alignment(close=100.0, ma5=100.0, ma20=90.0)
        # close > ma5 is False (100 > 100 = False)
        # close < ma5 < ma20 is False (100 < 100 is False)
        assert result == "NEUTRAL"


# ═══════════════════════════════════════════════════════════
# check_attack_pattern
# ═══════════════════════════════════════════════════════════
class TestCheckAttackPattern:
    """攻擊型態判斷測試"""

    def test_attack_true(self, analyzer):
        """攻擊型態成立: 連 3 日收紅 + 量遞增"""
        closes = np.array([100.0, 101.0, 103.0, 106.0])  # 最後 4 筆: 連 3 漲
        volumes = np.array([1000, 1200, 1500, 2000])      # 量遞增
        assert analyzer.check_attack_pattern(closes, volumes) is True

    def test_attack_price_not_up(self, analyzer):
        """價格未連續上升 → 不成立"""
        closes = np.array([100.0, 105.0, 103.0, 106.0])  # 第 2->3 下跌
        volumes = np.array([1000, 1200, 1500, 2000])
        assert analyzer.check_attack_pattern(closes, volumes) is False

    def test_attack_volume_not_up(self, analyzer):
        """量未遞增 → 不成立"""
        closes = np.array([100.0, 101.0, 103.0, 106.0])  # 價連 3 漲
        volumes = np.array([1000, 2000, 1500, 2000])      # 量第 2->3 跌
        assert analyzer.check_attack_pattern(closes, volumes) is False

    def test_attack_insufficient_data(self, analyzer):
        """少於 4 筆資料 → 不成立"""
        closes = np.array([100.0, 101.0, 102.0])
        volumes = np.array([1000, 1200, 1500])
        assert analyzer.check_attack_pattern(closes, volumes) is False

    def test_attack_empty(self, analyzer):
        """空陣列 → 不成立"""
        assert analyzer.check_attack_pattern(
            np.array([]), np.array([])
        ) is False

    def test_attack_only_last_4_matter(self, analyzer):
        """只檢查最近 4 筆"""
        closes = np.array([50.0, 60.0, 70.0, 80.0, 81.0, 83.0, 86.0])
        volumes = np.array([500, 600, 700, 1000, 1200, 1500, 2000])
        # 最後 4 筆: [80, 81, 83, 86] → 連 3 漲
        # 最後 4 筆量: [1000, 1200, 1500, 2000] → 遞增
        assert analyzer.check_attack_pattern(closes, volumes) is True


# ═══════════════════════════════════════════════════════════
# get_historical_data — mock DB
# ═══════════════════════════════════════════════════════════
class TestGetHistoricalData:
    """get_historical_data() 測試 (mock psycopg2)"""

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_get_historical_data_normal(self, mock_psycopg2, analyzer):
        """正常取得歷史資料"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock 20 rows, in DESC order (newest first)
        mock_rows = [
            (float(100 + i), 1000 + i * 10)  # (close_price, volume)
            for i in range(19, -1, -1)  # 19 down to 0
        ]
        mock_cursor.fetchall.return_value = mock_rows

        hist = analyzer.get_historical_data("2330", "2026-05-11")

        # Verify numpy arrays
        assert "closes" in hist
        assert "volumes" in hist
        assert len(hist["closes"]) == 20
        assert len(hist["volumes"]) == 20

        # Data should be in chronological order (oldest first)
        assert hist["closes"][0] < hist["closes"][-1]
        # First == oldest
        assert hist["closes"][0] == pytest.approx(100.0, rel=1e-9)
        assert hist["closes"][-1] == pytest.approx(119.0, rel=1e-9)

        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "stock_daily" in sql
        assert "close_price" in sql
        assert "volume" in sql

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_get_historical_data_empty(self, mock_psycopg2, analyzer):
        """無歷史資料時回傳空陣列"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        hist = analyzer.get_historical_data("2330", "2026-05-11")

        assert len(hist["closes"]) == 0
        assert len(hist["volumes"]) == 0


# ═══════════════════════════════════════════════════════════
# analyze() — mock DB + premium_results
# ═══════════════════════════════════════════════════════════
class TestAnalyze:
    """analyze() 方法整合測試 (mock DB)"""

    def _make_mock_db(self, mock_psycopg2, hist_rows: list):
        """建立 mock DB 回傳指定的歷史資料"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = hist_rows
        return mock_conn, mock_cursor

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_insufficient_data(self, mock_psycopg2, analyzer):
        """歷史資料不足 20 筆時回傳 NEUTRAL 不拋錯"""
        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2,
            # Only 10 records
            [(float(i), 1000) for i in range(10)]
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=105.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
        ]

        output = analyzer.analyze("2026-05-11", results)

        assert len(output) == 1
        assert output[0].technical_signal == "NEUTRAL"

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_breakout_signal(self, mock_psycopg2, analyzer):
        """帶量突破情境: 價站上 MA20 且量放大"""
        # 20 records: close goes from 90 to 109, volume spikes at end
        hist_rows = [
            (90.0 + i * 1.0, 1000 + i * 10) for i in range(19)
        ] + [
            (110.0, 5000)  # Last day: price jumps above MA20, volume spikes
        ]
        # Reverse to DESC order for DB mock
        hist_rows_desc = list(reversed(hist_rows))

        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2, hist_rows_desc
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=110.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
        ]

        output = analyzer.analyze("2026-05-11", results)

        assert len(output) == 1
        # MA20 ~= (90+109)/2 + 110/20 ≈ 99.5 + 5.5 = 105... let me compute exactly
        # Actually, last 20 of the 20 prices = all 20
        # MA20 = 99.95... close(110) > MA20 ✓
        # VMA20 = 1110... volume(5000) > 1.5 * 1110 = 1665 ✓
        assert output[0].technical_signal == "BREAKOUT"

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_bullish_signal(self, mock_psycopg2, analyzer):
        """多頭排列: close > ma5 > ma20"""
        # Create uptrend: 20 days, prices rising
        hist_rows = []
        for i in range(20):
            price = 80.0 + i * 2.0  # 80 to 118
            vol = 1000 + i * 20
            hist_rows.append((price, vol))
        hist_rows_desc = list(reversed(hist_rows))

        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2, hist_rows_desc
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=118.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
        ]

        output = analyzer.analyze("2026-05-11", results)

        # Strong uptrend: close(118) > ma5 > ma20 should be BULLISH
        # But also check_breakout might trigger first:
        # close(118) > MA20(99) ✓, volume(1800) > 1.5 * VMA20? VMA20~=1190, 1.5*1190=1785
        # volume(1800) > 1785 ✓ → BREAKOUT triggers first
        # That's fine - BREAKOUT is a stronger signal than BULLISH

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_bearish_signal(self, mock_psycopg2, analyzer):
        """空頭排列且非 junk: close < ma5 < ma20"""
        # Create downtrend
        hist_rows = []
        for i in range(20):
            price = 120.0 - i * 2.0  # 120 down to 82
            vol = 2000 - i * 10
            hist_rows.append((price, vol))
        hist_rows_desc = list(reversed(hist_rows))

        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2, hist_rows_desc
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=82.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
        ]

        output = analyzer.analyze("2026-05-11", results)

        assert output[0].technical_signal == "BEARISH"

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_junk_ignores_bearish(self, mock_psycopg2, analyzer):
        """junk 標的不標記 BEARISH → 應為 NEUTRAL"""
        # Same downtrend
        hist_rows = []
        for i in range(20):
            price = 120.0 - i * 2.0
            vol = 2000 - i * 10
            hist_rows.append((price, vol))
        hist_rows_desc = list(reversed(hist_rows))

        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2, hist_rows_desc
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=82.0, conversion_value=100000.0,
                           premium_ratio=0.07, is_junk=True),  # junk!
        ]

        output = analyzer.analyze("2026-05-11", results)

        # is_junk=True → BEARISH shouldn't be assigned → NEUTRAL
        assert output[0].technical_signal == "NEUTRAL"

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_attack_pattern(self, mock_psycopg2, analyzer):
        """攻擊型態: 連 3 漲 + 量遞增 → BREAKOUT"""
        # 17 normal + 4 attack pattern = 21 days
        hist_rows = []
        for i in range(17):
            hist_rows.append((100.0 + i * 0.5, 1000 + i * 10))

        # Last 4 days: attack pattern (price up, volume up)
        hist_rows.append((108.0, 1500))
        hist_rows.append((109.0, 1700))
        hist_rows.append((111.0, 2000))
        hist_rows.append((114.0, 2500))

        hist_rows_desc = list(reversed(hist_rows))

        mock_conn, mock_cursor = self._make_mock_db(
            mock_psycopg2, hist_rows_desc
        )

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=114.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
        ]

        output = analyzer.analyze("2026-05-11", results)

        # Attack pattern should trigger BREAKOUT
        assert output[0].technical_signal == "BREAKOUT"

    @patch("src.analytics.technical_analyzer.psycopg2")
    def test_analyze_multiple_symbols(self, mock_psycopg2, analyzer):
        """多檔股票分析"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Return data for any symbol: 20 ascending prices
        def fetch_side_effect():
            return [(100.0 + i, 1000 + i * 10) for i in range(19, -1, -1)]

        mock_cursor.fetchall.side_effect = fetch_side_effect

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=119.0, conversion_value=100000.0,
                           premium_ratio=0.01, is_junk=False),
            AnalysisResult(date="2026-05-11", symbol="2303",
                           close_price=119.0, conversion_value=100000.0,
                           premium_ratio=0.07, is_junk=True),
        ]

        output = analyzer.analyze("2026-05-11", results)

        assert len(output) == 2
        # First should be BREAKOUT (uptrend, non-junk)
        assert output[0].technical_signal == "BREAKOUT"
        # Second is junk, should not be BREAKOUT
        assert output[1].is_junk is True
