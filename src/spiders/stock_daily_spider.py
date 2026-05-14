"""
StockDailySpider - TWSE 個股日行情爬蟲

功能：
- 抓取 TWSE 個股日行情資料
- 支援日期區間抓取
- 存入 PostgreSQL 或 CSV

使用方式：
    spider = StockDailySpider()
    spider.fetch_daily("2330", 2024, 1)
    spider.fetch_date_range("2330", "2024-01-01", "2024-01-31")
"""
from __future__ import annotations

import logging
import time
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta

import requests

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import StockDailyItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline
from src.utils.date_converter import convert_minguo_date

logger = logging.getLogger(__name__)


class StockDailySpider(BaseSpider):
    """
    TWSE 個股日行情爬蟲
    
    支援指定股票、指定月份的日行情資料抓取
    
    Attributes:
        TWSE_URL: TWSE 日行情 API URL
        pipeline: 資料寫入管道
        items: 已抓取的行情列表
    """
    
    TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 StockDailySpider
        
        Args:
            pipeline: 資料寫入管道（預設 CsvPipeline）
            thread_count: 執行緒數
            redis_key: Redis 鍵
        """
        super().__init__(
            thread_count=thread_count,
            redis_key=redis_key,
            **kwargs
        )
        
        self.pipeline = pipeline or CsvPipeline(table_name="stock_daily")
        self.items: List[StockDailyItem] = []
        
        logger.info("StockDailySpider initialized")
    
    def _parse_number(self, value: str) -> Union[int, float]:
        """
        解析數值字串，處理千分位逗號
        
        Args:
            value: 數值字串（如 "1,234,567" 或 "1,234.56"）
        
        Returns:
            int 或 float
        """
        if not value or value.strip() == "":
            return 0
        
        cleaned = value.replace(",", "").replace("+", "").strip()
        
        try:
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except (ValueError, TypeError):
            return 0
    
    def _convert_minguo_date(self, minguo_date: str) -> str:
        """
        將民國年轉換為西元年
        
        Args:
            minguo_date: 民國年格式（如 "113/01/15"）
        
        Returns:
            西元年格式（如 "2024-01-15"）
        """
        return convert_minguo_date(minguo_date)
    
    def fetch_daily(self, symbol: str, year: int, month: int) -> SpiderResponse:
        """
        抓取單一股票單月資料（含自動重試）

        Args:
            symbol: 股票代號（如 "2330"）
            year: 年份（如 2024）
            month: 月份（1-12）

        Returns:
            SpiderResponse
        """
        max_retries = 3
        last_error = None
        params = {
            "response": "json",
            "date": f"{year}{month:02d}01",
            "stockNo": symbol,
        }

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Fetching TWSE daily: {symbol} {year}/{month:02d} (attempt {attempt}/{max_retries})")

                response = requests.get(
                    self.TWSE_URL,
                    params=params,
                    headers=self.headers,
                    timeout=30,
                )
                response.raise_for_status()

                data = response.json()

                if data.get("stat") != "OK":
                    logger.warning(f"TWSE API error: {data.get('stat')}")
                    self.record_request(success=False)
                    return SpiderResponse(
                        success=False,
                        error=f"API error: {data.get('stat')}",
                        url=self.TWSE_URL,
                        metadata={"symbol": symbol, "year": year, "month": month},
                    )

                # 成功
                items = self.parse_twse_json(data, symbol)
                self.items.extend(items)
                for item in items:
                    self.add_item(item)
                self.record_request(success=True)

                return SpiderResponse(
                    success=True,
                    data={"count": len(items), "symbol": symbol, "year": year, "month": month},
                    url=self.TWSE_URL,
                    metadata={"symbol": symbol, "year": year, "month": month},
                )

            except (requests.RequestException, ValueError) as e:
                last_error = str(e)
                logger.warning(
                    "Attempt %d/%d failed for %s %d/%d: %s",
                    attempt, max_retries, symbol, year, month, e,
                )
                self.record_request(success=False)

                if attempt < max_retries:
                    delay = 2 ** attempt  # 2s, 4s
                    logger.info("Retrying in %ds...", delay)
                    time.sleep(delay)

        # 所有重試都失敗
        logger.error("All %d attempts failed for %s %d/%d: %s", max_retries, symbol, year, month, last_error)
        return SpiderResponse(
            success=False,
            error=last_error,
            url=self.TWSE_URL,
        )
    
    def parse_twse_json(self, data: dict, symbol: str) -> List[StockDailyItem]:
        """
        解析 TWSE JSON 回應
        
        Args:
            data: TWSE API 回應的 JSON 資料
            symbol: 股票代號
        
        Returns:
            StockDailyItem 列表
        """
        items = []
        
        try:
            raw_data = data.get("data", [])
            fields = data.get("fields", [])
            
            if not raw_data:
                logger.warning(f"TWSE: No data for {symbol}")
                return items
            
            field_map = {}
            for i, field in enumerate(fields):
                field_lower = field.lower()
                if "日期" in field:
                    field_map["date"] = i
                elif "開盤價" in field:
                    field_map["open"] = i
                elif "最高價" in field:
                    field_map["high"] = i
                elif "最低價" in field:
                    field_map["low"] = i
                elif "收盤價" in field:
                    field_map["close"] = i
                elif "成交筆數" in field:
                    field_map["transactions"] = i
                elif "成交股數" in field:
                    field_map["volume"] = i
                elif "漲跌" in field:
                    field_map["change"] = i
            
            for row in raw_data:
                try:
                    minguo_date = row[field_map.get("date", 0)]
                    ad_date = self._convert_minguo_date(minguo_date)
                    
                    item = StockDailyItem(
                        symbol=symbol,
                        date=ad_date,
                        open_price=self._parse_number(row[field_map.get("open", 3)]),
                        high_price=self._parse_number(row[field_map.get("high", 4)]),
                        low_price=self._parse_number(row[field_map.get("low", 5)]),
                        close_price=self._parse_number(row[field_map.get("close", 6)]),
                        volume=self._parse_number(row[field_map.get("volume", 2)]),
                        price_change=self._parse_number(row[field_map.get("change", 7)]),
                        transaction_count=self._parse_number(row[field_map.get("transactions", 8)]),
                        source_url=self.TWSE_URL,
                        source_type="twse_daily"
                    )
                    
                    if item.validate():
                        items.append(item)
                        
                except (IndexError, ValueError) as e:
                    logger.debug(f"TWSE row parse error: {e}")
                    continue
            
            logger.info(f"TWSE {symbol}: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"TWSE JSON parse error: {e}")
        
        return items
    
    def _generate_months_in_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[tuple]:
        """
        生成日期區間內的所有月份
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        
        Returns:
            [(year, month), ...] 列表
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        months = []
        current = start_dt
        
        while current <= end_dt:
            months.append((current.year, current.month))
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
        
        return months
    
    def fetch_date_range(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        抓取日期區間內所有月份的資料
        
        Args:
            symbol: 股票代號
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        
        Returns:
            包含抓取結果的字典
        """
        months = self._generate_months_in_range(start_date, end_date)
        
        results = {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "months": len(months),
            "total_items": 0,
            "success_count": 0,
            "error_count": 0,
            "errors": []
        }
        
        logger.info(f"Fetching {symbol} from {start_date} to {end_date} ({len(months)} months)")
        
        for year, month in months:
            response = self.fetch_daily(symbol, year, month)
            
            if response.success:
                results["success_count"] += 1
                results["total_items"] += response.data.get("count", 0) if response.data else 0
            else:
                results["error_count"] += 1
                results["errors"].append({
                    "year": year,
                    "month": month,
                    "error": response.error
                })
        
        return results
    
    def get_items(self) -> List[StockDailyItem]:
        """取得所有爬取的 Item"""
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計"""
        stats = super().get_statistics()
        stats.update({
            "total_items": len(self.items),
            "unique_dates": len(set(item.date for item in self.items if item.date)),
        })
        return stats
    
    def close(self):
        """關閉 Pipeline"""
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return f"<StockDailySpider items={len(self.items)}>"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="StockDailySpider")
    parser.add_argument("--symbol", required=True, help="Stock symbol")
    parser.add_argument("--year", type=int, required=True, help="Year")
    parser.add_argument("--month", type=int, required=True, help="Month")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="stock_daily")
    
    spider = StockDailySpider(pipeline=pipeline)
    
    if args.start and args.end:
        results = spider.fetch_date_range(args.symbol, args.start, args.end)
        print(f"Results: {results}")
    else:
        response = spider.fetch_daily(args.symbol, args.year, args.month)
        print(f"Response: success={response.success}, count={response.data.get('count', 0) if response.data else 0}")
    
    print(f"Statistics: {spider.get_statistics()}")
    spider.close()
