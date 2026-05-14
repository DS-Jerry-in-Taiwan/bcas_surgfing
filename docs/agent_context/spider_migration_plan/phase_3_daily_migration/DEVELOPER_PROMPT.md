# Developer Prompt: Phase 3 日行情爬蟲遷移

## 角色

你是 Developer Agent，負責實作 Phase 3 的日行情爬蟲遷移任務。

## 專案路徑

```
~/projects/bcas_quant/
```

## 參考檔案

### 源碼 (要遷移的目標)
- `src/crawlers/daily/twse_daily.py` - TWSE 個股日行情
- `src/crawlers/daily/tpex_cb_daily.py` - TPEx 可轉債日行情

### 框架 (Phase 1)
- `src/framework/base_spider.py` - BaseSpider 類
- `src/framework/base_item.py` - StockDailyItem, TpexCbDailyItem
- `src/framework/pipelines.py` - PostgresPipeline, CsvPipeline

### 範例 (Phase 2)
- `src/spiders/stock_master_spider.py` - 參考模式
- `src/spiders/cb_master_spider.py` - 參考模式
- `tests/test_framework/test_master_spider.py` - 測試範例

### 工具
- `src/utils/date_converter.py` - 民國年轉換工具

## 實作任務

### Task 1: 建立 StockDailySpider

**檔案**: `src/spiders/stock_daily_spider.py`

**類結構**:
```python
from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import StockDailyItem
from src.framework.pipelines import PostgresPipeline, CsvPipeline

class StockDailySpider(BaseSpider):
    TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
    
    def __init__(self, pipeline=None, **kwargs):
        # 初始化邏輯
        pass
    
    def fetch_daily(self, symbol: str, year: int, month: int) -> SpiderResponse:
        # 抓取單一股票單月資料
        pass
    
    def parse_twse_json(self, data: dict, symbol: str) -> List[StockDailyItem]:
        # 解析 TWSE JSON 回應
        pass
    
    def fetch_date_range(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        # 抓取日期區間內所有月份
        pass
    
    # 實用方法
    def _convert_minguo_date(self, minguo_date: str) -> str:
        # 113/01/15 -> 2024-01-15
        pass
    
    def _parse_number(self, value: str) -> Union[int, float]:
        # 處理千分位 "1,234,567" -> 1234567
        pass
```

**TWSE API 參數**:
```python
params = {
    "response": "json",
    "date": f"{year}{month:02d}01",
    "stockNo": stock_id
}
```

**JSON 回應欄位**:
```
fields: ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"]
```

### Task 2: 建立 TpexCbDailySpider

**檔案**: `src/spiders/tpex_cb_daily_spider.py`

**類結構**:
```python
class TpexCbDailySpider(BaseSpider):
    BASE_URL = "https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"
    
    def __init__(self, pipeline=None, **kwargs):
        pass
    
    def fetch_daily(self, date: str) -> SpiderResponse:
        # 抓取指定日期所有 CB 行情
        pass
    
    def parse_cb_csv(self, content: bytes, target_date: str) -> List[TpexCbDailyItem]:
        # 解析 TPEx CB CSV
        pass
    
    def fetch_date_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        # 抓取日期區間
        pass
```

**TPEx API 參數**:
```python
params = {
    "l": "zh-tw",
    "d": date.replace("-", "/")  # 2024-01-15 -> 2024/01/15
}
```

### Task 3: 更新 __init__.py

**檔案**: `src/spiders/__init__.py`

**更新內容**:
```python
from .stock_daily_spider import StockDailySpider
from .tpex_cb_daily_spider import TpexCbDailySpider

__all__ = [
    "ExampleSpider", 
    "StockMasterSpider", 
    "CbMasterSpider",
    "StockDailySpider",       # 新增
    "TpexCbDailySpider"       # 新增
]
```

### Task 4: 建立單元測試

**檔案**: `tests/test_framework/test_daily_spider.py`

參考 `tests/test_framework/test_master_spider.py` 的結構

**測試類別**:
- `TestStockDailySpider`
- `TestStockDailyParse`
- `TestStockDailyFetch`
- `TestTpexCbDailySpider`
- `TestTpexCbDailyParse`
- `TestTpexCbDailyFetch`
- `TestDateUtilities`

### Task 5: 執行測試

```bash
cd ~/projects/bcas_quant
PYTHONPATH=. .venv/bin/python -m pytest tests/test_framework/test_daily_spider.py -v
```

## 關鍵要求

1. **必須繼承 BaseSpider**: 所有爬蟲必須使用 Phase 1 的 BaseSpider
2. **使用 Item dataclass**: 使用 Phase 1 定義的 StockDailyItem, TpexCbDailyItem
3. **支援 Pipeline**: 支援 PostgresPipeline 和 CsvPipeline
4. **民國年轉換**: 使用 convert_minguo_date 或實作 _convert_minguo_date
5. **去重**: unique_key 配合 PostgreSQL ON CONFLICT DO UPDATE
6. **CLI**: 提供 __main__ 命令列入口

## 驗收標準

- [ ] StockDailySpider 正確解析 TWSE JSON
- [ ] TpexCbDailySpider 正確解析 TPEx CSV
- [ ] 日期區間抓取正確迭代月份/日期
- [ ] 所有單元測試通過
- [ ] CLI 可正常執行

## 禁止事項

- 不要修改 Phase 1/Phase 2 的現有程式碼
- 不要刪除現有測試
- 不要添加無關功能

---

*Developer Prompt for Phase 3 - 最後更新：2026-04-16*
