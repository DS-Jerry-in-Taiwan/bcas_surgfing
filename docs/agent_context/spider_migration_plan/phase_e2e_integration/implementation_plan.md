# E2E 整合測試實作計畫

## 1. 測試檔案結構

```
tests/test_framework/test_full_system_integration.py
```

## 2. 測試類別

```python
class TestFullSystemIntegration:
    """全系統整合測試"""
    
    def setup_method(self):
        """測試前準備"""
        # 建立測試用 Pipeline
        # Mock HTTP 回應
        pass
    
    def teardown_method(self):
        """測試後清理"""
        # 清理測試資料
        pass
    
    # ===== 情境 1: 主檔 + 日行情流程 =====
    
    def test_master_then_daily_flow(self):
        """測試主檔抓取後緊接日行情抓取"""
        
        # Step 1: 抓取股票主檔
        master_spider = StockMasterSpider(pipeline=self.pipeline)
        master_response = master_spider.fetch_twse()
        
        # Step 2: 從主檔取得 symbol 清單
        symbols = [item.symbol for item in master_spider.get_items()][:3]
        
        # Step 3: 抓取日行情
        daily_spider = StockDailySpider(pipeline=self.pipeline)
        for symbol in symbols:
            daily_spider.fetch_daily(symbol, 2024, 1)
        
        # Step 4: 驗證
        assert len(daily_spider.get_items()) > 0
    
    # ===== 情境 2: 去重驗證 =====
    
    def test_deduplication_on_second_run(self):
        """測試二次執行時去重"""
        
        # Step 1: 首次寫入
        pipeline = PostgresPipeline(table_name="stock_daily")
        spider = StockDailySpider(pipeline=pipeline)
        
        item1 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        pipeline.save_items(item1)
        
        initial_count = self._get_db_count("stock_daily")
        
        # Step 2: 二次寫入相同 unique_key
        item2 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            close_price=106.0,  # 不同收盤價
            high_price=107.0,
            low_price=99.0,
            volume=1100000
        )
        pipeline.save_items(item2)
        pipeline.close()
        
        # Step 3: 驗證記錄數不變
        final_count = self._get_db_count("stock_daily")
        assert final_count == initial_count
        
        # Step 4: 驗證 updated_at 更新
        updated_at = self._get_updated_at("stock_daily", "2330_2024-01-15")
        assert updated_at > initial_updated_at
    
    # ===== 情境 3: 多表同時寫入 =====
    
    def test_multiple_tables_concurrent_write(self):
        """測試多表同時寫入"""
        
        # 同時寫入股票和 CB 資料
        pass
```

## 3. Mock HTTP 策略

```python
# 使用 unittest.mock.patch 攔截 requests.get
TWSE_MOCK = {
    "stat": "OK",
    "fields": [...],
    "data": [...]
}

TPEX_CB_MOCK = b"""代號,名稱,標的股票,...
"""
```

## 4. 資料庫隔離策略

```python
@pytest.fixture
def test_db():
    """建立測試用資料庫"""
    # 1. 建立隔離的 schema
    # 2. 執行測試
    # 3. 清理
```

## 5. 測試資料

### TWSE 股票主檔 Mock

```python
TWSE_MASTER_HTML = """
<table>
<tr><th>有價證券代號及名稱</th></tr>
<tr><td>2330　台積電</td></tr>
<tr><td>2317　鴻海</td></tr>
</table>
"""
```

### TWSE 日行情 Mock

```python
TWSE_DAILY_JSON = {
    "stat": "OK",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["113/01/15", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"]
    ]
}
```

---

*最後更新：2026-04-16*
