# Phase 2: Master 資料爬蟲遷移實作計畫

## 1. 概述

Phase 2 專注於將現有的 Master 資料爬蟲遷移至 Feapder 框架，確保主檔資料的穩定抓取與入庫。

---

## 2. 現有程式碼分析

### 2.1 cb_master.py 分析

```python
# 主要功能：下載 TPEx 可轉債主檔 CSV
# URL 格式: https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/{year}/{year_month}/RSdrs001.{date}-C.csv
# 編碼: Big5
# 特殊處理: 過濾 TITLE/DATADATE/GLOSS 開頭行
```

| 特性 | 說明 |
|------|------|
| 資料來源 | TPEx CSV |
| URL 模式 | `RSdrs001.{YYYYMMDD}-C.csv` |
| 編碼 | Big5 |
| 解析方式 | pandas.read_csv |
| 輸出 | CSV 檔案 |

### 2.2 stock_crawler.py 分析

```python
# 主要功能：抓取上市/上櫃股票主檔
# TWSE URL: https://isin.twse.com.tw/isin/C_public.jsp?strMode=2
# TPEx URL: https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4
# 編碼: TWSE(Big5), TPEx(UTF-8)
# 解析方式: pandas.read_html
```

| 特性 | 說明 |
|------|------|
| TWSE 編碼 | Big5 |
| TPEx 編碼 | UTF-8 |
| 解析方式 | pandas.read_html |
| 欄位處理 | "代號　名稱" → symbol, name |

---

## 3. 遷移目標

### 3.1 預期產出

```
src/spiders/
├── __init__.py
├── stock_master_spider.py    # 股票主檔爬蟲
└── cb_master_spider.py       # 可轉債主檔爬蟲
```

### 3.2 Feapder Items（Phase 1 已定義）

```python
# StockMasterItem - 股票主檔
@dataclass
class StockMasterItem(BaseItem):
    __table_name__ = "stock_master"
    symbol: str = ""
    name: str = ""
    market_type: str = ""  # TWSE / TPEx
    industry: str = ""
    listing_date: str = ""
    cfi_code: str = ""

# CbMasterItem - 可轉債主檔
@dataclass
class CbMasterItem(BaseItem):
    __table_name__ = "cb_master"
    cb_code: str = ""
    cb_name: str = ""
    underlying_stock: str = ""
    market_type: str = ""
    issue_date: str = ""
    maturity_date: str = ""
    conversion_price: float = 0.0
    coupon_rate: float = 0.0
```

---

## 4. 實作步驟

### Step 1: 建立 StockMasterSpider

**檔案**: `src/spiders/stock_master_spider.py`

```python
from feapder import AirSpider, Request
from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import StockMasterItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline
import pandas as pd


class StockMasterSpider(AirSpider, BaseSpider):
    """
    股票主檔爬蟲
    
    功能：
    - 抓取 TWSE 股票主檔
    - 抓取 TPEx 股票主檔
    - 存入 PostgreSQL
    """
    
    TWSE_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    TPEX_URL = "https://isin.tpex.org.tw/isin/C_public.jsp?strMode=4"
    
    def __init__(self, pipeline=None, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline or PostgresPipeline(table_name="stock_master")
    
    def start_requests(self):
        # TWSE 任務
        yield Request(self.TWSE_URL, callback=self.parse_twse)
        # TPEx 任務
        yield Request(self.TPEX_URL, callback=self.parse_tpex)
    
    def parse_twse(self, request, response):
        """解析 TWSE 主檔"""
        # 實作見程式碼
        pass
    
    def parse_tpex(self, request, response):
        """解析 TPEx 主檔"""
        # 實作見程式碼
        pass
```

### Step 2: 建立 CbMasterSpider

**檔案**: `src/spiders/cb_master_spider.py`

```python
from feapder import AirSpider, Request
from src.framework.base_spider import BaseSpider
from src.framework.base_item import CbMasterItem
from src.framework.pipelines import PostgresPipeline
from io import BytesIO, StringIO
import pandas as pd


class CbMasterSpider(AirSpider, BaseSpider):
    """
    可轉債主檔爬蟲
    
    功能：
    - 下載 TPEx CB Master CSV
    - Big5 編碼處理
    - 存入 PostgreSQL
    """
    
    BASE_URL = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb"
    
    def start_requests(self):
        # 生成近期日期的請求
        for date in self._generate_dates():
            url = f"{self.BASE_URL}/{date[:4]}/{date[:6]}/RSdrs001.{date}-C.csv"
            yield Request(url, callback=self.parse_cb_master)
    
    def parse_cb_master(self, request, response):
        """解析 CB Master CSV"""
        # 實作見程式碼
        pass
```

### Step 3: 整合 PostgresPipeline

確保 Pipeline 支援：
- `ON CONFLICT DO UPDATE` 去重
- 批次寫入
- 錯誤處理與重試

### Step 4: 欄位映射實作

#### TWSE 欄位映射

| HTML 欄位 | Item 欄位 |
|-----------|-----------|
| 有價證券代號及名稱 | symbol, name |
| Market | market_type |
| Industry | industry |
| Listed Date | listing_date |

#### TPEx CB CSV 欄位映射

| CSV 欄位 | Item 欄位 |
|----------|----------|
| CB Code | cb_code |
| CB Name | cb_name |
| Stock Code | underlying_stock |
| Issue Date | issue_date |
| Maturity Date | maturity_date |
| Conversion Price | conversion_price |
| Coupon Rate | coupon_rate |

---

## 5. 任務邊界定義

### Phase 2 完成項目

- [x] StockMasterSpider（TWSE + TPEx）
- [x] CbMasterSpider（TPEx CSV）
- [x] PostgresPipeline 整合
- [x] 去重邏輯（ON CONFLICT）
- [x] 單元測試
- [x] 整合測試

### Phase 3 (Daily) 涵蓋

- [x] StockDailySpider（日行情）
- [x] TpexCbDailySpider（日行情）
- [x] 批次排程
- [x] 增量更新邏輯
- [x] 歷史資料回補

---

## 6. 資料庫 Schema

```sql
-- 股票主檔
CREATE TABLE stock_master (
    symbol VARCHAR(10) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    industry VARCHAR(100),
    listing_date DATE,
    cfi_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, market_type)
);

-- 可轉債主檔
CREATE TABLE cb_master (
    cb_code VARCHAR(10) NOT NULL,
    underlying_stock VARCHAR(10) NOT NULL,
    cb_name VARCHAR(100),
    market_type VARCHAR(10),
    issue_date DATE,
    maturity_date DATE,
    conversion_price DECIMAL(10,2),
    coupon_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cb_code, underlying_stock)
);
```

---

## 7. 環境變數

```bash
# Phase 2 新增
MASTER_SPIDER_ENABLED=true
MASTER_UPDATE_INTERVAL=86400  # 每日更新
```

---

## 8. 風險與對策

| 風險 | 等級 | 對策 |
|------|------|------|
| Big5 編碼解析失敗 | 🟡 | 降級讀取、錯誤隔離 |
| pandas.read_html 不穩定 | 🟡 | 增加重試機制 |
| 大量資料寫入效能 | 🟡 | 批次寫入、事務控制 |
| TPEx 反爬機制 | 🔴 | 增加請求間隔、Proxy |

---

## 9. 預估工時

| 任務 | 預估時間 |
|------|----------|
| StockMasterSpider | 2 小時 |
| CbMasterSpider | 2 小時 |
| Pipeline 整合 | 1 小時 |
| 單元測試 | 2 小時 |
| 整合測試 | 1 小時 |
| **總計** | **8 小時** |

---

*文件版本：1.0.0*
*建立時間：2026-04-16*
