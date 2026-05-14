# Phase 5 Stage 3 — 開發者 Prompt

## 任務: BrokerBreakdownSpider 改寫 (TWSE API → BSR + OCR)

> 你是 Python 開發者。你的任務是改寫 `BrokerBreakdownSpider`，使其從失效的 TWSE MI_20S API 切換到使用 Stage 2 已完成的 `BsrClient`（BSR 網站 + ddddocr OCR）。所有測試需 mock BsrClient，不使用真實網路請求。

---

## 一、背景資訊

### Stage 2 已完成模組

| 模組 | 位置 | 說明 |
|------|------|------|
| `OcrSolver` | `src/spiders/ocr_solver.py` | ddddocr 封裝 (70行) |
| `BsrClient` | `src/spiders/bsr_client.py` | BSR 客戶端 (508行) |
| `test_bsr_client.py` | `tests/test_bsr_client.py` | 59 測試 ✅ |

### BsrClient 主要 API

```python
from src.spiders.bsr_client import BsrClient

client = BsrClient(max_retries=3, request_interval=2.0)
data = client.fetch_broker_data("2330")
# 回傳 List[Dict]:
# [
#     {
#         "seq": 1,
#         "broker_name": "凱基-台北",
#         "broker_id": "9200",
#         "buy_volume": 1234567,
#         "sell_volume": 567890,
#         "net_volume": 666677,
#     },
# ]
client.close()
```

### BsrClient 可能拋出的異常

| 異常 | 情境 |
|------|------|
| `BsrConnectionError` | 網路連線失敗 |
| `BsrCaptchaError` | 驗證碼重試耗盡 |
| `BsrParseError` | BSR 結果 HTML 解析失敗 |
| `BsrCircuitBreakerOpen` | Circuit Breaker 開啟中 |

---

## 二、你必須修改的檔案

### 2.1 `src/spiders/broker_breakdown_spider.py` — 改寫 (核心)

**保持不變的項目（絕對不能改）：**
- `__init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs)` — 簽名完全一致
- `self.pipeline = pipeline`
- `self.items: List[BrokerBreakdownItem] = []`
- `self.collect_only = True`
- `fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse` — 簽名完全一致
- `get_items()` → 回傳 `List[BrokerBreakdownItem]`
- `get_statistics()` → 回傳 `Dict`
- CLI 使用 `--date` 和 `--symbol` 參數

**需要變更的項目：**
- 移除 `API_BASE` 類別屬性 (不再需要 TWSE URL)
- 新增 `_bsr_client = None` (lazy init)
- 新增 `bsr_client` property (lazy init `BsrClient`)
- 改寫 `fetch_broker_breakdown()` 使用 `self.bsr_client.fetch_broker_data(symbol)`
- 將 BSR dict 對應到 `BrokerBreakdownItem` 欄位
- `source_type` 設為 `"bsr"`
- `source_url` 設為 `"https://bsr.twse.com.tw/bshtm/"`
- 包裝 BsrClient 的異常成 `SpiderResponse(success=False, error=...)`
- 新增 `close()` 方法清理 `BsrClient`

**改寫後的 `fetch_broker_breakdown` 偽代碼：**
```python
def fetch_broker_breakdown(self, date, symbol):
    try:
        records = self.bsr_client.fetch_broker_data(symbol)
        self.items.clear()
        
        for record in records:
            item = BrokerBreakdownItem(
                date=date,
                symbol=symbol,
                broker_id=record["broker_id"],
                broker_name=record["broker_name"],
                buy_volume=record["buy_volume"],
                sell_volume=record["sell_volume"],
                net_volume=record["net_volume"],
                rank=record.get("seq", 0),
                source_type="bsr",
                source_url="https://bsr.twse.com.tw/bshtm/",
            )
            self.items.append(item)
            self.add_item(item)
        
        return SpiderResponse(success=True, data={"count": len(self.items)})
    
    except (BsrConnectionError, BsrCaptchaError, BsrParseError, BsrCircuitBreakerOpen) as e:
        return SpiderResponse(success=False, error=f"BSR 查詢失敗: {e}")
    except Exception as e:
        return SpiderResponse(success=False, error=f"BSR 查詢異常: {e}")
```

### 2.2 `tests/test_broker_breakdown_spider.py` — 全面重寫

將現有 17 個測試從 mock `requests.get` 改為 mock `BsrClient`。

**Mock 策略：**
```python
# 取代原本的:
# @patch('requests.get')
# def test_successful_fetch(self, mock_get):

# 改為:
@patch('src.spiders.broker_breakdown_spider.BsrClient')
def test_successful_fetch(self, mock_bsr_client):
    mock_instance = mock_bsr_client.return_value
    mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA
    
    spider = BrokerBreakdownSpider()
    result = spider.fetch_broker_breakdown("20260509", "2330")
    
    assert result.success is True
    assert result.data["count"] == len(SAMPLE_BSR_DATA)
```

**測試範例資料：**
```python
SAMPLE_BSR_DATA = [
    {
        "seq": 1,
        "broker_name": "凱基-台北",
        "broker_id": "9200",
        "buy_volume": 1234567,
        "sell_volume": 567890,
        "net_volume": 666677,
    },
    {
        "seq": 2,
        "broker_name": "美商高盛",
        "broker_id": "1020",
        "buy_volume": 987654,
        "sell_volume": 432100,
        "net_volume": 555554,
    },
]
```

**最少 15+ 測試案例：**

| 測試類別 | 案例 | 說明 |
|---------|------|------|
| **Init** (3) | `test_init_accepts_pipeline` | pipeline=None |
| | `test_init_with_pipeline` | 接受 pipeline |
| | `test_items_empty` | items 初始化為 [] |
| **Fetch** (4) | `test_successful_fetch` | 成功回傳 SpiderResponse(data={"count": N}) |
| | `test_add_item_called` | 每筆資料呼叫 add_item() |
| | `test_items_type` | get_items() 回傳 BrokerBreakdownItem |
| | `test_items_cleared` | 每次 fetch 前清空 items |
| **Error** (4) | `test_bsr_connection_error` | BsrConnectionError → success=False |
| | `test_bsr_captcha_error` | BsrCaptchaError → success=False |
| | `test_bsr_parse_error` | BsrParseError → success=False |
| | `test_circuit_breaker_open` | BsrCircuitBreakerOpen → success=False |
| **Item** (3) | `test_item_fields` | BrokerBreakdownItem 欄位正確 |
| | `test_item_source_bsr` | source_type == "bsr" |
| | `test_rank_from_seq` | rank 從 BSR seq 取得 |
| **Stats** (2) | `test_statistics_includes_total` | get_statistics() 含 total_items |
| | `test_statistics_empty` | 無資料時 total_items = 0 |
| **Collect** (2) | `test_pending_items` | collect_only items 加入 _pending_items |
| | `test_no_pipeline_no_save` | 無 pipeline 不觸發 save |

---

## 三、實作細節

### 3.1 BrokerBreakdownSpider 檔案結構

```python
"""
BrokerBreakdownSpider — 券商分點買賣超爬蟲

資料源: BSR 網站 (https://bsr.twse.com.tw/bshtm/)
使用 BsrClient + ddddocr OCR 取得資料

Usage:
    spider = BrokerBreakdownSpider()
    result = spider.fetch_broker_breakdown("20260509", "2330")
    for item in spider.get_items():
        print(item.to_dict())
"""
from typing import Optional, List, Dict, Any
from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import BrokerBreakdownItem
from src.spiders.bsr_client import (
    BsrClient,
    BsrConnectionError,
    BsrCaptchaError,
    BsrParseError,
    BsrCircuitBreakerOpen,
)


class BrokerBreakdownSpider(BaseSpider):
    
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
        self._bsr_client: Optional[BsrClient] = None
    
    @property
    def bsr_client(self) -> BsrClient:
        if self._bsr_client is None:
            self._bsr_client = BsrClient()
        return self._bsr_client
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """..."""
    
    def get_items(self) -> List[BrokerBreakdownItem]:
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats
    
    def close(self):
        if self._bsr_client:
            self._bsr_client.close()


# CLI 支援 (保持與原本完全相同的介面)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="券商分點買賣超爬蟲")
    parser.add_argument("--date", required=True, help="日期 (YYYYMMDD)")
    parser.add_argument("--symbol", required=True, help="股票代號")
    args = parser.parse_args()
    
    spider = BrokerBreakdownSpider()
    try:
        result = spider.fetch_broker_breakdown(args.date, args.symbol)
        print(f"Success: {result.success}")
        print(f"Items: {len(spider.get_items())}")
        for item in spider.get_items():
            print(f"  {item.rank}. {item.broker_name}({item.broker_id}): "
                  f"買 {item.buy_volume} / 賣 {item.sell_volume} / 淨 {item.net_volume}")
    finally:
        spider.close()
```

### 3.2 注意事項

1. **Lazy init BsrClient**: 不要在 `__init__` 中建立 BsrClient，使用 property 延遲初始化（節省資源）
2. **異常處理**: `BsrClient.fetch_broker_data()` 會拋出 `BsrConnectionError`、`BsrCaptchaError` 等，需包裝成 `SpiderResponse(success=False)`
3. **資源清理**: 實作 `close()` 方法，在 spider 生命週期結束時關閉 BsrClient session
4. **CLI 相容**: CLI 的 `--date` 和 `--symbol` 參數保持完全一致
5. **Module-level BASE_URL**: `bsr_client.py` 的 `BASE_URL` 是 module-level 常數 (不是 class attribute)，使用 `"https://bsr.twse.com.tw/bshtm/"` 字串常數即可

---

## 四、驗收標準

請完成後執行：

```bash
# 1. 執行 spider 測試
cd /home/ubuntu/projects/bcas_quant
python -m pytest tests/test_broker_breakdown_spider.py -v 2>&1

# 2. 確認 import 正常
python -c "
from src.spiders.broker_breakdown_spider import BrokerBreakdownSpider
s = BrokerBreakdownSpider()
s.close()
print('BrokerBreakdownSpider OK')
" 2>&1

# 3. CLI 測試
python -m src.spiders.broker_breakdown_spider --date 20260509 --symbol 2330 2>&1 | head -5

# 4. 回歸測試
python -m pytest tests/ -v --tb=short 2>&1 | tail -10
```

## 五、邊界與禁止事項

- ❌ 不要修改 `src/spiders/bsr_client.py`
- ❌ 不要修改 `src/spiders/ocr_solver.py`
- ❌ 不要修改 `src/analytics/` 下的任何檔案
- ❌ 不要修改 `src/run_daily.py`
- ❌ 不要修改 DB schema
- ❌ 不要在 spider 中直接實作 HTTP 請求 — 全部透過 BsrClient
- ❌ 不要使用 `requests.get()` — BsrClient 已經封裝了所有 HTTP 邏輯
