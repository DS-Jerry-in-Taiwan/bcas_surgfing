"""
BatchSpider - 批次爬蟲

功能：
- 全市場歷史資料補檔
- 斷點續傳
- 並發控制
"""
from __future__ import annotations

import logging
import time
from typing import List, Dict, Any, Type, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from src.framework.base_spider import BaseSpider, SpiderResponse
from src.spiders.checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class BatchSpider:
    """
    批次爬蟲
    
    用於大規模歷史資料補檔，支援斷點續傳和並發控制。
    
    Attributes:
        spider_class: 要使用的 Spider 類別
        pipeline: 資料寫入管道
        checkpoint: 斷點管理器
        max_workers: 最大並發數
        request_interval: 請求間隔（秒）
    """
    
    def __init__(
        self,
        spider_class: Type[BaseSpider],
        pipeline=None,
        checkpoint_file: Optional[str] = None,
        max_workers: int = 4,
        request_interval: float = 1.0,
        max_retries: int = 3
    ):
        """
        初始化 BatchSpider
        
        Args:
            spider_class: Spider 類別
            pipeline: Pipeline 實例
            checkpoint_file: 斷點檔案路徑
            max_workers: 最大並發數
            request_interval: 請求間隔
            max_retries: 最大重試次數
        """
        self.spider_class = spider_class
        self.pipeline = pipeline
        self.max_workers = max_workers
        self.request_interval = request_interval
        self.max_retries = max_retries
        
        self.checkpoint: Optional[CheckpointManager] = None
        if checkpoint_file:
            self.checkpoint = CheckpointManager(checkpoint_file)
        
        self.results: List[Dict[str, Any]] = []
        self._spider_cache: Dict[str, BaseSpider] = {}
        
        logger.info(f"BatchSpider initialized: max_workers={max_workers}")
    
    def _get_spider(self) -> BaseSpider:
        """取得或建立 Spider 實例"""
        spider_key = "default"
        if spider_key not in self._spider_cache:
            self._spider_cache[spider_key] = self.spider_class(pipeline=self.pipeline)
        return self._spider_cache[spider_key]
    
    def _generate_keys(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> List[str]:
        """
        生成所有需要處理的 key
        
        Args:
            symbols: 股票代號清單
            start_date: 開始日期
            end_date: 結束日期
        
        Returns:
            key 清單
        """
        from src.spiders.stock_daily_spider import StockDailySpider
        from src.spiders.tpex_cb_daily_spider import TpexCbDailySpider
        
        keys = []
        spider_class_name = self.spider_class.__name__
        
        if spider_class_name == "StockDailySpider":
            spider = StockDailySpider()
            months = spider._generate_months_in_range(start_date, end_date)
            for symbol in symbols:
                for year, month in months:
                    key = f"{symbol}_{year}_{month:02d}"
                    keys.append(key)
        
        elif spider_class_name == "TpexCbDailySpider":
            from src.spiders.tpex_cb_daily_spider import TpexCbDailySpider
            spider = TpexCbDailySpider()
            dates = spider._generate_dates_in_range(start_date, end_date)
            for date in dates:
                key = f"daily_{date}"
                keys.append(key)
        
        else:
            for symbol in symbols:
                key = f"{symbol}_{start_date}_{end_date}"
                keys.append(key)
        
        return keys
    
    def _parse_key(self, key: str) -> Dict[str, Any]:
        """解析 key"""
        parts = key.split("_")
        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            return {
                "symbol": parts[0],
                "year": int(parts[-2]),
                "month": int(parts[-1])
            }
        elif key.startswith("daily_"):
            return {"date": key.replace("daily_", "")}
        return {"key": key}
    
    def _fetch_single(self, key: str) -> Dict[str, Any]:
        """
        抓取單一 key
        
        Args:
            key: 任務 key
        
        Returns:
            結果字典
        """
        spider = self._get_spider()
        parsed = self._parse_key(key)
        
        try:
            if "symbol" in parsed and "year" in parsed:
                response = spider.fetch_daily(
                    parsed["symbol"],
                    parsed["year"],
                    parsed["month"]
                )
                result = {
                    "key": key,
                    "success": response.success,
                    "count": response.data.get("count", 0) if response.data else 0,
                    "error": response.error
                }
            elif "date" in parsed:
                response = spider.fetch_daily(parsed["date"])
                result = {
                    "key": key,
                    "success": response.success,
                    "count": response.data.get("count", 0) if response.data else 0,
                    "error": response.error
                }
            else:
                result = {"key": key, "success": False, "error": "Unknown key format"}
            
            if result["success"]:
                self.checkpoint.mark_completed(key, {"count": result["count"]})
            else:
                self.checkpoint.mark_failed(key, result["error"] or "Unknown error")
            
            return result
            
        except Exception as e:
            logger.error(f"Fetch error for {key}: {e}")
            self.checkpoint.mark_failed(key, str(e))
            return {"key": key, "success": False, "error": str(e)}
    
    def backfill(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        批次補檔
        
        Args:
            symbols: 股票代號清單
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            resume: 是否從斷點續傳
        
        Returns:
            批次結果字典
        """
        keys = self._generate_keys(symbols, start_date, end_date)
        
        if self.checkpoint:
            if resume:
                pending_keys = self.checkpoint.get_pending(keys)
                logger.info(f"Resuming: {len(pending_keys)} pending of {len(keys)}")
            else:
                self.checkpoint.reset()
                self.checkpoint.set_total(len(keys))
                pending_keys = keys
            
            self.checkpoint.set_status("running")
        else:
            pending_keys = keys
        
        start_time = datetime.now()
        results = {"success": 0, "failed": 0, "errors": []}
        
        logger.info(f"Starting backfill: {len(pending_keys)} keys, max_workers={self.max_workers}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._fetch_single, key): key for key in pending_keys}
            
            for i, future in enumerate(as_completed(futures)):
                key = futures[future]
                
                try:
                    result = future.result()
                    if result["success"]:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                        if result.get("error"):
                            results["errors"].append({"key": key, "error": result["error"]})
                    
                    self.results.append(result)
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"Progress: {i + 1}/{len(pending_keys)}")
                    
                    if self.checkpoint and (i + 1) % 5 == 0:
                        self.checkpoint.save()
                    
                except Exception as e:
                    logger.error(f"Future error for {key}: {e}")
                    results["failed"] += 1
                    results["errors"].append({"key": key, "error": str(e)})
                
                time.sleep(self.request_interval)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if self.checkpoint:
            self.checkpoint.set_status("completed" if results["failed"] == 0 else "partial")
            self.checkpoint.save()
        
        final_results = {
            **results,
            "total": len(pending_keys),
            "duration_seconds": duration,
            "keys_per_second": len(pending_keys) / duration if duration > 0 else 0
        }
        
        logger.info(f"Backfill completed: {final_results}")
        return final_results
    
    def get_progress(self) -> Dict[str, Any]:
        """取得進度"""
        if self.checkpoint:
            return self.checkpoint.get_progress()
        return {"total": 0, "completed": 0, "failed": 0, "pending": 0}
    
    def close(self):
        """關閉資源"""
        if self.checkpoint:
            self.checkpoint.save()
        
        for spider in self._spider_cache.values():
            spider.close()
        
        if self.pipeline:
            self.pipeline.close()
    
    def __repr__(self) -> str:
        return f"<BatchSpider spider={self.spider_class.__name__} max_workers={self.max_workers}>"


if __name__ == "__main__":
    import argparse
    
    from src.spiders.stock_daily_spider import StockDailySpider
    from src.spiders.tpex_cb_daily_spider import TpexCbDailySpider
    from src.framework.pipelines import CsvPipeline
    
    parser = argparse.ArgumentParser(description="BatchSpider")
    parser.add_argument("--spider", choices=["stock_daily", "tpex_cb_daily"], required=True)
    parser.add_argument("--symbols", help="Comma-separated symbols")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--checkpoint", help="Checkpoint file path")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", default="csv")
    args = parser.parse_args()
    
    if args.spider == "stock_daily":
        spider_class = StockDailySpider
    else:
        spider_class = TpexCbDailySpider
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = None
    
    batch = BatchSpider(
        spider_class=spider_class,
        pipeline=pipeline,
        checkpoint_file=args.checkpoint,
        max_workers=args.workers
    )
    
    symbols = args.symbols.split(",") if args.symbols else []
    
    if args.start and args.end:
        results = batch.backfill(symbols, args.start, args.end, resume=args.resume)
    else:
        results = {"error": "Must specify --start and --end"}
    
    print(f"Results: {results}")
    print(f"Progress: {batch.get_progress()}")
    
    batch.close()
