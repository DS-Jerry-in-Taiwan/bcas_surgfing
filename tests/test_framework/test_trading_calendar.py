import pytest
from datetime import date
from src.utils.trading_calendar import TradingCalendar


class TestTradingCalendar:
    """Test TradingCalendar functionality"""
    
    def test_get_trading_days_2026_01(self):
        """2026-01 應排除週末與元旦"""
        trading_days = TradingCalendar.get_trading_days(2026, 1)
        assert len(trading_days) > 0
        assert "2026-01-01" not in trading_days  # 元旦
        
        # 檢查沒有週末
        for day_str in trading_days:
            d = date.fromisoformat(day_str)
            assert d.weekday() < 5, f"{day_str} 是週末"

    def test_get_trading_days_contains_weekdays_only(self):
        """交易日應只包含週一至週五"""
        trading_days = TradingCalendar.get_trading_days(2026, 4)
        for day_str in trading_days:
            d = date.fromisoformat(day_str)
            assert d.weekday() < 5

    def test_get_trading_days_sorted(self):
        """交易日應按時間順序排列"""
        trading_days = TradingCalendar.get_trading_days(2026, 4)
        assert trading_days == sorted(trading_days)

    def test_count_trading_days(self):
        """計數應與清單長度相符"""
        count = TradingCalendar.count_trading_days(2026, 4)
        days = TradingCalendar.get_trading_days(2026, 4)
        assert count == len(days)

    def test_get_trading_days_range_single_month(self):
        """單月範圍查詢應正確"""
        trading_days = TradingCalendar.get_trading_days_range("2026-04-01", "2026-04-30")
        single_month = TradingCalendar.get_trading_days(2026, 4)
        # 應該是子集
        for day in trading_days:
            assert day in single_month

    def test_get_trading_days_range_multiple_months(self):
        """多月範圍查詢應跨月份正確"""
        trading_days = TradingCalendar.get_trading_days_range("2026-01-01", "2026-02-28")
        assert len(trading_days) >= 30  # 兩個月至少 30 天

    def test_get_trading_days_range_sorted(self):
        """日期範圍結果應排序"""
        trading_days = TradingCalendar.get_trading_days_range("2026-01-01", "2026-03-31")
        assert trading_days == sorted(trading_days)

    def test_is_trading_day_holiday(self):
        """2026-01-01 是元旦，不是交易日"""
        assert not TradingCalendar.is_trading_day("2026-01-01")

    def test_is_trading_day_normal(self):
        """2026-01-02 是週五，是交易日"""
        assert TradingCalendar.is_trading_day("2026-01-02")

    def test_is_trading_day_saturday(self):
        """週六不是交易日"""
        # 2026-01-03 是週六
        assert not TradingCalendar.is_trading_day("2026-01-03")

    def test_is_trading_day_sunday(self):
        """週日不是交易日"""
        # 2026-01-04 是週日
        assert not TradingCalendar.is_trading_day("2026-01-04")

    def test_get_trading_days_february_2026(self):
        """2026-02 應包含平和紀念日（02-28）"""
        trading_days = TradingCalendar.get_trading_days(2026, 2)
        assert "2026-02-28" not in trading_days  # 和平紀念日

    def test_get_trading_days_april_2026(self):
        """2026-04 應排除兒童節（04-04）和清明節（04-05）"""
        trading_days = TradingCalendar.get_trading_days(2026, 4)
        assert "2026-04-04" not in trading_days  # 兒童節
        assert "2026-04-05" not in trading_days  # 清明節

    def test_get_trading_days_range_boundary(self):
        """邊界日期應正確包含"""
        start = "2026-01-02"
        end = "2026-01-02"
        trading_days = TradingCalendar.get_trading_days_range(start, end)
        # 2026-01-02 是週五，應該包含
        assert start in trading_days

    def test_get_trading_days_range_no_duplicates(self):
        """日期範圍結果應無重複"""
        trading_days = TradingCalendar.get_trading_days_range("2026-01-01", "2026-12-31")
        assert len(trading_days) == len(set(trading_days))

    def test_count_trading_days_april_2026(self):
        """2026-04 應有特定數量的交易日"""
        # 計算預期值
        count = TradingCalendar.count_trading_days(2026, 4)
        # 4 月有 30 天，週六週日各 4 天，加上 3 個假日
        # 應該約 21-22 天
        assert count >= 18
        assert count <= 22

    def test_get_trading_days_consecutive_months(self):
        """連續月份查詢應無縫銜接"""
        days_march = TradingCalendar.get_trading_days(2026, 3)
        days_april = TradingCalendar.get_trading_days(2026, 4)
        days_range = TradingCalendar.get_trading_days_range("2026-03-01", "2026-04-30")
        
        # 應該 = march + april
        combined = sorted(set(days_march + days_april))
        assert days_range == combined

    def test_trading_calendar_year_consistency(self):
        """同年份的 holidays 應一致"""
        # 2026-01-01 應始終返回 False
        assert not TradingCalendar.is_trading_day("2026-01-01")
        # 2026-02-28 應始終返回 False
        assert not TradingCalendar.is_trading_day("2026-02-28")

    def test_trading_days_format(self):
        """交易日格式應為 YYYY-MM-DD"""
        trading_days = TradingCalendar.get_trading_days(2026, 4)
        for day_str in trading_days:
            # 應該能轉換為 date
            d = date.fromisoformat(day_str)
            assert d.year == 2026
            assert d.month == 4

    def test_get_trading_days_year_with_holidays(self):
        """包含多個假日的月份應正確排除"""
        trading_days = TradingCalendar.get_trading_days(2026, 10)
        assert "2026-10-10" not in trading_days  # 雙十節

    def test_get_trading_days_range_with_holidays(self):
        """範圍查詢應正確排除假日"""
        trading_days = TradingCalendar.get_trading_days_range("2026-10-01", "2026-10-31")
        assert "2026-10-10" not in trading_days  # 雙十節


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
