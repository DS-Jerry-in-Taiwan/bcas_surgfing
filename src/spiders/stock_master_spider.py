"""
StockMasterSpider - 股票主檔爬蟲

功能：
- 抓取 TWSE 上市股票主檔
- 抓取 TPEx 上櫃股票主檔
- 存入 PostgreSQL 或 CSV

使用方式：
    spider = StockMasterSpider()
    spider.start()
"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import StockMasterItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline

logger = logging.getLogger(__name__)


class StockMasterSpider(BaseSpider):
    """
    股票主檔爬蟲
    
    支援 TWSE 和 TPEx 兩個市場的股票主檔資料抓取
    
    Attributes:
        TWSE_URL: TWSE ISIN 頁面 URL
        TPEX_URL: TPEx ISIN 頁面 URL
        pipeline: 資料寫入管道
        items: 已抓取的股票列表
    """
    
    TWSE_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    TPEX_URL = "https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4"
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 StockMasterSpider
        
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
        
        self.pipeline = pipeline or CsvPipeline(table_name="stock_master")
        self.items: List[StockMasterItem] = []
        self.twse_items: List[StockMasterItem] = []
        self.tpex_items: List[StockMasterItem] = []
        
        logger.info("StockMasterSpider initialized")
    
    def fetch_twse(self) -> SpiderResponse:
        """
        抓取 TWSE 股票主檔
        
        Returns:
            SpiderResponse
        """
        try:
            logger.info(f"Fetching TWSE from {self.TWSE_URL}")
            
            response = requests.get(
                self.TWSE_URL,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"TWSE fetch failed: HTTP {response.status_code}")
                self.record_request(success=False)
                return SpiderResponse(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    url=self.TWSE_URL
                )
            
            response.encoding = "big5"
            
            items = self.parse_twse_html(response.text)
            self.twse_items.extend(items)
            self.items.extend(items)
            
            for item in items:
                self.add_item(item)
            
            self.record_request(success=True)
            
            return SpiderResponse(
                success=True,
                data={"count": len(items)},
                url=self.TWSE_URL,
                metadata={"market": "TWSE"}
            )
            
        except Exception as e:
            logger.error(f"TWSE fetch error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=self.TWSE_URL
            )
    
    def fetch_tpex(self) -> SpiderResponse:
        """
        抓取 TPEx 股票主檔
        
        Returns:
            SpiderResponse
        """
        try:
            logger.info(f"Fetching TPEx from {self.TPEX_URL}")
            
            response = requests.get(
                self.TPEX_URL,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"TPEx fetch failed: HTTP {response.status_code}")
                self.record_request(success=False)
                return SpiderResponse(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    url=self.TPEX_URL
                )
            
            response.encoding = "utf-8"
            
            items = self.parse_tpex_html(response.text)
            self.tpex_items.extend(items)
            self.items.extend(items)
            
            for item in items:
                self.add_item(item)
            
            self.record_request(success=True)
            
            return SpiderResponse(
                success=True,
                data={"count": len(items)},
                url=self.TPEX_URL,
                metadata={"market": "TPEx"}
            )
            
        except Exception as e:
            logger.error(f"TPEx fetch error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=self.TPEX_URL
            )
    
    def parse_twse_html(self, html_content: str) -> List[StockMasterItem]:
        """
        解析 TWSE HTML
        
        Args:
            html_content: HTML 內容
        
        Returns:
            StockMasterItem 列表
        """
        items = []
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            tables = soup.find_all("table")
            
            table = None
            for tbl in tables:
                header_row = tbl.find("tr")
                if header_row:
                    header_cells = header_row.find_all(["th", "td"])
                    header_text = " ".join(c.get_text(strip=True) for c in header_cells)
                    if "代號" in header_text and "名稱" in header_text:
                        table = tbl
                        break
            
            if not table:
                logger.warning("TWSE: No table with expected header found")
                return items
            
            rows = table.find_all("tr")
            
            if len(rows) < 2:
                return items
            
            header = rows[0]
            header_cols = [c.get_text(strip=True) for c in header.find_all(["th", "td"])]
            
            symbol_name_col = None
            for i, col in enumerate(header_cols):
                if "代號" in col and "名稱" in col:
                    symbol_name_col = i
                    break
            
            if symbol_name_col is None:
                for i, col in enumerate(header_cols):
                    if "有價證券代號及名稱" in col or "有價證券代號" in col:
                        symbol_name_col = i
                        break
            
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) <= symbol_name_col:
                    continue
                
                try:
                    symbol_name_text = cols[symbol_name_col].get_text(strip=True)
                    
                    if not symbol_name_text or "　" not in symbol_name_text:
                        continue
                    
                    parts = symbol_name_text.split("　")
                    if len(parts) < 2:
                        continue
                    
                    symbol = parts[0].strip()
                    name = parts[1].strip()
                    
                    if not symbol:
                        continue
                    
                    item = StockMasterItem(
                        symbol=symbol,
                        name=name,
                        market_type="TWSE",
                        source_url=self.TWSE_URL,
                        source_type="twse"
                    )
                    
                    if item.validate():
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"TWSE row parse error: {e}")
                    continue
            
            logger.info(f"TWSE: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"TWSE HTML parse error: {e}")
        
        return items
    
    def parse_tpex_html(self, html_content: str) -> List[StockMasterItem]:
        """
        解析 TPEx HTML
        
        Args:
            html_content: HTML 內容
        
        Returns:
            StockMasterItem 列表
        """
        items = []
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            table = soup.find("table")
            
            if not table:
                logger.warning("TPEx: No table found")
                return items
            
            rows = table.find_all("tr")
            
            if len(rows) < 2:
                return items
            
            header = rows[0]
            header_cols = [th.get_text(strip=True) for th in header.find_all("th")]
            
            symbol_name_col = None
            for i, col in enumerate(header_cols):
                if "代號" in col and "名稱" in col:
                    symbol_name_col = i
                    break
            
            if symbol_name_col is None:
                for i, col in enumerate(header_cols):
                    if "有價證券代號及名稱" in col or "有價證券代號" in col:
                        symbol_name_col = i
                        break
            
            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) <= symbol_name_col:
                    continue
                
                try:
                    symbol_name_text = cols[symbol_name_col].get_text(strip=True)
                    
                    if not symbol_name_text or "　" not in symbol_name_text:
                        continue
                    
                    parts = symbol_name_text.split("　")
                    if len(parts) < 2:
                        continue
                    
                    symbol = parts[0].strip()
                    name = parts[1].strip()
                    
                    if not symbol:
                        continue
                    
                    item = StockMasterItem(
                        symbol=symbol,
                        name=name,
                        market_type="TPEx",
                        source_url=self.TPEX_URL,
                        source_type="tpex"
                    )
                    
                    if item.validate():
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"TPEx row parse error: {e}")
                    continue
            
            logger.info(f"TPEx: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"TPEx HTML parse error: {e}")
        
        return items
    
    def fetch_all(self) -> Dict[str, Any]:
        """
        抓取所有市場的股票主檔
        
        Returns:
            包含 TWSE 和 TPEx 結果的字典
        """
        results = {
            "twse": self.fetch_twse(),
            "tpex": self.fetch_tpex()
        }
        
        return results
    
    def get_items(self) -> List[StockMasterItem]:
        """取得所有爬取的 Item"""
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得統計"""
        stats = super().get_statistics()
        stats.update({
            "total_items": len(self.items),
            "twse_count": len(self.twse_items),
            "tpex_count": len(self.tpex_items),
        })
        return stats
    
    def close(self):
        """關閉 Pipeline"""
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return (
            f"<StockMasterSpider "
            f"twse={len(self.twse_items)} "
            f"tpex={len(self.tpex_items)} "
            f"total={len(self.items)}>"
        )


# ===== 命令列入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="StockMasterSpider")
    parser.add_argument("--market", default="all", choices=["twse", "tpex", "all"])
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="stock_master")
    
    spider = StockMasterSpider(pipeline=pipeline)
    
    if args.market in ["twse", "all"]:
        spider.fetch_twse()
    
    if args.market in ["tpex", "all"]:
        spider.fetch_tpex()
    
    print(f"Statistics: {spider.get_statistics()}")
    spider.close()
