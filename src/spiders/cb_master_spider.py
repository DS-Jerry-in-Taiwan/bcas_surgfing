"""
CbMasterSpider - 可轉債主檔爬蟲

功能：
- 下載 TPEx CB Master CSV
- Big5 編碼處理
- 存入 PostgreSQL 或 CSV

使用方式：
    spider = CbMasterSpider()
    spider.start()
"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from io import BytesIO, StringIO

import pandas as pd
import requests

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import CbMasterItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline

logger = logging.getLogger(__name__)


class CbMasterSpider(BaseSpider):
    """
    可轉債主檔爬蟲
    
    從 TPEx 下載可轉債主檔 CSV
    
    Attributes:
        BASE_URL: TPEx CB CSV 基本 URL
        pipeline: 資料寫入管道
        items: 已抓取的 CB 列表
        days_back: 回查天數
    """
    
    BASE_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
    
    def __init__(
        self,
        pipeline=None,
        days_back: int = 30,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 CbMasterSpider
        
        Args:
            pipeline: 資料寫入管道（預設 CsvPipeline）
            days_back: 回查天數
            thread_count: 執行緒數
            redis_key: Redis 鍵
        """
        super().__init__(
            thread_count=thread_count,
            redis_key=redis_key,
            **kwargs
        )
        
        self.pipeline = pipeline or CsvPipeline(table_name="cb_master")
        self.items: List[CbMasterItem] = []
        self.days_back = days_back
        
        logger.info(f"CbMasterSpider initialized: days_back={days_back}")
    
    def _generate_dates(self, days: int = None) -> List[str]:
        """
        生成日期列表
        
        Args:
            days: 天數（預設使用 self.days_back）
        
        Returns:
            YYYYMMDD 格式的日期列表
        """
        days = days or self.days_back
        dates = []
        today = datetime.now()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            dates.append(date_str)
        
        return dates
    
    def _build_url(self, date: str) -> str:
        """
        建立 CSV URL
        
        Args:
            date: YYYYMMDD 格式日期
        
        Returns:
            CSV 下載 URL
        """
        year = date[:4]
        year_month = date[:6]
        return f"{self.BASE_URL}/{year}/{year_month}/RSdrs001.{date}-C.csv"
    
    def fetch_cb_master(self, date: str = None) -> SpiderResponse:
        """
        抓取指定日期的 CB Master
        
        Args:
            date: YYYYMMDD 格式日期（預設今天）
        
        Returns:
            SpiderResponse
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        url = self._build_url(date)
        
        try:
            logger.info(f"Fetching CB Master from {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"CB Master download failed: {response.status_code}")
                self.record_request(success=False)
                return SpiderResponse(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    url=url
                )
            
            items = self.parse_cb_csv(response.content, date)
            self.items.extend(items)
            
            for item in items:
                self.pipeline.save_items(item)
            
            self.record_request(success=True)
            
            return SpiderResponse(
                success=True,
                data={"count": len(items), "date": date},
                url=url,
                metadata={"date": date}
            )
            
        except Exception as e:
            logger.error(f"CB Master fetch error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=url
            )
    
    def parse_cb_csv(self, content: bytes, target_date: str = None) -> List[CbMasterItem]:
        """
        解析 CB Master CSV
        
        Args:
            content: CSV 原始內容（bytes）
            target_date: 目標日期
        
        Returns:
            CbMasterItem 列表
        """
        items = []
        
        try:
            raw_lines = BytesIO(content).read().decode(
                "big5", errors="ignore"
            ).splitlines()
            
            header_cols = []
            data_lines = []
            
            for line in raw_lines:
                if line.startswith("GLOSS,"):
                    header_cols = line[6:].split(",")
                elif line.startswith("TITLE") or line.startswith("DATADATE"):
                    continue
                elif line.startswith("DATA,"):
                    data_lines.append(line[5:])
                elif line.strip() == "":
                    continue
                elif "," in line and not line.startswith("DATA"):
                    data_lines.append(line)
            
            if not data_lines:
                logger.warning(f"CB Master: No data lines for {target_date}")
                return items
            
            clean_csv = StringIO("\n".join(data_lines))
            
            try:
                if header_cols:
                    df = pd.read_csv(clean_csv, header=None, names=header_cols)
                else:
                    df = pd.read_csv(clean_csv)
            except Exception as e:
                logger.error(f"CSV parse error: {e}")
                return items
            
            for _, row in df.iterrows():
                try:
                    item = self._row_to_item(row, target_date)
                    
                    if item and item.validate():
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"CB row parse error: {e}")
                    continue
            
            logger.info(f"CB Master {target_date}: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"CB Master CSV parse error: {e}")
        
        return items
    
    def _row_to_item(self, row: pd.Series, target_date: str = None) -> Optional[CbMasterItem]:
        """
        將 CSV 行轉換為 Item
        
        Args:
            row: pandas Series
            target_date: 目標日期
        
        Returns:
            CbMasterItem 或 None
        """
        try:
            cb_code = str(row.get("CB Code", "")).strip()
            cb_name = str(row.get("CB Name", "")).strip()
            underlying_stock = str(row.get("Stock Code", "")).strip()
            
            if not cb_code or cb_code == "nan":
                return None
            
            return CbMasterItem(
                cb_code=cb_code,
                cb_name=cb_name if cb_name != "nan" else "",
                underlying_stock=underlying_stock if underlying_stock != "nan" else "",
                market_type="TPEx",
                source_url=self.BASE_URL,
                source_type="tpex_cb"
            )
            
        except Exception as e:
            logger.debug(f"Row to item error: {e}")
            return None
    
    def fetch_all(self) -> Dict[str, Any]:
        """
        抓取所有日期的 CB Master
        
        Returns:
            結果字典
        """
        dates = self._generate_dates()
        results = {
            "dates": dates,
            "items_count": 0,
            "errors": []
        }
        
        for date in dates:
            response = self.fetch_cb_master(date)
            if response.success:
                results["items_count"] += len(self.items)
            else:
                results["errors"].append({"date": date, "error": response.error})
        
        return results
    
    def get_items(self) -> List[CbMasterItem]:
        """取得所有爬取的 Item"""
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計"""
        stats = super().get_statistics()
        stats.update({
            "total_items": len(self.items),
            "unique_cb_count": len(set(i.cb_code for i in self.items if i.cb_code)),
            "unique_stock_count": len(set(i.underlying_stock for i in self.items if i.underlying_stock)),
        })
        return stats
    
    def close(self):
        """關閉 Pipeline"""
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return (
            f"<CbMasterSpider "
            f"total={len(self.items)} "
            f"days_back={self.days_back}>"
        )


# ===== 命令列入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CbMasterSpider")
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="cb_master")
    
    spider = CbMasterSpider(pipeline=pipeline, days_back=args.days)
    
    results = spider.fetch_all()
    print(f"Results: {results}")
    print(f"Statistics: {spider.get_statistics()}")
    spider.close()
