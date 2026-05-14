# Phase 5 Stage 3 — 任務規劃文件

> 建立日期: 2026-05-13
> 階段: Phase 5 Stage 3 — BrokerBreakdownSpider 改寫
> 預估工時: 4h

---

## 1. 需求確認

### 1.1 任務目標

將 `BrokerBreakdownSpider` 的資料源從失效的 TWSE MI_20S API 切換到 `BsrClient`（BSR 網站 + OCR），
保持現有介面、`collect_only` 模式、`pipeline` 流程完全相容。

### 1.2 成功標準

| 標準 | 驗證方式 |
|------|---------|
| `fetch_broker_breakdown(date, symbol)` 簽名不變 | 匯入測試 |
| 使用 BsrClient 而非 requests.get 直連 TWSE | 測試 mock BsrClient |
| source_type 改為 "bsr" | 測試 assert |
| source_url 為 BSR 網站 URL | 測試 assert |
| collect_only + pipeline 模式不變 | 測試 assert |
| CLI 介面 (`--date`, `--symbol`) 不變 | 測試 assert |
| 所有測試通過 | `pytest tests/test_broker_breakdown_spider.py -v` |
| 不影響現有測試 | `pytest tests/ -v` |

### 1.3 任務邊界

**範圍內:**
- ✅ 改寫 `src/spiders/broker_breakdown_spider.py`
- ✅ 重寫 `tests/test_broker_breakdown_spider.py` (mock BsrClient)

**範圍外:**
- ❌ 不修改 `src/spiders/bsr_client.py` (Stage 2 已穩定)
- ❌ 不修改 `src/spiders/ocr_solver.py` (Stage 2 已穩定)
- ❌ 不修改 `src/analytics/risk_assessor.py` (Stage 4)
- ❌ 不修改 `src/analytics/chip_profiler.py` (Stage 4)
- ❌ 不修改 `src/run_daily.py` (Stage 5)
- ❌ 不修改 DB schema

---

## 2. 改寫方案

### 2.1 Spider 改寫要點

```python
class BrokerBreakdownSpider(BaseSpider):
    
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        # 簽名完全保持不變
        super().__init__(...)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
        self._bsr_client = None  # lazy init
    
    @property
    def bsr_client(self):
        """Lazy init BsrClient"""
        if self._bsr_client is None:
            from src.spiders.bsr_client import BsrClient
            self._bsr_client = BsrClient()
        return self._bsr_client
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """
        使用 BSR + OCR 取得分點資料
        
        簽名完全保持: (date, symbol) → SpiderResponse
        """
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
                    source_url=BsrClient.BASE_URL,  # 注意: BASE_URL 是 module-level
                )
                self.items.append(item)
                self.add_item(item)
            
            return SpiderResponse(
                success=True,
                data={"count": len(self.items)},
            )
        except (BsrConnectionError, BsrCaptchaError, BsrParseError, BsrCircuitBreakerOpen) as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
            )
        except Exception as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢異常: {e}",
            )
    
    def close(self):
        """清理 BSR session"""
        if self._bsr_client:
            self._bsr_client.close()
```

### 2.2 BsrClient.fetch_broker_data() 回傳格式

```python
# BSR 客戶端回傳的 dict list
[
    {
        "seq": 1,              # 排名 (1-based)
        "broker_name": "凱基-台北",
        "broker_id": "9200",
        "buy_volume": 1234567,
        "sell_volume": 567890,
        "net_volume": 666677,
    },
    # ... 其餘券商
]
```

### 2.3 BrokerBreakdownItem 對應

| BSR dict 欄位 | BrokerBreakdownItem | 說明 |
|---------------|-------------------|------|
| `seq` | `rank` | 排名 |
| `broker_name` | `broker_name` | 券商名稱 |
| `broker_id` | `broker_id` | 券商代號 (str) |
| `buy_volume` | `buy_volume` | 買進股數 |
| `sell_volume` | `sell_volume` | 賣出股數 |
| `net_volume` | `net_volume` | 淨買超股數 |
| (固定) | `source_type` | "bsr" |
| (固定) | `source_url` | BSR base URL |
| (參數) | `date` | YYYYMMDD |
| (參數) | `symbol` | 股票代號 |

---

## 3. 測試策略

將現有 17 個測試從 mock `requests.get` 改為 mock `BsrClient`：

| 測試類別 | 現有測試 | 改寫方式 |
|---------|---------|---------|
| Init 測試 (3) | mock 無關 | **不修改** (__init__ 簽名不變) |
| Fetch 測試 (4) | mock requests.get → TWSE JSON | mock BsrClient.fetch_broker_data() |
| Error 測試 (4) | mock requests exception | mock BsrClient exception |
| Item 測試 (3) | assert TWSE 欄位 | assert BSR 欄位 (source_type="bsr") |
| Statistics (2) | mock requests.get | mock BsrClient |
| Collect Only (2) | mock requests.get | mock BsrClient |

### 測試 Mock 策略

```python
# 取代原本的 @patch('requests.get')
# 改為:
@patch('src.spiders.broker_breakdown_spider.BsrClient')
def test_successful_fetch(self, mock_bsr_client):
    # 設定 mock
    instance = mock_bsr_client.return_value
    instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA
    
    # 執行
    spider = BrokerBreakdownSpider()
    result = spider.fetch_broker_breakdown("20260509", "2330")
    
    # 驗證
    assert result.success is True
    assert result.data["count"] == 2
    assert len(spider.get_items()) == 2
    assert spider.get_items()[0].source_type == "bsr"
```

### 測試範例資料

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

---

## 4. 完成標準

- [ ] `broker_breakdown_spider.py` 使用 BsrClient 替代直接 HTTP 請求
- [ ] `fetch_broker_breakdown(date, symbol)` 簽名不變
- [ ] `source_type` 改為 `"bsr"`
- [ ] CLI `--date`, `--symbol` 介面不變
- [ ] `collect_only` + `pipeline` 模式不變
- [ ] `close()` 方法正確清理 BsrClient session
- [ ] 所有測試通過 (15+ 案例)
- [ ] 回歸測試不影響現有 59 個 Stage 2 測試
