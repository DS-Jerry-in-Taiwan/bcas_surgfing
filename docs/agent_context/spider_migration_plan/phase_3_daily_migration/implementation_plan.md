# Phase 3 實作計畫

## 1. StockDailySpider 實作

### 1.1 類結構

```python
class StockDailySpider(BaseSpider):
    """個股日行情爬蟲"""
    
    TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    
    def __init__(self, pipeline=None, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline or PostgresPipeline(table_name="stock_daily")
        self.items: List[StockDailyItem] = []
    
    def fetch_daily(self, symbol: str, year: int, month: int) -> SpiderResponse:
        """抓取單一股票單月資料"""
        
    def fetch_date_range(
        self, 
        symbol: str, 
        start_date: str,  # YYYY-MM-DD
        end_date: str      # YYYY-MM-DD
    ) -> Dict[str, Any]:
        """抓取日期區間內所有月份"""
        
    def parse_twse_json(self, data: dict, symbol: str) -> List[StockDailyItem]:
        """解析 TWSE JSON 回應"""
```

### 1.2 TWSE JSON 回應格式

```json
{
  "stat": "OK",
  "date": "20240115",
  "title": "某股票日成交資訊",
  "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
  "data": [
    ["113/01/15", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"]
  ]
}
```

### 1.3 欄位映射

| TWSE欄位 | StockDailyItem | 說明 |
|----------|----------------|------|
| 日期 | date | 需民國年轉換 |
| 開盤價 | open_price | float |
| 最高價 | high_price | float |
| 最低價 | low_price | float |
| 收盤價 | close_price | float |
| 成交股數 | volume | int (需移除逗號) |
| 漲跌價差 | price_change | float |
| 成交筆數 | transaction_count | int |

---

## 2. TpexCbDailySpider 實作

### 2.1 類結構

```python
class TpexCbDailySpider(BaseSpider):
    """TPEx 可轉債日行情爬蟲"""
    
    BASE_URL = "https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"
    
    def __init__(self, pipeline=None, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline or PostgresPipeline(table_name="tpex_cb_daily")
        self.items: List[TpexCbDailyItem] = []
    
    def fetch_daily(self, date: str) -> SpiderResponse:
        """抓取指定日期所有 CB 行情"""
        
    def fetch_date_range(
        self,
        start_date: str,  # YYYY-MM-DD
        end_date: str     # YYYY-MM-DD
    ) -> Dict[str, Any]:
        """抓取日期區間內所有 CB 行情"""
        
    def parse_cb_csv(self, content: bytes, target_date: str) -> List[TpexCbDailyItem]:
        """解析 TPEx CB CSV"""
```

### 2.2 TPEx CB CSV 欄位

| CSV欄位 | TpexCbDailyItem | 說明 |
|---------|-----------------|------|
| 代號 | cb_code | 可轉債代號 |
| 名稱 | cb_name | 可轉債名稱 |
| 標的股票 | underlying_stock | 標的股票代號 |
| 收盤價 | closing_price | float |
| 成交量 | volume | int |
| 週轉率(%) | turnover_rate | float |
| 溢價率(%) | premium_rate | float |
| 轉換價格 | conversion_price | float |
| 餘額(千) | remaining_balance | float |

---

## 3. 日期處理模組

```python
from datetime import datetime, timedelta

def generate_date_range(start: str, end: str) -> List[str]:
    """生成日期區間列表"""
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")
    
    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

def get_months_in_range(start: str, end: str) -> List[Tuple[int, int]]:
    """取得區間內所有月份 (year, month)"""
    # 實現月份迭代邏輯
```

---

## 4. 實作步驟

### Step 1: 創建框架 (30分鐘)
1. 創建 `src/spiders/stock_daily_spider.py` 框架
2. 創建 `src/spiders/tpex_cb_daily_spider.py` 框架
3. 更新 `src/spiders/__init__.py` 匯出

### Step 2: StockDailySpider 實作 (1小時)
1. 實作 `fetch_daily()` - 單一股票單月
2. 實作 `parse_twse_json()` - JSON 解析
3. 實作 `fetch_date_range()` - 日期區間
4. 實作民國年轉換邏輯

### Step 3: TpexCbDailySpider 實作 (1小時)
1. 實作 `fetch_daily()` - 單日所有CB
2. 實作 `parse_cb_csv()` - CSV 解析
3. 實作 `fetch_date_range()` - 日期區間
4. 處理 Big5 編碼

### Step 4: CLI 入口 (30分鐘)
1. 實作 `__main__` 命令列解析
2. 支援 `--symbol`, `--start`, `--end`, `--output` 參數

### Step 5: 單元測試 (2小時)
1. Mock HTTP 回應測試解析邏輯
2. 日期處理測試
3. Item 驗證測試
4. Pipeline 整合測試

---

## 5. 關鍵技術點

### 5.1 民國年轉換
```python
def convert_minguo_to_ad(minguo_date: str) -> str:
    """113/01/15 -> 2024-01-15"""
    parts = minguo_date.strip().split("/")
    year = int(parts[0]) + 1911
    return f"{year:04d}-{parts[1]}-{parts[2]}"
```

### 5.2 數值解析
```python
def parse_number(value: str) -> Union[int, float]:
    """處理千分位逗號"""
    cleaned = value.replace(",", "").replace("+", "")
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except:
        return 0
```

### 5.3 去重 unique_key
```python
# StockDailyItem
def get_unique_key(self) -> str:
    return f"{self.symbol}_{self.date}"

# TpexCbDailyItem  
def get_unique_key(self) -> str:
    return f"{self.cb_code}_{self.trade_date}"
```

---

## 6. 錯誤處理策略

| 錯誤類型 | 處理方式 |
|----------|----------|
| HTTP 404 | 記錄警告, 繼續下一筆 |
| HTTP 500 | 重試 3 次, 然後記錄錯誤 |
| 解析失敗 | 記錄錯誤, 跳過該筆 |
| 空資料 | 記錄警告, 繼續 |
| 網路超時 | 重試 3 次 |

---

*最後更新：2026-04-16*
