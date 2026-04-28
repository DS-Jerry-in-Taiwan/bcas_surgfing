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
from src.configs.csv_templates import CB_MASTER_TPEX

logger = logging.getLogger(__name__)


class CbMasterSpider(BaseSpider):
    """
    可轉債主檔爬蟲
    
    從 TPEx 下載可轉債主檔 CSV
    
    Attributes:
        BASE_URL: TPEx CB CSV 基本 URL
        CSV_CONFIG: CSV 格式設定（可抽換以因應格式變更）
        pipeline: 資料寫入管道
        items: 已抓取的 CB 列表
        days_back: 回查天數
    """
    
    BASE_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
    
    CSV_CONFIG = CB_MASTER_TPEX
    
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
        cfg = self.CSV_CONFIG
        
        try:
            import csv as csv_lib
            raw_lines = BytesIO(content).read().decode(
                cfg.encoding, errors="ignore"
            ).splitlines()
            
            header_cols = []
            data_lines = []
            header_found = False
            
            for line in raw_lines:
                if any(line.startswith(p) for p in cfg.skip_prefixes):
                    continue
                
                matched_prefix = None
                if not header_found:
                    for prefix in cfg.header_prefixes:
                        if line.startswith(prefix):
                            csv_header = line[len(prefix):]
                            header_cols = [h.strip(cfg.quote_char).strip() for h in next(csv_lib.reader([csv_header]))]
                            header_found = True
                            matched_prefix = prefix
                            break
                if matched_prefix:
                    continue
                
                matched_prefix = None
                for prefix in cfg.body_prefixes:
                    if line.startswith(prefix):
                        body = line[len(prefix):]
                        data_lines.append(body)
                        matched_prefix = prefix
                        break
                if matched_prefix:
                    continue
                
                if line.strip() == "":
                    continue
                if cfg.delimiter in line:
                    data_lines.append(line)
            
            if not data_lines:
                logger.warning(f"CB Master: No data lines for {target_date}")
                return items
            
            reader = csv_lib.reader(data_lines)
            rows = [r for r in reader]
            import pandas as pd
            df = pd.DataFrame(rows)
            
            if header_cols and len(header_cols) == df.shape[1]:
                df.columns = header_cols
            else:
                logger.warning(f"CB Master: header/data column mismatch ({len(header_cols)} vs {df.shape[1]}), using default names")
            
            for _, row in df.iterrows():
                try:
                    item = self._row_to_item(row, target_date)
                    if item is not None:
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
        將 CSV 行轉換為 Item（依 CSV_CONFIG 的 column_mapping）
        
        Args:
            row: pandas Series
            target_date: 目標日期
        
        Returns:
            CbMasterItem 或 None
        """
        cfg = self.CSV_CONFIG
        
        try:
            mapped = {}
            for csv_col, field_name in cfg.column_mapping.items():
                val = str(row.get(csv_col, "")).strip().strip(cfg.quote_char)
                mapped[field_name] = val if val and val != "nan" else ""
            
            for f, default_val in cfg.defaults.items():
                if f not in mapped or not mapped[f]:
                    mapped[f] = default_val
            
            for req in cfg.required_fields:
                if not mapped.get(req):
                    return None
            
            return CbMasterItem(
                cb_code=mapped.get("cb_code", ""),
                cb_name=mapped.get("cb_name", ""),
                underlying_stock=mapped.get("underlying_stock", ""),
                issue_date=mapped.get("issue_date", ""),
                maturity_date=mapped.get("maturity_date", ""),
                conversion_price=mapped.get("conversion_price", ""),
                market_type=mapped.get("market_type", "TPEx"),
                source_url=self.BASE_URL,
                source_type=mapped.get("source_type", "tpex_cb"),
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
