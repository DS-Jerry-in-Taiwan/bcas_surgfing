from datetime import date, timedelta
import calendar
from typing import List
import logging

logger = logging.getLogger(__name__)

class TradingCalendar:
    """交易日曆（基於簡單規則）"""
    
    # 國定假日映射（年份 → [月-日]）
    NATIONAL_HOLIDAYS = {
        2026: [
            "01-01",  # 元旦
            "02-28",  # 和平紀念日
            "04-04",  # 兒童節
            "04-05",  # 清明節
            "06-10",  # 端午節
            "09-28",  # 教師節
            "10-10",  # 雙十節
        ]
    }
    
    # 補班日（年份 → [月-日]）
    MAKEUP_DAYS = {
        2026: []
    }
    
    @staticmethod
    def get_trading_days(year: int, month: int) -> List[str]:
        """
        回傳該月份的交易日清單（YYYY-MM-DD 格式）
        不包含：週六、週日、國定假日
        """
        trading_days = []
        
        # 生成該月所有日期
        days_in_month = calendar.monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 排除週末（0=Monday, 5=Saturday, 6=Sunday）
            if current_date.weekday() >= 5:
                continue
            
            # 排除國定假日
            holiday_key = f"{month:02d}-{day:02d}"
            if year in TradingCalendar.NATIONAL_HOLIDAYS:
                if holiday_key in TradingCalendar.NATIONAL_HOLIDAYS[year]:
                    continue
            
            # 加入交易日
            trading_days.append(date_str)
        
        return sorted(trading_days)
    
    @staticmethod
    def count_trading_days(year: int, month: int) -> int:
        """回傳該月份的交易日數"""
        return len(TradingCalendar.get_trading_days(year, month))
    
    @staticmethod
    def get_trading_days_range(start_date: str, end_date: str) -> List[str]:
        """
        回傳日期範圍內的所有交易日（YYYY-MM-DD）
        start_date, end_date: 格式 "YYYY-MM-DD"
        """
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        all_trading_days = []
        current = start
        
        while current.year < end.year or (current.year == end.year and current.month <= end.month):
            trading_days = TradingCalendar.get_trading_days(current.year, current.month)
            # 只保留在日期範圍內的
            for day in trading_days:
                if start_date <= day <= end_date:
                    all_trading_days.append(day)
            
            # 移到下一個月
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        return sorted(list(set(all_trading_days)))
    
    @staticmethod
    def is_trading_day(date_str: str) -> bool:
        """檢查某日是否為交易日"""
        d = date.fromisoformat(date_str)
        trading_days = TradingCalendar.get_trading_days(d.year, d.month)
        return date_str in trading_days
