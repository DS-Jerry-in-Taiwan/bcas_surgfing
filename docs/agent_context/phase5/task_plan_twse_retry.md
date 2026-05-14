# TWSE Rate Limit Retry — 任務規劃

> **觸發**: E2E 測試中 stock_master 大量請求後，TWSE 短暫擋掉 stock_daily
> **方案**: 「先簡單處理」— 加 retry + 既有統計監控，後續再全面優化
> **預計工時**: 1.5h
> **優先級**: 🟡 中

---

## 1. 問題

`stock_daily_spider.fetch_daily()` 遇到 TWSE rate limiting 時直接失敗，沒有任何重試：

```
TWSE fetch error: Expecting value: line 1 column 1 (char 0)
→ 立刻回傳 SpiderResponse(success=False)
→ 不重試，整批 stock_daily 遺失
```

## 2. 既有基礎設施

`BaseSpider` 已有：
- ✅ `record_request(success=True/False)` — 記錄成功/失敗次數
- ✅ `request_count` / `error_count` — 請求統計
- ✅ `get_statistics()` → `success_rate` — 成功率監控
- ✅ `SpiderResponse` — 統一回傳格式

## 3. 實作：簡單 retry (in-line)

在 `fetch_daily()` 中加入 inline retry loop，不需要裝飾器或新類別：

```python
def fetch_daily(self, symbol: str, year: int, month: int) -> SpiderResponse:
    max_retries = 3
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching TWSE daily: {symbol} {year}/{month:02d} (attempt {attempt})")

            response = requests.get(
                self.TWSE_URL,
                params={"response": "json", "date": f"{year}{month:02d}01", "stockNo": symbol},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("stat") != "OK":
                logger.warning(f"TWSE API error: {data.get('stat')}")
                self.record_request(success=False)
                return SpiderResponse(success=False, error=f"API error: {data.get('stat')}", url=self.TWSE_URL)

            # 成功
            items = self.parse_twse_json(data, symbol)
            self.items.extend(items)
            for item in items:
                self.add_item(item)
            self.record_request(success=True)
            return SpiderResponse(
                success=True,
                data={"count": len(items), "symbol": symbol, "year": year, "month": month},
                url=self.TWSE_URL,
            )

        except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
            self.record_request(success=False)

            if attempt < max_retries:
                delay = 2 ** attempt  # 2s, 4s
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed: {last_error}")

    return SpiderResponse(success=False, error=last_error, url=self.TWSE_URL)
```

---

## 4. 測試驗證

### 4.1 既有測試零回歸
```bash
python -m pytest tests/ -v --tb=short
```

### 4.2 重試邏輯測試
在現有的 `test_framework/test_daily_spider.py` 中新增：

```python
@patch("spiders.stock_daily_spider.requests.get")
def test_fetch_daily_retry_on_failure(self, mock_get):
    """失敗時自動重試 3 次"""
    mock_get.side_effect = [
        requests.RequestException("rate limited"),  # 1st fail
        requests.RequestException("rate limited"),  # 2nd fail
        _make_mock_response(),                      # 3rd success
    ]
    spider = StockDailySpider()
    result = spider.fetch_daily("2330", 2026, 4)
    assert result.success
    assert mock_get.call_count == 3

@patch("spiders.stock_daily_spider.requests.get")
def test_fetch_daily_all_retries_fail(self, mock_get):
    """全部 3 次重試失敗"""
    mock_get.side_effect = requests.RequestException("always down")
    spider = StockDailySpider()
    result = spider.fetch_daily("2330", 2026, 4)
    assert not result.success
    assert mock_get.call_count == 3

@patch("spiders.stock_daily_spider.requests.get")
def test_fetch_daily_success_first_try(self, mock_get):
    """第一次就成功 (不重試)"""
    mock_get.return_value = _make_mock_response()
    spider = StockDailySpider()
    result = spider.fetch_daily("2330", 2026, 4)
    assert result.success
    assert mock_get.call_count == 1
```
