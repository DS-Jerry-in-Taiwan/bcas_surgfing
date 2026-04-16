"""
ExampleSpider - 全鏈路打通範例爬蟲

示範從爬取到入庫的完整流程
"""
from __future__ import annotations

import logging
import traceback
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from feapder import AirSpider, Request
except ImportError:
    AirSpider = object
    Request = object

import requests

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import StockDailyItem
from src.framework.pipelines import CsvPipeline, MemoryPipeline
from src.framework.alerts import alert_manager, AlertLevel

logger = logging.getLogger(__name__)


class ExampleSpider(BaseSpider if BaseSpider else object):
    """
    範例爬蟲
    
    功能：
    - 從 TWSE API 抓取股票日成交資料
    - 解析為 StockDailyItem
    - 寫入 CSV 檔案
    """
    
    BASE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        # 初始化 BaseSpider
        super().__init__(
            thread_count=thread_count,
            redis_key=redis_key,
            **kwargs
        )
        
        # Pipeline 配置
        self.pipeline = pipeline or MemoryPipeline()
        
        # 統計
        self.items: List[StockDailyItem] = []
        self.success_count: int = 0
        self.error_count: int = 0
        
        logger.info(f"ExampleSpider initialized: thread={thread_count}")
    
    def fetch_stock(self, stock: str, year: int, month: int) -> SpiderResponse:
        """
        手動抓取單支股票
        
        Args:
            stock: 股票代碼
            year: 年份
            month: 月份
        
        Returns:
            SpiderResponse
        """
        url = self.BASE_URL
        params = {
            "response": "json",
            "date": f"{year}{month:02d}01",
            "stockNo": stock
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            parsed = self.parse_response(response)
            
            if parsed.success and parsed.data:
                data = parsed.data
                if data.get("stat") == "OK":
                    records = data.get("data", [])
                    for record in records:
                        try:
                            item = self._parse_record(record, stock, year, month)
                            if item and item.validate():
                                self.items.append(item)
                                self.pipeline.save_items(item)
                                self.success_count += 1
                        except Exception as e:
                            logger.error(f"Failed to parse record: {e}")
                            self.error_count += 1
                else:
                    self.error_count += 1
            else:
                self.error_count += 1
            
            return parsed
            
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            self.error_count += 1
            
            if hasattr(self, 'alert_enabled') and self.alert_enabled:
                alert_manager.error(
                    title=f"ExampleSpider Fetch Error",
                    message=str(e),
                    spider_name=self.__class__.__name__,
                    error_details=traceback.format_exc()
                )
            
            return SpiderResponse(success=False, error=str(e))
    
    def batch_fetch(self, stocks: List[str], year: int, month: int):
        """批次抓取多支股票"""
        for stock in stocks:
            self.fetch_stock(stock, year, month)
    
    def _parse_record(self, record: List[str], stock: str, year: int, month: int) -> Optional[StockDailyItem]:
        """解析單筆記錄"""
        try:
            # TWSE 格式: ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", ...]
            date_str = record[0]
            open_price = self._parse_price(record[3])
            high_price = self._parse_price(record[4])
            low_price = self._parse_price(record[5])
            close_price = self._parse_price(record[6])
            volume = self._parse_volume(record[1])
            
            return StockDailyItem(
                symbol=stock,
                date=self._convert_date(date_str),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                source_url=self.BASE_URL,
                source_type="twse"
            )
        except Exception as e:
            logger.error(f"Record parse error: {e}")
            return None
    
    def _parse_price(self, price_str: str) -> float:
        """解析價格"""
        try:
            return float(price_str.replace(",", ""))
        except:
            return 0.0
    
    def _parse_volume(self, volume_str: str) -> int:
        """解析成交量"""
        try:
            return int(volume_str.replace(",", ""))
        except:
            return 0
    
    def _convert_date(self, minguo_date: str) -> str:
        """民國年轉西元年"""
        try:
            parts = minguo_date.split("/")
            year = int(parts[0]) + 1911
            month = parts[1].zfill(2)
            day = parts[2].zfill(2)
            return f"{year}-{month}-{day}"
        except:
            return datetime.now().strftime("%Y-%m-%d")
    
    def get_items(self) -> List[StockDailyItem]:
        """取得所有爬取的 Item"""
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計"""
        total = self.success_count + self.error_count
        return {
            "request_count": total,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / total * 100) if total > 0 else 100.0,
            "items_collected": len(self.items)
        }
    
    def close(self):
        """關閉 Pipeline"""
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return f"<ExampleSpider items={len(self.items)} success={self.success_count} error={self.error_count}>"
