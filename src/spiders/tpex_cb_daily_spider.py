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
from src.configs.csv_templates import CB_DAILY_TPEX

logger = logging.getLogger(__name__)


class TpexCbDailySpider(BaseSpider):
    """
    TPEx 可轉債日行情爬蟲
    
    從 TPEx 下載可轉債日行情 CSV
    
    Attributes:
        BASE_URL: TPEx CB CSV 儲存路徑
        CSV_CONFIG: CSV 格式設定（可抽換）
        pipeline: 資料寫入管道
        items: 已抓取的 CB 行情列表
    """
    
    BASE_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
    CSV_CONFIG = CB_DAILY_TPEX
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            thread_count=thread_count,
            redis_key=redis_key,
            **kwargs
        )
        
        self.pipeline = pipeline or CsvPipeline(table_name="tpex_cb_daily")
        self.items: List[TpexCbDailyItem] = []
        
        logger.info("TpexCbDailySpider initialized")
    
    def _build_url(self, date: str) -> str:
        """
        建立 CSV 下載 URL
        
        Args:
            date: YYYYMMDD 格式
        
        Returns:
            完整下載 URL
        """
        year = date[:4]
        year_month = date[:6]
        return f"{self.BASE_URL}/{year}/{year_month}/RSta0113.{date}-C.csv"
    
    def _parse_number(self, value) -> float:
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
        url_date = date.replace("-", "")
        url = self._build_url(url_date)
        
        try:
            logger.info(f"Fetching TPEx CB Daily: {date}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.warning(f"TPEx CB Daily download failed: {response.status_code}")
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TPEx CB fetch error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=url
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self.record_request(success=False)
            return SpiderResponse(
                success=False,
                error=str(e),
                url=url
            )
    
    def parse_cb_csv(self, content: bytes, target_date: str) -> List[TpexCbDailyItem]:
        """
        解析 TPEx CB CSV（依 CSV_CONFIG）
        
        Args:
            content: CSV 原始內容
            target_date: 目標日期
        
        Returns:
            TpexCbDailyItem 列表
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
            
            for line in raw_lines:
                if any(line.startswith(p) for p in cfg.skip_prefixes):
                    continue
                
                matched = False
                for prefix in cfg.header_prefixes:
                    if line.startswith(prefix):
                        h = line[len(prefix):]
                        header_cols = [c.strip(cfg.quote_char).strip() for c in next(csv_lib.reader([h]))]
                        matched = True
                        break
                if matched:
                    continue
                
                for prefix in cfg.body_prefixes:
                    if line.startswith(prefix):
                        data_lines.append(line[len(prefix):])
                        matched = True
                        break
                if matched:
                    continue
                
                if line.strip() == "":
                    continue
                if cfg.delimiter in line:
                    data_lines.append(line)
            
            if not data_lines:
                logger.warning(f"TPEx CB Daily {target_date}: No data lines")
                return items
            
            reader = csv_lib.reader(data_lines)
            rows = [r for r in reader]
            import pandas as pd
            df = pd.DataFrame(rows)
            
            if header_cols and len(header_cols) == df.shape[1]:
                df.columns = header_cols
            else:
                logger.warning(f"TPEx CB Daily: header/data column mismatch ({len(header_cols)} vs {df.shape[1]})")
            
            for _, row in df.iterrows():
                try:
                    mapped = {}
                    for csv_col, field_name in cfg.column_mapping.items():
                        val = str(row.get(csv_col, "")).strip().strip(cfg.quote_char)
                        mapped[field_name] = val if val and val != "nan" else ""
                    
                    for f, default_val in cfg.defaults.items():
                        if f not in mapped or not mapped[f]:
                            mapped[f] = default_val
                    
                    cb_code_val = mapped.get("cb_code", "")
                    if not cb_code_val or cb_code_val in ("合計", "GLOSS"):
                        continue
                    
                    item = TpexCbDailyItem(
                        cb_code=cb_code_val,
                        cb_name=mapped.get("cb_name", ""),
                        underlying_stock=mapped.get("underlying_stock", ""),
                        trade_date=target_date,
                        closing_price=self._parse_number(mapped.get("closing_price", 0)),
                        volume=self._parse_number(mapped.get("volume", 0)),
                        turnover_rate=self._parse_number(mapped.get("turnover_rate", 0)),
                        premium_rate=self._parse_number(mapped.get("premium_rate", 0)),
                        conversion_price=self._parse_number(mapped.get("conversion_price", 0)),
                        remaining_balance=self._parse_number(mapped.get("remaining_balance", 0)),
                        source_url=self.BASE_URL,
                        source_type="tpex_cb_daily"
                    )
                    
                    if item.validate():
                        items.append(item)
                        
                except Exception as e:
                    logger.debug(f"CB row parse error: {e}")
                    continue
            
            logger.info(f"TPEx CB Daily {target_date}: Parsed {len(items)} items")
            
        except Exception as e:
            logger.error(f"TPEx CB Daily CSV parse error: {e}")
        
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
