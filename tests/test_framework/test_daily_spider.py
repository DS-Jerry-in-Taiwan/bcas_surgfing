"""
StockDailySpider & TpexCbDailySpider 單元測試
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO

import sys
sys.path.insert(0, "src")

from spiders.stock_daily_spider import StockDailySpider
from spiders.tpex_cb_daily_spider import TpexCbDailySpider
from framework.base_item import StockDailyItem, TpexCbDailyItem
from framework.pipelines import MemoryPipeline, CsvPipeline


class TestStockDailySpider:
    """StockDailySpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = StockDailySpider(pipeline=self.pipeline)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.spider is not None
        assert self.spider.request_count == 0
        assert self.spider.error_count == 0
        assert self.spider.items == []
    
    def test_get_items(self):
        """測試取得 Items"""
        items = self.spider.get_items()
        assert isinstance(items, list)
        assert len(items) == 0
    
    def test_get_statistics(self):
        """測試取得統計"""
        stats = self.spider.get_statistics()
        
        assert "request_count" in stats
        assert "error_count" in stats
        assert "total_items" in stats
    
    def test_urls(self):
        """測試 URL 常量"""
        assert "twse.com.tw" in self.spider.TWSE_URL
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.spider)
        assert "StockDailySpider" in repr_str


class TestStockDailyParse:
    """StockDailySpider 解析測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.spider = StockDailySpider()
    
    def test_parse_number_with_comma(self):
        """測試千分位數值解析"""
        assert self.spider._parse_number("1,234,567") == 1234567
        assert self.spider._parse_number("1,234.56") == 1234.56
        assert self.spider._parse_number("") == 0
        assert self.spider._parse_number("+123") == 123
    
    def test_parse_number_invalid(self):
        """測試無效數值解析"""
        assert self.spider._parse_number("invalid") == 0
        assert self.spider._parse_number(None) == 0
    
    def test_convert_minguo_date(self):
        """測試民國年轉換"""
        assert self.spider._convert_minguo_date("113/01/15") == "2024-01-15"
        assert self.spider._convert_minguo_date("112/12/31") == "2023-12-31"
        assert self.spider._convert_minguo_date("001/01/01") == "1912-01-01"
    
    def test_parse_twse_json_basic(self):
        """測試 TWSE JSON 解析 - 基本"""
        data = {
            "stat": "OK",
            "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
            "data": [
                ["113/01/02", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"],
                ["113/01/03", "6,123,456", "138,901,234", "103", "108", "102", "107", "+4", "1,456"]
            ]
        }
        
        items = self.spider.parse_twse_json(data, "2330")
        
        assert len(items) == 2
        assert items[0].symbol == "2330"
        assert items[0].date == "2024-01-02"
        assert items[0].open_price == 100.0
        assert items[0].high_price == 105.0
        assert items[0].low_price == 99.0
        assert items[0].close_price == 103.0
        assert items[0].volume == 5234567
        assert items[0].transaction_count == 1234
        assert items[0].validate()
    
    def test_parse_twse_json_empty(self):
        """測試 TWSE JSON 解析 - 空資料"""
        data = {"stat": "OK", "fields": [], "data": []}
        items = self.spider.parse_twse_json(data, "2330")
        assert len(items) == 0
    
    def test_parse_twse_json_invalid(self):
        """測試 TWSE JSON 解析 - 無效資料"""
        data = {"stat": "OK", "fields": [], "data": None}
        items = self.spider.parse_twse_json(data, "2330")
        assert len(items) == 0


class TestStockDailyFetch:
    """StockDailySpider 爬取測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = StockDailySpider(pipeline=self.pipeline)
    
    @patch('spiders.stock_daily_spider.requests.get')
    def test_fetch_daily_success(self, mock_get):
        """測試抓取成功"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "stat": "OK",
            "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
            "data": [["113/01/02", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"]]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_daily("2330", 2024, 1)
        
        assert response.success is True
        assert len(self.spider.items) == 1
    
    @patch('spiders.stock_daily_spider.requests.get')
    def test_fetch_daily_api_error(self, mock_get):
        """測試 API 錯誤"""
        mock_response = Mock()
        mock_response.json.return_value = {"stat": "ERROR", "message": "Stock not found"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_daily("99999", 2024, 1)
        
        assert response.success is False
    
    @patch('spiders.stock_daily_spider.requests.get')
    def test_fetch_daily_network_error(self, mock_get):
        """測試網路錯誤"""
        mock_get.side_effect = Exception("Connection timeout")
        
        response = self.spider.fetch_daily("2330", 2024, 1)
        
        assert response.success is False
    
    def test_generate_months_in_range(self):
        """測試月份生成"""
        months = self.spider._generate_months_in_range("2024-01-01", "2024-03-01")
        
        assert len(months) == 3
        assert (2024, 1) in months
        assert (2024, 2) in months
        assert (2024, 3) in months
    
    def test_generate_months_single_month(self):
        """測試單月"""
        months = self.spider._generate_months_in_range("2024-01-01", "2024-01-31")
        
        assert len(months) == 1
        assert (2024, 1) in months
    
    @patch.object(StockDailySpider, 'fetch_daily')
    def test_fetch_date_range(self, mock_fetch):
        """測試日期區間抓取"""
        mock_fetch.return_value = Mock(success=True, data={"count": 20})
        
        results = self.spider.fetch_date_range("2330", "2024-01-01", "2024-01-31")
        
        assert results["symbol"] == "2330"
        assert results["months"] == 1
        assert results["success_count"] == 1


class TestTpexCbDailySpider:
    """TpexCbDailySpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = TpexCbDailySpider(pipeline=self.pipeline)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.spider is not None
        assert self.spider.request_count == 0
        assert self.spider.error_count == 0
        assert self.spider.items == []
    
    def test_get_items(self):
        """測試取得 Items"""
        items = self.spider.get_items()
        assert isinstance(items, list)
        assert len(items) == 0
    
    def test_get_statistics(self):
        """測試取得統計"""
        stats = self.spider.get_statistics()
        
        assert "request_count" in stats
        assert "total_items" in stats
        assert "unique_cb_count" in stats
    
    def test_urls(self):
        """測試 URL 常量"""
        assert "tpex.org.tw" in self.spider.BASE_URL
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.spider)
        assert "TpexCbDailySpider" in repr_str


class TestTpexCbDailyParse:
    """TpexCbDailySpider 解析測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.spider = TpexCbDailySpider()
    
    def test_parse_number(self):
        """測試數值解析"""
        assert self.spider._parse_number(123.45) == 123.45
        assert self.spider._parse_number("1,234.56") == 1234.56
        assert self.spider._parse_number(None) == 0.0
    
    def test_parse_cb_csv_basic(self):
        """測試 CB CSV 解析 - 基本（HEADER/BODY 格式）"""
        csv_content = """HEADER,代號,名稱,收市,單位
BODY,"35031A","TestCB1","105.5","1000"
BODY,"35032B","TestCB2","98.3","500"
""".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "2024-01-15")
        
        assert len(items) == 2
        assert items[0].cb_code == "35031A"
        assert items[0].cb_name == "TestCB1"
        assert items[0].closing_price == 105.5
        assert items[0].volume == 1000.0
        assert items[0].trade_date == "2024-01-15"
        assert items[0].validate()
    
    def test_parse_cb_csv_empty(self):
        """測試 CB CSV 解析 - 空內容"""
        csv_content = b""
        items = self.spider.parse_cb_csv(csv_content, "2024-01-15")
        assert len(items) == 0
    
    def test_parse_cb_csv_no_data(self):
        """測試 CB CSV 解析 - 無資料"""
        csv_content = "HEADER,代號,名稱\n".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "2024-01-15")
        assert len(items) == 0


class TestTpexCbDailyFetch:
    """TpexCbDailySpider 爬取測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = TpexCbDailySpider(pipeline=self.pipeline)
    
    @patch('spiders.tpex_cb_daily_spider.requests.get')
    def test_fetch_daily_success(self, mock_get):
        """測試抓取成功"""
        csv_content = """HEADER,代號,名稱,收市,單位
BODY,"35031A","TestCB","105.5","1000"
""".encode("big5")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = csv_content
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_daily("2024-01-15")
        
        assert response.success is True
        assert len(self.spider.items) == 1
    
    @patch('spiders.tpex_cb_daily_spider.requests.get')
    def test_fetch_daily_network_error(self, mock_get):
        """測試網路錯誤"""
        mock_get.side_effect = Exception("Connection timeout")
        
        response = self.spider.fetch_daily("2024-01-15")
        
        assert response.success is False
    
    def test_generate_dates_in_range(self):
        """測試日期生成"""
        dates = self.spider._generate_dates_in_range("2024-01-01", "2024-01-05")
        
        assert len(dates) == 5
        assert "2024-01-01" in dates
        assert "2024-01-05" in dates
    
    def test_generate_dates_same_day(self):
        """測試同一天"""
        dates = self.spider._generate_dates_in_range("2024-01-01", "2024-01-01")
        
        assert len(dates) == 1
        assert dates[0] == "2024-01-01"
    
    @patch.object(TpexCbDailySpider, 'fetch_daily')
    def test_fetch_date_range(self, mock_fetch):
        """測試日期區間抓取"""
        mock_fetch.return_value = Mock(success=True, data={"count": 10})
        
        results = self.spider.fetch_date_range("2024-01-01", "2024-01-03")
        
        assert results["total_dates"] == 3
        assert results["success_count"] == 3


class TestDailySpiderCsvPipeline:
    """日行情爬蟲 CSV Pipeline 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """測試後清理"""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stock_csv_pipeline(self):
        """測試股票行情 CSV Pipeline"""
        import os
        
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        spider = StockDailySpider(pipeline=pipeline)
        
        item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000,
            source_url="https://example.com",
            source_type="twse_daily"
        )
        
        pipeline.save_items(item)
        pipeline.flush_all()
        
        csv_path = os.path.join(self.test_dir, "stock_daily.csv")
        assert os.path.exists(csv_path)
    
    def test_cb_csv_pipeline(self):
        """測試 CB 行情 CSV Pipeline"""
        import os
        
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        spider = TpexCbDailySpider(pipeline=pipeline)
        
        item = TpexCbDailyItem(
            cb_code="35031A",
            cb_name="TestCB",
            underlying_stock="2330",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000,
            source_url="https://example.com",
            source_type="tpex_cb_daily"
        )
        
        pipeline.save_items(item)
        pipeline.flush_all()
        
        csv_path = os.path.join(self.test_dir, "tpex_cb_daily.csv")
        assert os.path.exists(csv_path)


class TestDateUtilities:
    """日期工具測試"""
    
    def test_stock_item_unique_key(self):
        """測試 StockDailyItem unique_key"""
        item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000,
            source_url="https://example.com",
            source_type="twse_daily"
        )
        
        assert item.get_unique_key() == "2330_2024-01-15"
    
    def test_cb_item_unique_key(self):
        """測試 TpexCbDailyItem unique_key"""
        item = TpexCbDailyItem(
            cb_code="35031A",
            cb_name="TestCB",
            underlying_stock="2330",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000,
            source_url="https://example.com",
            source_type="tpex_cb_daily"
        )
        
        assert item.get_unique_key() == "35031A_2024-01-15"
    
    def test_stock_item_validate(self):
        """測試 StockDailyItem 驗證"""
        item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        assert item.validate() is True
        
        item_empty = StockDailyItem(symbol="", date="")
        assert item_empty.validate() is False
    
    def test_cb_item_validate(self):
        """測試 TpexCbDailyItem 驗證"""
        item = TpexCbDailyItem(
            cb_code="35031A",
            trade_date="2024-01-15",
            closing_price=105.5
        )
        assert item.validate() is True
        
        item_empty = TpexCbDailyItem(cb_code="", trade_date="")
        assert item_empty.validate() is False


class TestSpiderClose:
    """爬蟲關閉測試"""
    
    def test_stock_spider_close(self):
        """測試 StockDailySpider 關閉"""
        pipeline = MemoryPipeline()
        spider = StockDailySpider(pipeline=pipeline)
        spider.close()
    
    def test_cb_spider_close(self):
        """測試 TpexCbDailySpider 關閉"""
        pipeline = MemoryPipeline()
        spider = TpexCbDailySpider(pipeline=pipeline)
        spider.close()
