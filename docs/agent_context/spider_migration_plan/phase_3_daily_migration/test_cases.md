# Phase 3 測試案例

## 測試檔案結構

```
tests/test_framework/
├── test_daily_spider.py          # 新增: 日行情爬蟲測試
│   ├── TestStockDailySpider       # 個股日行情測試
│   ├── TestStockDailyParse        # TWSE JSON 解析測試
│   ├── TestTpexCbDailySpider      # CB 日行情測試
│   ├── TestTpexCbDailyParse       # CSV 解析測試
│   ├── TestDateRange              # 日期區間測試
│   └── TestDateUtilities          # 日期工具測試
```

## 單元測試清單

### TestStockDailySpider

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| SD-01 | test_initialization | 正確初始化, items 為空列表 |
| SD-02 | test_get_items | 返回當前 items 列表 |
| SD-03 | test_get_statistics | 統計包含 request_count, total_items |
| SD-04 | test_urls | TWSE_URL 正確 |
| SD-05 | test_repr | repr 包含 StockDailySpider |

### TestStockDailyParse

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| SD-10 | test_parse_twse_json_basic | 正常JSON | 正確解析日期、價格、成交量 |
| SD-11 | test_parse_twse_json_empty | 空data陣列 | 返回空列表 |
| SD-12 | test_parse_twse_json_invalid | 格式錯誤 | 返回空列表, 記錄錯誤 |
| SD-13 | test_convert_minguo_date | "113/01/15" | "2024-01-15" |
| SD-14 | test_convert_minguo_date_edge | "001/01/01" | "1912-01-01" |
| SD-15 | test_parse_number_with_comma | "1,234,567" | 1234567 |
| SD-16 | test_parse_number_float | "1,234.56" | 1234.56 |
| SD-17 | test_parse_number_empty | "" | 0 |
| SD-18 | test_item_unique_key | StockDailyItem | "2330_2024-01-15" |

### TestStockDailyFetch

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| SD-20 | test_fetch_daily_success | 返回 SpiderResponse, items 增加 |
| SD-21 | test_fetch_daily_404 | 返回失敗 response, 不增加 items |
| SD-22 | test_fetch_daily_network_error | 返回失敗 response |
| SD-23 | test_fetch_date_range | 正確迭代月份 |
| SD-24 | test_fetch_multiple_stocks | 批量抓取多檔股票 |

### TestTpexCbDailySpider

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| CB-01 | test_initialization | 正確初始化 |
| CB-02 | test_get_items | 返回 items 列表 |
| CB-03 | test_get_statistics | 統計包含 unique_cb_count |
| CB-04 | test_urls | BASE_URL 正確 |
| CB-05 | test_repr | repr 包含 TpexCbDailySpider |

### TestTpexCbDailyParse

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| CB-10 | test_parse_cb_csv_basic | 正常CSV | 正確解析所有欄位 |
| CB-11 | test_parse_cb_csv_empty | 空內容 | 返回空列表 |
| CB-12 | test_parse_cb_csv_filter | 多餘標題行 | 正確過濾 |
| CB-13 | test_row_to_item | 有效行 | TpexCbDailyItem |
| CB-14 | test_row_to_item_invalid | 空代號 | None |
| CB-15 | test_item_unique_key | TpexCbDailyItem | "35031A_2024-01-15" |

### TestTpexCbDailyFetch

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| CB-20 | test_fetch_daily_success | 返回 SpiderResponse |
| CB-21 | test_fetch_daily_404 | 返回失敗 response |
| CB-22 | test_fetch_date_range | 迭代所有日期 |

### TestDateRange

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| DR-01 | test_generate_date_range | "2024-01-01", "2024-01-05" | 5個日期 |
| DR-02 | test_generate_date_range_same | "2024-01-01", "2024-01-01" | 1個日期 |
| DR-03 | test_get_months_in_range | "2024-01-01", "2024-03-01" | 3個月 |

### TestDateUtilities

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| DT-01 | test_convert_minguo_date | 正常轉換 |
| DT-02 | test_convert_minguo_date_invalid | ValueError |
| DT-03 | test_is_trading_day_weekend | 週六日返回False |
| DT-04 | test_parse_yyyymmdd | "20240115" -> datetime |

## 整合測試

### Integration Test: 完整抓取流程

```python
def test_full_crawl_pipeline():
    """測試完整爬取->解析->入庫流程"""
    
    # 1. Mock HTTP 回應
    mock_response = create_mock_twse_response()
    
    # 2. 建立 Spider
    pipeline = MemoryPipeline()
    spider = StockDailySpider(pipeline=pipeline)
    
    # 3. 執行抓取
    result = spider.fetch_daily("2330", 2024, 1)
    
    # 4. 驗證結果
    assert result.success
    assert len(spider.items) == 20  # 約20個交易日
    assert pipeline.get_item_count() == 20
    
    # 5. 驗證 Item 欄位
    item = spider.items[0]
    assert item.symbol == "2330"
    assert item.date == "2024-01-15"
    assert item.open_price > 0
    assert item.validate()
```

### Integration Test: 區間抓取

```python
def test_date_range_crawl():
    """測試日期區間抓取"""
    spider = StockDailySpider()
    
    results = spider.fetch_date_range(
        symbol="2330",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    
    assert results["months"] == 1
    assert results["success_count"] >= 0
```

## Mock Data

### TWSE JSON Mock

```python
TWSE_MOCK_RESPONSE = {
    "stat": "OK",
    "date": "20240115",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["113/01/02", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"],
        ["113/01/03", "6,123,456", "138,901,234", "103", "108", "102", "107", "+4", "1,456"]
    ]
}
```

### TPEx CB CSV Mock

```python
TPEX_CB_MOCK_CSV = b"""代號,名稱,標的股票,收盤價,成交量,週轉率,溢價率,轉換價格,餘額
35031A,某可轉債,2330,105.5,1000,0.5,15.2,80.0,50000
35032B,另一可轉債,2317,98.3,500,0.2,8.5,65.0,30000
"""
```

---

## 測試執行指令

```bash
# 執行日行情爬蟲測試
pytest tests/test_framework/test_daily_spider.py -v

# 執行特定測試類別
pytest tests/test_framework/test_daily_spider.py::TestStockDailySpider -v

# 執行整合測試
pytest tests/test_framework/test_daily_spider.py -k "integration" -v

# 產生覆蓋率報告
pytest tests/test_framework/test_daily_spider.py --cov=src/spiders --cov-report=html
```

---

*最後更新：2026-04-16*
