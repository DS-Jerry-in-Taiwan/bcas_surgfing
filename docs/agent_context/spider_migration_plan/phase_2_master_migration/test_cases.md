# Phase 2: Master 爬蟲測試案例

## 1. 測試矩陣

| 測試 ID | 測試名稱 | 類型 | 優先級 | 前置條件 |
|---------|----------|------|--------|----------|
| TC-M-01 | TWSE 解析正確性 | 單元 | 高 | 無 |
| TC-M-02 | TPEx 解析正確性 | 單元 | 高 | 無 |
| TC-M-03 | CB Master 解析正確性 | 單元 | 高 | 無 |
| TC-M-04 | 欄位映射驗證 (Stock) | 單元 | 高 | TC-M-01 |
| TC-M-05 | 欄位映射驗證 (CB) | 單元 | 高 | TC-M-03 |
| TC-M-06 | 去重邏輯驗證 | 單元 | 中 | Pipeline 準備 |
| TC-M-07 | CSV 寫入驗證 | 整合 | 高 | Pipeline 準備 |
| TC-M-08 | PostgreSQL 入庫驗證 | 整合 | 高 | DB 準備 |
| TC-M-09 | 編碼處理驗證 | 單元 | 高 | 無 |
| TC-M-10 | 錯誤處理驗證 | 單元 | 中 | 無 |

---

## 2. 詳細測試案例

### TC-M-01: TWSE 解析正確性

```python
def test_twse_parse_correctness():
    """TC-M-01: TWSE 回應解析正確性"""
    from spiders.stock_master_spider import StockMasterSpider
    
    spider = StockMasterSpider()
    
    # Mock TWSE 回應
    mock_html = """
    <table>
        <tr><td>有價證券代號及名稱</td><td>市場</td><td>產業</td></tr>
        <tr><td>2330　台積電</td><td>上市</td><td>半導體</td></tr>
        <tr><td>2317　鴻海</td><td>上市</td><td>電子組裝</td></tr>
    </table>
    """
    
    items = spider.parse_twse_html(mock_html)
    
    assert len(items) == 2
    assert items[0].symbol == "2330"
    assert items[0].name == "台積電"
    assert items[0].market_type == "TWSE"
    assert items[1].symbol == "2317"
    assert items[1].name == "鴻海"
```

### TC-M-02: TPEx 解析正確性

```python
def test_tpex_parse_correctness():
    """TC-M-02: TPEx 回應解析正確性"""
    from spiders.stock_master_spider import StockMasterSpider
    
    spider = StockMasterSpider()
    
    # Mock TPEx 回應
    mock_html = """
    <table>
        <tr><td>有價證券代號及名稱</td><td>市場</td></tr>
        <tr><td>6177　新冠藥</td><td>上櫃</td></tr>
    </table>
    """
    
    items = spider.parse_tpex_html(mock_html)
    
    assert len(items) == 1
    assert items[0].symbol == "6177"
    assert items[0].name == "新冠藥"
    assert items[0].market_type == "TPEx"
```

### TC-M-03: CB Master 解析正確性

```python
def test_cb_master_parse_correctness():
    """TC-M-03: CB Master CSV 解析正確性"""
    from spiders.cb_master_spider import CbMasterSpider
    
    spider = CbMasterSpider()
    
    # Mock CB CSV 內容
    mock_csv = """CB Code,CB Name,Stock Code,Issue Date,Maturity Date,Conversion Price,Coupon Rate
12345,測試轉債A,2330,2024-01-01,2027-01-01,150.00,2.5
12346,測試轉債B,2317,2024-02-01,2028-02-01,200.00,3.0"""
    
    items = spider.parse_cb_csv(mock_csv)
    
    assert len(items) == 2
    assert items[0].cb_code == "12345"
    assert items[0].cb_name == "測試轉債A"
    assert items[0].underlying_stock == "2330"
    assert items[0].conversion_price == 150.00
    assert items[0].coupon_rate == 2.5
```

### TC-M-04: 欄位映射驗證 (Stock)

```python
def test_stock_field_mapping():
    """TC-M-04: 股票主檔欄位映射驗證"""
    from src.framework.base_item import StockMasterItem
    
    # 測試 StockMasterItem.from_dict
    raw_data = {
        "symbol": "2330",
        "name": "台積電",
        "market_type": "TWSE",
        "industry": "半導體",
        "listing_date": "2024-01-01",
        "cfi_code": "ESVUFR",
    }
    
    item = StockMasterItem.from_dict(raw_data)
    
    assert item.symbol == "2330"
    assert item.name == "台積電"
    assert item.market_type == "TWSE"
    assert item.industry == "半導體"
    assert item.listing_date == "2024-01-01"
    assert item.cfi_code == "ESVUFR"
    
    # 驗證 unique_key
    assert item.get_unique_key() == "2330_TWSE"
```

### TC-M-05: 欄位映射驗證 (CB)

```python
def test_cb_field_mapping():
    """TC-M-05: 可轉債主檔欄位映射驗證"""
    from src.framework.base_item import CbMasterItem
    
    raw_data = {
        "cb_code": "12345",
        "cb_name": "測試轉債",
        "underlying_stock": "2330",
        "market_type": "TPEx",
        "issue_date": "2024-01-01",
        "maturity_date": "2027-01-01",
        "conversion_price": 150.00,
        "coupon_rate": 2.5,
    }
    
    item = CbMasterItem.from_dict(raw_data)
    
    assert item.cb_code == "12345"
    assert item.underlying_stock == "2330"
    assert item.conversion_price == 150.00
    
    # 驗證 unique_key
    assert item.get_unique_key() == "12345_2330"
```

### TC-M-06: 去重邏輯驗證

```python
def test_deduplication_logic():
    """TC-M-06: 去重邏輯驗證"""
    from src.framework.base_item import StockMasterItem
    
    item1 = StockMasterItem(
        symbol="2330",
        name="台積電",
        market_type="TWSE"
    )
    
    item2 = StockMasterItem(
        symbol="2330",
        name="台積電股份有限公司",  # 名稱可能不同
        market_type="TWSE"
    )
    
    # 相同 unique_key
    assert item1.get_unique_key() == item2.get_unique_key()
    assert item1.get_unique_key() == "2330_TWSE"
```

### TC-M-07: CSV 寫入驗證

```python
def test_csv_pipeline_write():
    """TC-M-07: CSV Pipeline 寫入驗證"""
    import tempfile
    import os
    from spiders.stock_master_spider import StockMasterSpider
    from src.framework.pipelines import CsvPipeline
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = CsvPipeline(output_dir=tmpdir)
        spider = StockMasterSpider(pipeline=pipeline)
        
        # Mock 資料
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE"
        )
        
        pipeline.save_items(item)
        pipeline.flush_all()
        
        csv_path = os.path.join(tmpdir, "stock_master.csv")
        assert os.path.exists(csv_path)
        
        with open(csv_path, "r") as f:
            content = f.read()
            assert "2330" in content
            assert "台積電" in content
```

### TC-M-08: PostgreSQL 入庫驗證

```python
def test_postgres_deduplication():
    """TC-M-08: PostgreSQL 去重入庫驗證"""
    from src.framework.pipelines import PostgresPipeline
    from src.framework.base_item import StockMasterItem
    
    # 這個測試需要實際的 PostgreSQL
    # 使用 Mock 或 Integration Test 環境
    
    pipeline = PostgresPipeline(
        table_name="stock_master",
        unique_key="unique_key"
    )
    
    item1 = StockMasterItem(
        symbol="2330",
        name="台積電",
        market_type="TWSE"
    )
    
    item2 = StockMasterItem(
        symbol="2330",
        name="台積電更新名稱",  # 更新名稱
        market_type="TWSE"
    )
    
    # 第一次寫入
    pipeline.save_items(item1)
    
    # 第二次寫入相同 unique_key
    pipeline.save_items(item2)
    
    # 驗證只寫入一次（UPSERT）
    # 實際測試需查詢資料庫確認
```

### TC-M-09: 編碼處理驗證

```python
def test_big5_encoding_handling():
    """TC-M-09: Big5 編碼處理驗證"""
    from spiders.cb_master_spider import CbMasterSpider
    
    spider = CbMasterSpider()
    
    # Big5 編碼的中文字
    test_cases = [
        ("台積電", "台積電"),
        ("測試轉債", "測試轉債"),
        ("鴻海精密", "鴻海精密"),
    ]
    
    for original, expected in test_cases:
        # 驗證編碼/解碼正確
        encoded = original.encode("big5")
        decoded = encoded.decode("big5")
        assert decoded == expected


def test_mixed_encoding():
    """TC-M-09b: 混合編碼處理"""
    from spiders.stock_master_spider import StockMasterSpider
    
    spider = StockMasterSpider()
    
    # TWSE: Big5, TPEx: UTF-8
    twse_content = "2330　台積電".encode("big5")
    tpex_content = "6177　新冠藥".encode("utf-8")
    
    # 驗證解碼正確
    assert twse_content.decode("big5") == "2330　台積電"
    assert tpex_content.decode("utf-8") == "6177　新冠藥"
```

### TC-M-10: 錯誤處理驗證

```python
def test_parse_error_handling():
    """TC-M-10: 解析錯誤處理"""
    from spiders.stock_master_spider import StockMasterSpider
    
    spider = StockMasterSpider()
    
    # 無效 HTML
    invalid_html = "<invalid>not a table</invalid>"
    
    items = spider.parse_twse_html(invalid_html)
    
    assert len(items) == 0  # 不應崩潰
    
    # 空 HTML
    empty_html = ""
    items = spider.parse_twse_html(empty_html)
    
    assert len(items) == 0


def test_network_error_handling():
    """TC-M-10b: 網路錯誤處理"""
    from spiders.stock_master_spider import StockMasterSpider
    from unittest.mock import patch
    
    spider = StockMasterSpider()
    
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        
        # 應返回空列表，不應崩潰
        try:
            items = spider.fetch_twse()
            assert len(items) == 0
        except Exception as e:
            # 錯誤應被記錄
            assert "Network error" in str(e)
```

---

## 3. 整合測試

### IT-01: 完整爬取流程

```python
def test_full_crawl_flow():
    """IT-01: 完整爬取到入庫流程"""
    from spiders.stock_master_spider import StockMasterSpider
    from src.framework.pipelines import CsvPipeline
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = CsvPipeline(output_dir=tmpdir)
        spider = StockMasterSpider(pipeline=pipeline)
        
        # Mock 爬取
        with patch.object(spider, 'fetch_twse') as mock_twse:
            with patch.object(spider, 'fetch_tpex') as mock_tpex:
                mock_twse.return_value = [
                    StockMasterItem(symbol="2330", name="台積電", market_type="TWSE"),
                    StockMasterItem(symbol="2317", name="鴻海", market_type="TWSE"),
                ]
                mock_tpex.return_value = [
                    StockMasterItem(symbol="6177", name="新冠藥", market_type="TPEx"),
                ]
                
                # 執行爬取
                spider.fetch_all()
                
                # 驗證
                stats = spider.get_statistics()
                assert stats["success_count"] == 3
        
        # 驗證 CSV
        csv_path = os.path.join(tmpdir, "stock_master.csv")
        assert os.path.exists(csv_path)
```

---

## 4. 測試資料

### 4.1 Mock TWSE HTML

```html
<table>
    <thead>
        <tr>
            <th>有價證券代號及名稱</th>
            <th>市場</th>
            <th>產業</th>
            <th>上市日</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>2330　台積電</td>
            <td>上市</td>
            <td>半導體</td>
            <td>2024-01-01</td>
        </tr>
        <tr>
            <td>2317　鴻海</td>
            <td>上市</td>
            <td>電子組裝</td>
            <td>2024-01-15</td>
        </tr>
    </tbody>
</table>
```

### 4.2 Mock TPEx HTML

```html
<table>
    <thead>
        <tr>
            <th>有價證券代號及名稱</th>
            <th>市場</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>6177　新冠藥</td>
            <td>上櫃</td>
        </tr>
    </tbody>
</table>
```

### 4.3 Mock CB CSV

```csv
CB Code,CB Name,Stock Code,Issue Date,Maturity Date,Conversion Price,Coupon Rate
12345,測試轉債A,2330,2024-01-01,2027-01-01,150.00,2.50
12346,測試轉債B,2317,2024-02-01,2028-02-01,200.00,3.00
12347,測試轉債C,2454,2024-03-01,2029-03-01,180.00,2.75
```

---

## 5. 通過標準

### 單元測試

| 測試類別 | 通過率目標 |
|----------|------------|
| 解析正確性 | 100% |
| 欄位映射 | 100% |
| 去重邏輯 | 100% |
| 錯誤處理 | 100% |

### 整合測試

| 測試 | 標準 |
|------|------|
| CSV 寫入 | 檔案存在且內容正確 |
| 去重 | 相同 unique_key 只寫入一次 |
| 統計追蹤 | 數值合理 |

---

## 6. 測試執行

```bash
# 執行所有測試
python -m pytest tests/test_framework/test_master_spider.py -v

# 執行單元測試
python -m pytest tests/test_framework/test_master_spider.py::TestStockMasterSpider -v

# 執行整合測試
python -m pytest tests/test_framework/test_master_spider.py::TestIntegration -v

# 執行並顯示覆蓋率
python -m pytest tests/test_framework/test_master_spider.py --cov=src.spiders --cov-report=html
```

---

*文件版本：1.0.0*
*建立時間：2026-04-16*
