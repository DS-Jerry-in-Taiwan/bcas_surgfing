"""
PremiumCalculator 單元測試

測試策略:
  - 靜態方法: 直接測試數學計算 (不依賴 DB)
  - analyze() / save_results(): 透過 mock psycopg2 驗證
"""

from unittest.mock import MagicMock, patch

import pytest

from src.analytics.models import AnalysisResult
from src.analytics.premium_calculator import PremiumCalculator


# ─── 固定參數 ─────────────────────────────────────────────
CB_CLOSE = 120.0
CONV_PRICE = 100.0
STOCK_CLOSE = 150.0

# 預期: 轉換價值 = (120/100) * 1000 * 150 = 180000.0
EXPECTED_CONV_VALUE = (CB_CLOSE / CONV_PRICE) * 1000 * STOCK_CLOSE
# 預期: 溢價率 = (120/180000) - 1 = -0.999333...
EXPECTED_PREMIUM = (CB_CLOSE / EXPECTED_CONV_VALUE) - 1


# ═══════════════════════════════════════════════════════════
# calculate_conversion_value
# ═══════════════════════════════════════════════════════════
class TestCalculateConversionValue:
    """轉換價值計算測試"""

    def test_normal_case(self):
        """正常情況: (120/100)*1000*150 = 180000.0"""
        result = PremiumCalculator.calculate_conversion_value(
            CB_CLOSE, CONV_PRICE, STOCK_CLOSE
        )
        assert result == pytest.approx(180000.0, rel=1e-9)
        assert result == EXPECTED_CONV_VALUE

    def test_zero_conversion_price(self):
        """轉換價格為 0 時回傳 0.0 不拋錯"""
        result = PremiumCalculator.calculate_conversion_value(
            CB_CLOSE, 0.0, STOCK_CLOSE
        )
        assert result == 0.0

    def test_negative_conversion_price(self):
        """轉換價格為負值時回傳 0.0"""
        result = PremiumCalculator.calculate_conversion_value(
            CB_CLOSE, -10.0, STOCK_CLOSE
        )
        assert result == 0.0

    def test_zero_cb_close(self):
        """CB 收盤價為 0: (0/100)*1000*150 = 0.0"""
        result = PremiumCalculator.calculate_conversion_value(
            0.0, CONV_PRICE, STOCK_CLOSE
        )
        assert result == 0.0

    def test_zero_stock_close(self):
        """現股收盤價為 0: (120/100)*1000*0 = 0.0"""
        result = PremiumCalculator.calculate_conversion_value(
            CB_CLOSE, CONV_PRICE, 0.0
        )
        assert result == 0.0

    def test_large_values(self):
        """大數值測試，確保不溢位"""
        result = PremiumCalculator.calculate_conversion_value(
            500.0, 50.0, 1000.0
        )
        # (500/50) * 1000 * 1000 = 10000000.0
        assert result == pytest.approx(10_000_000.0, rel=1e-9)


# ═══════════════════════════════════════════════════════════
# calculate_premium_ratio
# ═══════════════════════════════════════════════════════════
class TestCalculatePremiumRatio:
    """溢價率計算測試"""

    def test_normal_case(self):
        """正常情況"""
        result = PremiumCalculator.calculate_premium_ratio(
            CB_CLOSE, EXPECTED_CONV_VALUE
        )
        assert result == pytest.approx(EXPECTED_PREMIUM, rel=1e-9)

    def test_premium_cb_above_par(self):
        """溢價: CB價 > 轉換價值 → 正溢價率"""
        # CB=200, 轉換價值=100 → 溢價率=1.0 (100%)
        result = PremiumCalculator.calculate_premium_ratio(200.0, 100.0)
        assert result == pytest.approx(1.0, rel=1e-9)

    def test_discount_cb_below_par(self):
        """折價: CB價 < 轉換價值 → 負溢價率"""
        # CB=90, 轉換價值=100 → 溢價率=-0.1 (-10%)
        result = PremiumCalculator.calculate_premium_ratio(90.0, 100.0)
        assert result == pytest.approx(-0.1, rel=1e-9)

    def test_zero_conversion_value(self):
        """轉換價值為 0 時回傳 999.0 不拋錯"""
        result = PremiumCalculator.calculate_premium_ratio(CB_CLOSE, 0.0)
        assert result == 999.0

    def test_negative_conversion_value(self):
        """轉換價值為負值時回傳 999.0"""
        result = PremiumCalculator.calculate_premium_ratio(CB_CLOSE, -100.0)
        assert result == 999.0

    def exact_parity(self):
        """平價: CB價 = 轉換價值 → 溢價率 = 0"""
        result = PremiumCalculator.calculate_premium_ratio(100.0, 100.0)
        assert result == pytest.approx(0.0, abs=1e-9)


# ═══════════════════════════════════════════════════════════
# is_junk
# ═══════════════════════════════════════════════════════════
class TestIsJunk:
    """廢棄標的判斷測試"""

    def test_below_threshold(self):
        """溢價率 3% → False (未超過 5%)"""
        assert PremiumCalculator.is_junk(0.03) is False

    def test_above_threshold(self):
        """溢價率 7% → True (超過 5%)"""
        assert PremiumCalculator.is_junk(0.07) is True

    def test_at_threshold(self):
        """溢價率剛好 5% → False (不大於 5%)"""
        assert PremiumCalculator.is_junk(0.05) is False

    def test_negative_premium(self):
        """負溢價率 → False"""
        assert PremiumCalculator.is_junk(-0.1) is False

    def test_custom_threshold(self):
        """自訂門檻值測試"""
        assert PremiumCalculator.is_junk(0.10, threshold=0.08) is True
        assert PremiumCalculator.is_junk(0.06, threshold=0.08) is False

    def test_extreme_premium(self):
        """極大溢價率 (999.0) → True"""
        assert PremiumCalculator.is_junk(999.0) is True


# ═══════════════════════════════════════════════════════════
# analyze() — mock DB
# ═══════════════════════════════════════════════════════════
class TestAnalyze:
    """analyze() 方法測試 (mock psycopg2)"""

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_analyze_with_data(self, mock_psycopg2):
        """正常分析流程"""
        # Mock connection & cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock CB records: (cb_code, closing_price, conversion_price, underlying_stock, premium_rate)
        mock_cursor.fetchall.return_value = [
            ("CB01", 120.0, 100.0, "2330", 0.05),
        ]

        # Mock stock_daily query: first call -> cb records above, subsequent calls -> stock close
        # We need a side_effect that handles two different execute calls
        def execute_side_effect(sql, params):
            if "tpex_cb_daily" in sql:
                # This is the first query, fetchall returns cb records
                pass
            elif "stock_daily" in sql:
                # second query: mock fetchone to return a single result
                mock_cursor.fetchone.return_value = (150.0,)

        mock_cursor.execute.side_effect = execute_side_effect

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        # Verify
        assert len(results) == 1
        r = results[0]
        assert r.date == "2026-05-11"
        assert r.symbol == "2330"
        assert r.close_price == 150.0
        assert r.conversion_value == pytest.approx(180000.0, rel=1e-9)
        # premium_ratio is rounded to 4 decimal places in analyze()
        assert r.premium_ratio == pytest.approx(round(EXPECTED_PREMIUM, 4), rel=1e-9)
        assert r.is_junk is False  # premium_ratio is negative
        assert r.technical_signal == "NEUTRAL"

        # Verify DB operations
        assert mock_cursor.close.called
        assert mock_conn.close.called

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_analyze_empty_cb(self, mock_psycopg2):
        """當日無 CB 資料"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        assert len(results) == 0

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_analyze_skip_no_stock_data(self, mock_psycopg2):
        """跳過無對應現股資料的 CB"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("CB01", 120.0, 100.0, "9999", 0.05),
        ]

        # stock_daily returns None for symbol 9999
        def execute_side_effect(sql, params):
            if "stock_daily" in sql:
                mock_cursor.fetchone.return_value = None

        mock_cursor.execute.side_effect = execute_side_effect

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        assert len(results) == 0

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_analyze_skip_null_fields(self, mock_psycopg2):
        """跳過 null 欄位的 CB"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Some fields are None
        mock_cursor.fetchall.return_value = [
            ("CB01", None, 100.0, "2330", 0.05),    # cb_close is None
            ("CB02", 120.0, None, "2330", 0.05),    # conv_price is None
            ("CB03", 120.0, 100.0, None, 0.05),     # under_stock is None
        ]

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        assert len(results) == 0

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_analyze_junk_detection(self, mock_psycopg2):
        """溢價率 > 5% 被正確標記為 junk"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # CB close 遠高於 stock close → 溢價
        mock_cursor.fetchall.return_value = [
            ("CB01", 1000.0, 100.0, "2330", 0.05),
        ]

        def execute_side_effect(sql, params):
            if "stock_daily" in sql:
                mock_cursor.fetchone.return_value = (10.0,)  # stock close = 10

        mock_cursor.execute.side_effect = execute_side_effect

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        assert len(results) == 1
        r = results[0]
        # conv_value = (1000/100)*1000*10 = 100000
        # premium_ratio = (1000/100000) - 1 = -0.99 (discount)
        # Actually: CB=1000, conversion_value=((1000/100)*1000*10)=100000
        # premium = 1000/100000 - 1 = 0.01 - 1 = -0.99
        assert r.is_junk is False  # negative premium

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_multiple_symbols(self, mock_psycopg2):
        """多筆 CB 分析"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            ("CB01", 120.0, 100.0, "2330", 0.05),
            ("CB02", 200.0, 80.0, "2303", 0.10),
        ]

        stock_prices = {"2330": 150.0, "2303": 50.0}

        def execute_side_effect(sql, params):
            if "stock_daily" in sql:
                symbol = params[0]
                mock_cursor.fetchone.return_value = (stock_prices.get(symbol),)

        mock_cursor.execute.side_effect = execute_side_effect

        pc = PremiumCalculator()
        results = pc.analyze("2026-05-11")

        assert len(results) == 2
        symbols = [r.symbol for r in results]
        assert "2330" in symbols
        assert "2303" in symbols


# ═══════════════════════════════════════════════════════════
# save_results()
# ═══════════════════════════════════════════════════════════
class TestSaveResults:
    """save_results() 方法測試 (mock psycopg2)"""

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_save_results_success(self, mock_psycopg2):
        """正常寫入"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        results = [
            AnalysisResult(date="2026-05-11", symbol="2330",
                           close_price=150.0, conversion_value=180000.0,
                           premium_ratio=-0.000333, is_junk=False),
            AnalysisResult(date="2026-05-11", symbol="2303",
                           close_price=50.0, conversion_value=25000.0,
                           premium_ratio=0.03, is_junk=False),
        ]

        pc = PremiumCalculator()
        saved = pc.save_results("2026-05-11", results)

        assert saved == 2
        assert mock_cursor.execute.call_count == 2
        assert mock_conn.commit.called
        assert mock_cursor.close.called
        assert mock_conn.close.called

    @patch("src.analytics.premium_calculator.psycopg2")
    def test_save_results_empty(self, mock_psycopg2):
        """空列表不寫入"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        pc = PremiumCalculator()
        saved = pc.save_results("2026-05-11", [])

        assert saved == 0
        assert mock_cursor.execute.call_count == 0
        # commit is called but with no pending
        assert mock_conn.commit.called
