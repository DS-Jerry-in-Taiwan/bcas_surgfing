# 全鏈路打通測試規範

## 1. 概述

本規範定義 `ExampleSpider` 必須完成的完整流程測試，驗證 Feapder 框架的可用性，確保從爬取、解析到入庫的全鏈路正確運作。

---

## 2. ExampleSpider 規格

### 2.1 功能需求

```
ExampleSpider 需實作一個完整的爬蟲流程：

1. 從 TWSE API 抓取股票日成交資料
2. 解析 JSON 回應為 StockDailyItem
3. 通過 CsvPipeline 寫入 CSV 檔案
4. 記錄完整統計並發送告警
```

### 2.2 目標網站

| 項目 | 值 |
|------|-----|
| URL | `https://www.twse.com.tw/exchangeReport/STOCK_DAY` |
| 方法 | GET |
| 參數 | `response=json`, `date={YYYY}{MM}01`, `stockNo={股票代碼}` |
| 範例股票 | 2330 (台積電) |

### 2.3 預期輸出

```csv
symbol,date,open_price,high_price,low_price,close_price,volume,turnover_rate,price_change,transaction_count
2330,2026-01,100.0,105.0,99.0,103.0,5000000,2.5,3.0,15000
```

---

## 3. 測試案例

### 3.1 測試矩陣

| 測試編號 | 測試名稱 | 前置條件 | 執行步驟 | 預期結果 |
|----------|----------|----------|----------|----------|
| TC-01 | 單筆爬取測試 | 無 | 爬取 2330 單月資料 | 取得 20+ 筆資料 |
| TC-02 | 多筆爬取測試 | 無 | 爬取 3 支股票單月資料 | 取得 60+ 筆資料 |
| TC-03 | CSV 寫入測試 | TC-01 | 執行爬取並寫入 | CSV 檔案存在且內容正確 |
| TC-04 | 去重測試 | TC-03 | 重複執行同一任務 | 資料不重複寫入 |
| TC-05 | 錯誤處理測試 | 無 | 爬取不存在的股票 | 錯誤被正確處理 |
| TC-06 | 統計追蹤測試 | TC-01 | 檢視統計資料 | request_count, error_count 正確 |
| TC-07 | 告警觸發測試 | Slack 已配置 | 觸發錯誤 | 收到 Slack 通知 |

### 3.2 詳細測試案例

#### TC-01: 單筆爬取測試

```python
# tests/test_framework/test_example_spider.py

def test_single_stock_crawl():
    """TC-01: 單筆爬取測試"""
    spider = ExampleSpider()
    
    # 執行爬取
    spider.fetch_stock("2330", 2026, 1)
    
    # 驗證
    assert spider.request_count > 0
    assert spider.success_count > 0
    
    # 驗證資料筆數
    items = spider.get_items()
    assert len(items) >= 20  # 一個月約 20 個交易日
```

#### TC-02: 多筆爬取測試

```python
def test_multi_stock_crawl():
    """TC-02: 多筆爬取測試"""
    spider = ExampleSpider()
    
    stocks = ["2330", "2317", "2454"]
    spider.batch_fetch(stocks, 2026, 1)
    
    # 驗證
    assert spider.request_count == 3
    items = spider.get_items()
    assert len(items) >= 60  # 3 支股票 × 20 個交易日
```

#### TC-03: CSV 寫入測試

```python
def test_csv_pipeline_write():
    """TC-03: CSV 寫入測試"""
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = CsvPipeline(output_dir=tmpdir, batch_size=10)
        spider = ExampleSpider(pipeline=pipeline)
        
        spider.fetch_stock("2330", 2026, 1)
        
        # 觸發寫入
        pipeline.flush_all()
        
        # 驗證檔案
        csv_path = os.path.join(tmpdir, "stock_daily.csv")
        assert os.path.exists(csv_path)
        
        # 驗證內容
        with open(csv_path, "r") as f:
            lines = f.readlines()
            assert len(lines) > 1  # 包含 header
            assert "2330" in f.read()
```

#### TC-04: 去重測試

```python
def test_deduplication():
    """TC-04: 去重測試"""
    spider = ExampleSpider()
    pipeline = MemoryPipeline()
    
    # 執行兩次相同的爬取
    spider.fetch_stock("2330", 2026, 1)
    spider.fetch_stock("2330", 2026, 1)
    
    # 收集 Item
    for item in spider.items:
        pipeline.save_items(item)
    
    # 驗證去重
    unique_keys = set()
    for item in pipeline.get_items():
        unique_keys.add(item.get_unique_key())
    
    # 由於兩次請求相同資料，去重後數量應與單次相同
    assert len(pipeline.get_items()) == len(unique_keys)
```

#### TC-05: 錯誤處理測試

```python
def test_error_handling():
    """TC-05: 錯誤處理測試"""
    spider = ExampleSpider()
    
    # 爬取不存在的股票
    result = spider.fetch_stock("INVALID", 2026, 1)
    
    # 驗證錯誤被正確處理
    assert result.success is False or result.data == []
    
    # 驗證錯誤計數
    assert spider.error_count > 0 or result.success is False
```

#### TC-06: 統計追蹤測試

```python
def test_statistics():
    """TC-06: 統計追蹤測試"""
    spider = ExampleSpider()
    
    spider.fetch_stock("2330", 2026, 1)
    
    stats = spider.get_statistics()
    
    # 驗證統計欄位
    assert "request_count" in stats
    assert "error_count" in stats
    assert "success_rate" in stats
    
    # 驗證數值合理性
    assert stats["request_count"] > 0
    assert 0 <= stats["success_rate"] <= 100
```

---

## 4. 實作程式碼

### 4.1 ExampleSpider

```python
# src/spiders/example_spider.py
"""
ExampleSpider - 全鏈路打通範例爬蟲

示範從爬取到入庫的完整流程
"""
from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from feapder import AirSpider, Request
import requests

from src.framework import BaseSpider, SpiderResponse
from src.framework.base_item import StockDailyItem
from src.framework.pipelines import CsvPipeline, MemoryPipeline
from src.framework.alerts import alert_manager, AlertLevel
from src.settings.feapder_settings import settings

logger = logging.getLogger(__name__)


class ExampleSpider(AirSpider, BaseSpider):
    """
    範例爬蟲
    
    功能：
    - 從 TWSE API 抓取股票日成交資料
    - 解析為 StockDailyItem
    - 寫入 CSV 檔案
    
    使用方式：
        spider = ExampleSpider()
        spider.fetch_stock("2330", 2026, 1)
        spider.start()
    """
    
    def __init__(
        self,
        pipeline=None,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        **kwargs
    ):
        # Feapder AirSpider 初始化
        super().__init__(
            thread_count=thread_count,
            redis_key=redis_key or settings.redis.key_prefix,
            **kwargs
        )
        
        # BaseSpider 配置
        self.proxy_enable = settings.proxy.enabled
        self.proxy_list = settings.proxy.proxy_list
        self.requests_interval = 1.0
        
        # Pipeline 配置
        self.pipeline = pipeline or CsvPipeline(output_dir="data/output")
        
        # 統計
        self.items: List[StockDailyItem] = []
        self.success_count: int = 0
        self.error_count: int = 0
        
        logger.info(f"ExampleSpider initialized: thread={thread_count}")
    
    def start_requests(self):
        """Feapder 入口"""
        # 生成請求任務
        stocks = ["2330", "2317", "2454"]
        year, month = 2026, 1
        
        for stock in stocks:
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            params = {
                "response": "json",
                "date": f"{year}{month:02d}01",
                "stockNo": stock
            }
            
            yield Request(
                url=url,
                params=params,
                callback=self.parse_stock_daily,
                request_kwargs={"stock": stock, "year": year, "month": month}
            )
    
    def parse_stock_daily(self, request, response):
        """解析股票日成交資料"""
        try:
            data = response.json
            
            if data.get("stat") != "OK":
                logger.warning(f"API returned error: {data.get('stat')}")
                self.error_count += 1
                return
            
            # 解析資料
            records = data.get("data", [])
            
            for record in records:
                try:
                    item = self._parse_record(record, request.stock)
                    if item and item.validate():
                        self.items.append(item)
                        self.pipeline.save_items(item)
                        self.success_count += 1
                except Exception as e:
                    logger.error(f"Failed to parse record: {e}")
                    self.error_count += 1
            
            logger.info(f"Parsed {len(records)} records for {request.stock}")
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            self.error_count += 1
            
            # 發送告警
            if settings.slack_alert.enabled:
                alert_manager.error(
                    title=f"ExampleSpider Parse Error",
                    message=f"Failed to parse response for {request.stock}",
                    spider_name=self.__class__.__name__,
                    request_url=str(request.url),
                    error_details=str(e)
                )
    
    def _parse_record(self, record: List[str], stock: str) -> Optional[StockDailyItem]:
        """解析單筆記錄"""
        try:
            # TWSE 格式: ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", ...]
            date_str = record[0]  # 民國年
            open_price = self._parse_price(record[3])
            high_price = self._parse_price(record[4])
            low_price = self._parse_price(record[5])
            close_price = self._parse_price(record[6])
            volume = int(record[1].replace(",", ""))
            
            return StockDailyItem(
                symbol=stock,
                date=self._convert_date(date_str),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                source_url="https://www.twse.com.tw",
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
    
    def _convert_date(self, minguo_date: str) -> str:
        """民國年轉西元年"""
        try:
            parts = minguo_date.split("/")
            year = int(parts[0]) + 1911
            month = parts[1]
            day = parts[2]
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
    
    def on_exception(self, exception: Exception, request: Request = None):
        """處理例外"""
        self.error_count += 1
        
        # 發送告警
        if settings.slack_alert.enabled:
            alert_manager.error(
                title=f"ExampleSpider Exception",
                message=str(exception),
                spider_name=self.__class__.__name__,
                request_url=str(request.url) if request else "",
                error_details=traceback.format_exc()
            )
        
        return super().on_exception(exception, request)
    
    def end_callback(self):
        """完成回調"""
        logger.info(f"Spider completed: {self.get_statistics()}")
        
        # 關閉 Pipeline
        if self.pipeline:
            self.pipeline.close()
        
        # 發送完成通知
        if settings.slack_alert.enabled:
            alert_manager.info(
                title=f"ExampleSpider Completed",
                message=f"Fetched {len(self.items)} items",
                spider_name=self.__class__.__name__,
                metadata=self.get_statistics()
            )
        
        return super().end_callback()
    
    # ===== 手動呼叫方法 =====
    
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
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
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
            
            return self.parse_response(response)
            
        except Exception as e:
            return SpiderResponse(success=False, error=str(e))
    
    def batch_fetch(self, stocks: List[str], year: int, month: int):
        """批次抓取多支股票"""
        for stock in stocks:
            self.fetch_stock(stock, year, month)


# ===== 命令列入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ExampleSpider")
    parser.add_argument("--stock", default="2330", help="Stock code")
    parser.add_argument("--year", type=int, default=2026, help="Year")
    parser.add_argument("--month", type=int, default=1, help="Month")
    parser.add_argument("--output", default="data/output", help="Output directory")
    
    args = parser.parse_args()
    
    # 建立 Pipeline
    pipeline = CsvPipeline(output_dir=args.output)
    
    # 建立爬蟲
    spider = ExampleSpider(pipeline=pipeline)
    
    # 執行爬取
    response = spider.fetch_stock(args.stock, args.year, args.month)
    
    if response.success:
        print(f"Success: {len(spider.get_items())} items fetched")
        pipeline.flush_all()
    else:
        print(f"Error: {response.error}")
    
    # 顯示統計
    print(f"Statistics: {spider.get_statistics()}")
```

---

## 5. 測試執行

### 5.1 執行命令

```bash
# 單筆測試
python -m tests.test_framework.test_example_spider::test_single_stock_crawl

# 多筆測試
python -m tests.test_framework.test_example_spider::test_multi_stock_crawl

# CSV 寫入測試
python -m tests.test_framework.test_example_spider::test_csv_pipeline_write

# 去重測試
python -m tests.test_framework.test_example_spider::test_deduplication

# 錯誤處理測試
python -m tests.test_framework.test_example_spider::test_error_handling

# 統計追蹤測試
python -m tests.test_framework.test_example_spider::test_statistics

# 所有測試
python -m pytest tests/test_framework/test_example_spider.py -v
```

### 5.2 預期輸出

```
tests/test_framework/test_example_spider.py::test_single_stock_crawl PASSED
tests/test_framework/test_example_spider.py::test_multi_stock_crawl PASSED
tests/test_framework/test_example_spider.py::test_csv_pipeline_write PASSED
tests/test_framework/test_example_spider.py::test_deduplication PASSED
tests/test_framework/test_example_spider.py::test_error_handling PASSED
tests/test_framework/test_example_spider.py::test_statistics PASSED

6 passed in 15.23s
```

---

## 6. 驗證清單

- [ ] ExampleSpider 可成功抓取 TWSE 資料
- [ ] 解析正確轉換民國年為西元年
- [ ] StockDailyItem 驗證通過
- [ ] CsvPipeline 正確寫入 CSV
- [ ] 去重邏輯正確運作
- [ ] 錯誤處理不中斷程式
- [ ] 統計追蹤正確記錄
- [ ] 所有單元測試通過
- [ ] 全鏈路整合測試通過

---

## 7. 成功標準

當以下條件全部滿足時，視為 Phase 1 打通測試完成：

```
1. 7/7 測試案例全部通過
2. CSV 輸出檔案內容正確
3. 統計數值合理
4. 無未處理的例外
5. (可選) Slack 告警成功發送
```

---

*文件版本：1.0.0*
*建立時間：2026-04-15*
