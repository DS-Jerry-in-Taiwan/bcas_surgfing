# Developer Prompt - Phase 2 Master 爬蟲遷移

## 概述

本 Prompt 定義 Phase 2 的實作工作，Developer Agent 需完成股票主檔與可轉債主檔爬蟲的 Feapder 框架遷移。

---

## 1. 參考文件

| 文件 | 路徑 | 用途 |
|------|------|------|
| 實作計畫 | `docs/agent_context/spider_migration_plan/phase_2_master_migration/implementation_plan.md` | 實作步驟 |
| 測試案例 | `docs/agent_context/spider_migration_plan/phase_2_master_migration/test_cases.md` | 測試定義 |
| 現有爬蟲 | `src/crawlers/master/cb_master.py` | CB Master 原始碼 |
| 現有爬蟲 | `src/crawlers/master/stock_crawler.py` | 股票主檔原始碼 |
| Phase 1 框架 | `src/framework/base_spider.py` | BaseSpider |
| Phase 1 Item | `src/framework/base_item.py` | StockMasterItem, CbMasterItem |
| Phase 1 Pipeline | `src/framework/pipelines.py` | PostgresPipeline |

---

## 2. 實作清單

### 2.1 新建目錄結構

```
src/spiders/
├── __init__.py                    # 更新匯出
├── stock_master_spider.py        # 【新建】
└── cb_master_spider.py           # 【新建】

tests/test_framework/
├── test_master_spider.py         # 【新建】
└── __init__.py
```

### 2.2 StockMasterSpider (`src/spiders/stock_master_spider.py`)

```python
"""
StockMasterSpider - 股票主檔爬蟲

功能：
- 抓取 TWSE 上市股票主檔
- 抓取 TPEx 上櫃股票主檔
- 存入 PostgreSQL

使用方式：
    spider = StockMasterSpider()
    spider.start()
"""
from feapder import AirSpider, Request
from src.framework.base_spider import BaseSpider
from src.framework.base_item import StockMasterItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class StockMasterSpider(AirSpider, BaseSpider):
    """股票主檔爬蟲"""
    
    TWSE_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    TPEX_URL = "https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4"
    
    def __init__(self, pipeline=None, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline or CsvPipeline(table_name="stock_master")
        self.items = []
    
    def start_requests(self):
        """生成爬取任務"""
        yield Request(self.TWSE_URL, callback=self.parse_twse)
        yield Request(self.TPEX_URL, callback=self.parse_tpex)
    
    def parse_twse(self, request, response):
        """解析 TWSE 主檔"""
        try:
            response.encoding = "big5"
            dfs = pd.read_html(response.text, encoding="big5")
            df = dfs[0]
            
            # 欄位處理
            df.columns = df.iloc[0]
            df = df[1:]
            
            col_name = [c for c in df.columns if "代號" in str(c) and "名稱" in str(c)][0]
            df = df[df[col_name].notnull()]
            df = df[df[col_name].str.contains("　")]
            
            for _, row in df.iterrows():
                try:
                    symbol_name = str(row[col_name])
                    symbol = symbol_name.split("　")[0].strip()
                    name = symbol_name.split("　")[1].strip() if "　" in symbol_name else ""
                    
                    item = StockMasterItem(
                        symbol=symbol,
                        name=name,
                        market_type="TWSE",
                        source_url=self.TWSE_URL,
                        source_type="twse"
                    )
                    
                    if item.validate():
                        self.items.append(item)
                        self.pipeline.save_items(item)
                        
                except Exception as e:
                    logger.error(f"TWSE row parse error: {e}")
                    continue
            
            logger.info(f"TWSE: Parsed {len(self.items)} items")
            
        except Exception as e:
            logger.error(f"TWSE parse error: {e}")
    
    def parse_tpex(self, request, response):
        """解析 TPEx 主檔"""
        try:
            dfs = pd.read_html(response.text)
            df = dfs[0]
            
            df.columns = df.iloc[0]
            df = df[1:]
            df = df[df["有價證券代號及名稱"].notnull()]
            df = df[df["有價證券代號及名稱"].str.contains("　")]
            
            for _, row in df.iterrows():
                try:
                    symbol_name = str(row["有價證券代號及名稱"])
                    symbol = symbol_name.split("　")[0].strip()
                    name = symbol_name.split("　")[1].strip() if "　" in symbol_name else ""
                    
                    item = StockMasterItem(
                        symbol=symbol,
                        name=name,
                        market_type="TPEx",
                        source_url=self.TPEX_URL,
                        source_type="tpex"
                    )
                    
                    if item.validate():
                        self.items.append(item)
                        self.pipeline.save_items(item)
                        
                except Exception as e:
                    logger.error(f"TPEx row parse error: {e}")
                    continue
            
            logger.info(f"TPEx: Parsed {len(self.items)} items")
            
        except Exception as e:
            logger.error(f"TPEx parse error: {e}")
    
    def get_statistics(self):
        """取得統計"""
        return {
            "total_items": len(self.items),
            "twse_count": len([i for i in self.items if i.market_type == "TWSE"]),
            "tpex_count": len([i for i in self.items if i.market_type == "TPEx"]),
        }


# ===== 命令列入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="stock_master")
    
    spider = StockMasterSpider(pipeline=pipeline)
    spider.start()
    
    print(f"Statistics: {spider.get_statistics()}")
    spider.pipeline.close()
```

### 2.3 CbMasterSpider (`src/spiders/cb_master_spider.py`)

```python
"""
CbMasterSpider - 可轉債主檔爬蟲

功能：
- 下載 TPEx CB Master CSV
- Big5 編碼處理
- 存入 PostgreSQL

使用方式：
    spider = CbMasterSpider()
    spider.start()
"""
from feapder import AirSpider, Request
from src.framework.base_spider import BaseSpider
from src.framework.base_item import CbMasterItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline
from io import BytesIO, StringIO
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CbMasterSpider(AirSpider, BaseSpider):
    """可轉債主檔爬蟲"""
    
    BASE_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
    
    def __init__(self, pipeline=None, days_back=30, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline or CsvPipeline(table_name="cb_master")
        self.items = []
        self.days_back = days_back
    
    def start_requests(self):
        """生成爬取任務"""
        dates = self._generate_dates()
        
        for date in dates:
            year = date[:4]
            year_month = date[:6]
            url = f"{self.BASE_URL}/{year}/{year_month}/RSdrs001.{date}-C.csv"
            
            yield Request(
                url,
                callback=self.parse_cb_master,
                request_kwargs={"target_date": date}
            )
    
    def _generate_dates(self):
        """生成近期的日期列表"""
        dates = []
        today = datetime.now()
        
        for i in range(self.days_back):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            dates.append(date_str)
        
        return dates
    
    def parse_cb_master(self, request, response):
        """解析 CB Master CSV"""
        try:
            target_date = request.request_kwargs.get("target_date", "")
            
            # Big5 解碼並過濾標題行
            raw_lines = BytesIO(response.content).read().decode(
                "big5", errors="ignore"
            ).splitlines()
            
            data_lines = [
                line for line in raw_lines
                if not (line.startswith("TITLE") or 
                        line.startswith("DATADATE") or 
                        line.startswith("GLOSS"))
            ]
            
            clean_csv = StringIO("\n".join(data_lines))
            df = pd.read_csv(clean_csv)
            
            for _, row in df.iterrows():
                try:
                    item = self._row_to_item(row, target_date)
                    
                    if item and item.validate():
                        self.items.append(item)
                        self.pipeline.save_items(item)
                        
                except Exception as e:
                    logger.error(f"CB row parse error: {e}")
                    continue
            
            logger.info(f"CB Master {target_date}: Parsed {len(df)} rows")
            
        except Exception as e:
            logger.error(f"CB Master parse error: {e}")
    
    def _row_to_item(self, row, target_date):
        """將 CSV 行轉換為 Item"""
        try:
            # 欄位映射（根據實際 CSV 格式調整）
            cb_code = str(row.get("CB Code", "")).strip()
            cb_name = str(row.get("CB Name", "")).strip()
            underlying_stock = str(row.get("Stock Code", "")).strip()
            
            return CbMasterItem(
                cb_code=cb_code,
                cb_name=cb_name,
                underlying_stock=underlying_stock,
                market_type="TPEx",
                source_url=self.BASE_URL,
                source_type="tpex_cb"
            )
            
        except Exception as e:
            logger.error(f"Row to item error: {e}")
            return None
    
    def get_statistics(self):
        """取得統計"""
        return {
            "total_items": len(self.items),
            "unique_cb_count": len(set(i.cb_code for i in self.items)),
        }


# ===== 命令列入口 =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--output", default="csv", choices=["csv", "db"])
    args = parser.parse_args()
    
    if args.output == "csv":
        pipeline = CsvPipeline(output_dir="data/output")
    else:
        pipeline = PostgresPipeline(table_name="cb_master")
    
    spider = CbMasterSpider(pipeline=pipeline, days_back=args.days)
    spider.start()
    
    print(f"Statistics: {spider.get_statistics()}")
    spider.pipeline.close()
```

### 2.4 更新 `src/spiders/__init__.py`

```python
"""Spiders Module"""
from .example_spider import ExampleSpider
from .stock_master_spider import StockMasterSpider
from .cb_master_spider import CbMasterSpider

__all__ = [
    "ExampleSpider",
    "StockMasterSpider",
    "CbMasterSpider",
]
```

### 2.5 建立測試檔案 (`tests/test_framework/test_master_spider.py`)

```python
"""Master 爬蟲測試"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, "src")

from spiders.stock_master_spider import StockMasterSpider
from spiders.cb_master_spider import CbMasterSpider
from src.framework.base_item import StockMasterItem, CbMasterItem
from src.framework.pipelines import CsvPipeline, MemoryPipeline


class TestStockMasterSpider:
    """StockMasterSpider 測試"""
    
    def test_initialization(self):
        """測試初始化"""
        spider = StockMasterSpider()
        assert spider is not None
        assert spider.TWSE_URL == "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        assert spider.TPEX_URL == "https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4"
    
    def test_parse_twse_html(self):
        """測試 TWSE HTML 解析"""
        spider = StockMasterSpider()
        
        mock_html = """
        <table>
            <tr><td>2330　台積電</td><td>上市</td></tr>
            <tr><td>2317　鴻海</td><td>上市</td></tr>
        </table>
        """
        
        # 直接測試解析邏輯
        # 由於 parse_twse 需要 response 物件，這裡用簡化測試
        pass
    
    def test_get_statistics(self):
        """測試統計"""
        spider = StockMasterSpider()
        stats = spider.get_statistics()
        
        assert "total_items" in stats
        assert "twse_count" in stats
        assert "tpex_count" in stats


class TestCbMasterSpider:
    """CbMasterSpider 測試"""
    
    def test_initialization(self):
        """測試初始化"""
        spider = CbMasterSpider()
        assert spider is not None
        assert spider.days_back == 30
    
    def test_generate_dates(self):
        """測試日期生成"""
        spider = CbMasterSpider(days_back=7)
        dates = spider._generate_dates()
        
        assert len(dates) == 7
        assert len(dates[0]) == 8  # YYYYMMDD
    
    def test_row_to_item(self):
        """測試行轉換 Item"""
        spider = CbMasterSpider()
        
        mock_row = {
            "CB Code": "12345",
            "CB Name": "測試轉債",
            "Stock Code": "2330",
        }
        
        item = spider._row_to_item(mock_row, "20240101")
        
        assert item is not None
        assert item.cb_code == "12345"
        assert item.cb_name == "測試轉債"
        assert item.underlying_stock == "2330"


class TestFieldMapping:
    """欄位映射測試"""
    
    def test_stock_master_unique_key(self):
        """測試 StockMasterItem unique_key"""
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE"
        )
        assert item.get_unique_key() == "2330_TWSE"
    
    def test_cb_master_unique_key(self):
        """測試 CbMasterItem unique_key"""
        item = CbMasterItem(
            cb_code="12345",
            underlying_stock="2330"
        )
        assert item.get_unique_key() == "12345_2330"


class TestIntegration:
    """整合測試"""
    
    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_csv_pipeline_integration(self):
        """測試 CSV Pipeline 整合"""
        pipeline = CsvPipeline(output_dir=self.test_dir)
        spider = StockMasterSpider(pipeline=pipeline)
        
        # 添加測試資料
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE"
        )
        
        spider.items.append(item)
        pipeline.save_items(item)
        pipeline.flush_all()
        
        import os
        csv_path = os.path.join(self.test_dir, "stock_master.csv")
        assert os.path.exists(csv_path)
```

---

## 3. 測試執行

```bash
# 執行所有測試
python -m pytest tests/test_framework/test_master_spider.py -v

# 執行並顯示覆蓋率
python -m pytest tests/test_framework/test_master_spider.py --cov=src.spiders --cov-report=html

# 執行單一測試
python -m pytest tests/test_framework/test_master_spider.py::TestStockMasterSpider::test_initialization -v
```

---

## 4. 驗收標準

- [ ] `src/spiders/stock_master_spider.py` 存在且可執行
- [ ] `src/spiders/cb_master_spider.py` 存在且可執行
- [ ] `StockMasterSpider` 可抓取 TWSE/TPEx 資料
- [ ] `CbMasterSpider` 可下載 CB Master CSV
- [ ] CSV Pipeline 正確寫入
- [ ] 所有單元測試通過
- [ ] 整合測試通過

---

## 5. 預估工時

| 任務 | 預估時間 |
|------|----------|
| StockMasterSpider | 2 小時 |
| CbMasterSpider | 2 小時 |
| 測試撰寫 | 2 小時 |
| 整合驗證 | 1 小時 |
| **總計** | **7 小時** |

---

*Prompt 版本：1.0.0*
*產生時間：2026-04-16*
*Architect Agent*
