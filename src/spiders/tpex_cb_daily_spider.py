"""
TpexCbDailySpider - TPEx 可轉債日行情爬蟲

功能：
- 抓取 TPEx 可轉債日行情資料
- 支援日期區間抓取
- 存入 PostgreSQL 或 CSV

使用方式：
    spider = TpexCbDailySpider()
    spider.fetch_daily("2024-01-15")
    spider.fetch_date_range("2024-01-01", "2024-01-31")
"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from io import BytesIO

import pandas as pd
import requests

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import TpexCbDailyItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline

logger = logging.getLogger(__name__)


class TpexCbDailySpider(BaseSpider):
    """
    TPEx 可轉債日行情爬蟲
    
    從 TPEx 下載可轉債日行情 CSV
    
    Attributes:
        BASE_URL: TPEx CB Daily API URL
        pipeline: 資料寫入管道
        items: 已抓取的 CB 行情列表
    """
    
    BASE_URL = "https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 TpexCbDailySpider
        
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
        
        self.pipeline = pipeline or CsvPipeline(table_name="tpex_cb_daily")
        self.items: List[TpexCbDailyItem] = []
        
        logger.info("TpexCbDailySpider initialized")
    
    def _convert_date_format(self, date: str) -> str:
        """
        轉換日期格式
        
        Args:
            date: YYYY-MM-DD 格式
        
        Returns:
            YYYY/MM/DD 格式
        """
        return date.replace("-", "/")
    
    def _parse_number(self, value) -> float:
        """
        解析數值
        
        Args:
            value: 數值
        
        Returns:
            float
        """
        if pd.isna(value):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace(",", "").strip()
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def fetch_daily(self, date: str) -> SpiderResponse:
        """
        抓取指定日期的所有 CB 行情
        
        Args:
            date: 日期 (YYYY-MM-DD)
        
        Returns:
            SpiderResponse
        """
        params = {
            "l": "zh-tw",
            "d": self._convert_date_format(date)
        }
        
        try:
            logger.info(f"Fetching TPEx CB Daily: {date}")
            
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            items = self.parse_cb_csv(response.content, date)
            self.items.extend(items)
            
            for item in items:
                self.pipeline.save_items(item)
            
            self.record_request(success=True)
            
            return SpiderResponse(
                success=True,
                data={"count": len(items), "date": date},
                url=self.BASE_URL,
                metadata={"date": date}
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TPEx CB fetch error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=self.BASE_URL
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=self.BASE_URL
            )
    
    def parse_cb_csv(self, content: bytes, target_date: str) -> List[TpexCbDailyItem]:
        """
        解析 TPEx CB CSV
        
        Args:
            content: CSV 原始內容
            target_date: 目標日期
        
        Returns:
            TpexCbDailyItem 列表
        """
        items = []
        
        try:
            df = pd.read_csv(BytesIO(content), encoding="utf-8", dtype=str)
            
            df = df.fillna("")
            
            column_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if "代號" in col and "股票" not in col:
                    column_map["code"] = col
                elif "名稱" in col:
                    column_map["name"] = col
                elif "標的股票" in col:
                    column_map["stock"] = col
                elif "週轉率" in col:
                    column_map["turnover"] = col
                elif "溢價率" in col:
                    column_map["premium"] = col
                elif "轉換價格" in col:
                    column_map["conversion"] = col
                elif "餘額" in col:
                    column_map["balance"] = col
                elif "收盤價" in col:
                    column_map["price"] = col
                elif "成交量" in col:
                    column_map["volume"] = col
            
            for _, row in df.iterrows():
                try:
                    cb_code = str(row.get(column_map.get("code", "代號"), "")).strip()
                    
                    if not cb_code or cb_code == "nan":
                        continue
                    
                    item = TpexCbDailyItem(
                        cb_code=cb_code,
                        cb_name=str(row.get(column_map.get("name", "名稱"), "")).strip(),
                        underlying_stock=str(row.get(column_map.get("stock", "標的股票"), "")).strip(),
                        trade_date=target_date,
                        closing_price=self._parse_number(row.get(column_map.get("price", "收盤價"), 0)),
                        volume=self._parse_number(row.get(column_map.get("volume", "成交量"), 0)),
                        turnover_rate=self._parse_number(row.get(column_map.get("turnover", "週轉率(%)"), 0)),
                        premium_rate=self._parse_number(row.get(column_map.get("premium", "溢價率(%)"), 0)),
                        conversion_price=self._parse_number(row.get(column_map.get("conversion", "轉換價格"), 0)),
                        remaining_balance=self._parse_number(row.get(column_map.get("balance", "餘額(千)"), 0)),
                        source_url=self.BASE_URL,
                        source_type="tpex_cb_daily"
                    )
                    
                    if item.validate():
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"CB row parse error: {e}")
                    continue
            
            logger.info(f"TPEx CB {target_date}: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"TPEx CB CSV parse error: {e}")
        
        return items
    
    def _generate_dates_in_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[str]:
        """
        生成日期區間內的所有日期
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        
        Returns:
            日期字串列表
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = []
        current = start_dt
        
        while current <= end_dt:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return dates
    
    def fetch_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        抓取日期區間內所有日期的 CB 行情
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
        
        Returns:
            包含抓取結果的字典
        """
        dates = self._generate_dates_in_range(start_date, end_date)
        
        results = {
            "start_date": start_date,
            "end_date": end_date,
            "total_dates": len(dates),
            "total_items": 0,
            "success_count": 0,
            "error_count": 0,
            "errors": []
        }
        
        logger.info(f"Fetching TPEx CB from {start_date} to {end_date} ({len(dates)} days)")
        
        for date in dates:
            response = self.fetch_daily(date)
            
            if response.success:
                results["success_count"] += 1
                results["total_items"] += response.data.get("count", 0) if response.data else 0
            else:
                results["error_count"] += 1
                results["errors"].append({
                    "date": date,
                    "error": response.error
                })
        
        return results
    
    def get_items(self) -> List[TpexCbDailyItem]:
        """取得所有爬取的 Item"""
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計"""
        stats = super().get_statistics()
        stats.update({
            "total_items": len(self.items),
            "unique_cb_count": len(set(item.cb_code for item in self.items if item.cb_code)),
        })
        return stats
    
    def close(self):
        """關閉 Pipeline"""
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return f"<TpexCbDailySpider items={len(self.items)}>"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TpexCbDailySpider")
    parser.add_argument("--date", help="Date (YYYY-MM-DD)")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="tpex_cb_daily")
    
    spider = TpexCbDailySpider(pipeline=pipeline)
    
    if args.start and args.end:
        results = spider.fetch_date_range(args.start, args.end)
        print(f"Results: {results}")
    elif args.date:
        response = spider.fetch_daily(args.date)
        print(f"Response: success={response.success}, count={response.data.get('count', 0) if response.data else 0}")
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        response = spider.fetch_daily(today)
        print(f"Response: success={response.success}, count={response.data.get('count', 0) if response.data else 0}")
    
    print(f"Statistics: {spider.get_statistics()}")
    spider.close()
