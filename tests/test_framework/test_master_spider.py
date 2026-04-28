"""
StockMasterSpider & CbMasterSpider 單元測試
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from io import BytesIO, StringIO

import sys
sys.path.insert(0, "src")

from spiders.stock_master_spider import StockMasterSpider
from spiders.cb_master_spider import CbMasterSpider
from framework.base_item import StockMasterItem, CbMasterItem
from framework.pipelines import MemoryPipeline, CsvPipeline


class TestStockMasterSpider:
    """StockMasterSpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = StockMasterSpider(pipeline=self.pipeline)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.spider is not None
        assert self.spider.request_count == 0
        assert self.spider.error_count == 0
        assert self.spider.items == []
        assert self.spider.twse_items == []
        assert self.spider.tpex_items == []
    
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
        assert "success_rate" in stats
        assert "total_items" in stats
        assert "twse_count" in stats
        assert "tpex_count" in stats
        
        assert stats["total_items"] == 0
        assert stats["twse_count"] == 0
        assert stats["tpex_count"] == 0
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.spider)
        assert "StockMasterSpider" in repr_str
    
    def test_urls(self):
        """測試 URL 常量"""
        assert "twse.com.tw" in self.spider.TWSE_URL
        assert "tpex.org.tw" in self.spider.TPEX_URL


class TestStockMasterSpiderParse:
    """StockMasterSpider 解析測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = StockMasterSpider(pipeline=self.pipeline)
    
    def test_parse_twse_html_basic(self):
        """測試 TWSE HTML 解析 - 基本"""
        html = """
        <table>
            <tr><th>有價證券代號及名稱</th><th>國際證券辨識號碼(ISIN)</th></tr>
            <tr><td>2330　台積電</td><td>TW0002330008</td></tr>
            <tr><td>2317　鴻海</td><td>TW0002317005</td></tr>
        </table>
        """
        items = self.spider.parse_twse_html(html)
        
        assert len(items) == 2
        assert items[0].symbol == "2330"
        assert items[0].name == "台積電"
        assert items[0].market_type == "TWSE"
        assert items[0].source_type == "twse"
    
    def test_parse_twse_html_empty(self):
        """測試 TWSE HTML 解析 - 空內容"""
        html = "<html><body></body></html>"
        items = self.spider.parse_twse_html(html)
        assert len(items) == 0
    
    def test_parse_twse_html_no_table(self):
        """測試 TWSE HTML 解析 - 無表格"""
        html = "<html><body><p>No table</p></body></html>"
        items = self.spider.parse_twse_html(html)
        assert len(items) == 0
    
    def test_parse_tpex_html_basic(self):
        """測試 TPEx HTML 解析 - 基本"""
        html = """
        <table>
            <tr><th>有價證券代號及名稱</th><th>國際證券辨識號碼(ISIN)</th></tr>
            <tr><td>6457　紘康</td><td>TW0006457006</td></tr>
        </table>
        """
        items = self.spider.parse_tpex_html(html)
        
        assert len(items) == 1
        assert items[0].symbol == "6457"
        assert items[0].name == "紘康"
        assert items[0].market_type == "TPEx"
        assert items[0].source_type == "tpex"
    
    def test_parse_twse_html_filter_invalid(self):
        """測試 TWSE HTML 解析 - 過濾無效行"""
        html = """
        <table>
            <tr><th>有價證券代號及名稱</th></tr>
            <tr><td></td></tr>
            <tr><td>2330</td></tr>
            <tr><td>　台積電</td></tr>
        </table>
        """
        items = self.spider.parse_twse_html(html)
        assert len(items) == 0
    
    def test_unique_key(self):
        """測試 unique key"""
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE",
            source_url="https://example.com",
            source_type="twse"
        )
        
        assert item.get_unique_key() == "2330_TWSE"


class TestStockMasterSpiderFetch:
    """StockMasterSpider 爬取測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = StockMasterSpider(pipeline=self.pipeline)
    
    @patch('spiders.stock_master_spider.requests.get')
    def test_fetch_twse_success(self, mock_get):
        """測試 TWSE 抓取成功"""
        html = """
        <table>
            <tr><th>有價證券代號及名稱</th></tr>
            <tr><td>2330　台積電</td></tr>
        </table>
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_twse()
        
        assert response.success is True
        assert response.data["count"] == 1
        assert len(self.spider.twse_items) == 1
    
    @patch('spiders.stock_master_spider.requests.get')
    def test_fetch_twse_error(self, mock_get):
        """測試 TWSE 抓取錯誤"""
        mock_get.side_effect = Exception("Network error")
        
        response = self.spider.fetch_twse()
        
        assert response.success is False
        assert "Network error" in response.error
    
    @patch('spiders.stock_master_spider.requests.get')
    def test_fetch_tpex_success(self, mock_get):
        """測試 TPEx 抓取成功"""
        html = """
        <table>
            <tr><th>有價證券代號及名稱</th></tr>
            <tr><td>6457　紘康</td></tr>
        </table>
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_tpex()
        
        assert response.success is True
        assert response.data["count"] == 1
        assert len(self.spider.tpex_items) == 1
    
    def test_fetch_all(self):
        """測試 fetch_all"""
        with patch.object(self.spider, 'fetch_twse') as mock_twse, \
             patch.object(self.spider, 'fetch_tpex') as mock_tpex:
            
            mock_twse.return_value = Mock(success=True)
            mock_tpex.return_value = Mock(success=True)
            
            results = self.spider.fetch_all()
            
            assert "twse" in results
            assert "tpex" in results


class TestStockMasterSpiderCsvPipeline:
    """StockMasterSpider CSV Pipeline 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """測試後清理"""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_csv_pipeline_manual(self):
        """測試手動寫入 CSV"""
        import os
        
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        spider = StockMasterSpider(pipeline=pipeline)
        
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE",
            source_url="https://example.com",
            source_type="twse"
        )
        
        spider.pipeline.save_items(item)
        spider.pipeline.flush_all()
        
        csv_path = os.path.join(self.test_dir, "stock_master.csv")
        assert os.path.exists(csv_path)


class TestCbMasterSpider:
    """CbMasterSpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = CbMasterSpider(pipeline=self.pipeline)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.spider is not None
        assert self.spider.request_count == 0
        assert self.spider.error_count == 0
        assert self.spider.items == []
        assert self.spider.days_back == 30
    
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
        assert "success_rate" in stats
        assert "total_items" in stats
        assert "unique_cb_count" in stats
        assert "unique_stock_count" in stats
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.spider)
        assert "CbMasterSpider" in repr_str


class TestCbMasterSpiderUrl:
    """CbMasterSpider URL 建構測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.spider = CbMasterSpider()
    
    def test_generate_dates(self):
        """測試日期生成"""
        dates = self.spider._generate_dates(3)
        
        assert len(dates) == 3
        for date in dates:
            assert len(date) == 8
            assert date.isdigit()
    
    def test_build_url(self):
        """測試 URL 建構"""
        url = self.spider._build_url("20240115")
        
        assert "2024" in url
        assert "202401" in url
        assert "RSdrs001.20240115-C.csv" in url


class TestCbMasterSpiderParse:
    """CbMasterSpider 解析測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.spider = CbMasterSpider()
    
    def test_parse_cb_csv_basic(self):
        """測試 CB CSV 解析 - 基本（HEADER/BODY 格式）"""
        csv_content = """TITLE,CB Master Data
DATADATE,test
HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格
BODY,"35031A","TestCB1","2025/01/01","2028/12/31","100.0000"
BODY,"35032A","TestCB2","2025/06/01","2029/05/31","200.0000"
""".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "20240115")
        
        assert len(items) == 2
        assert items[0].cb_code == "35031A"
        assert items[0].cb_name == "TestCB1"
        assert items[0].market_type == "TPEx"
    
    def test_parse_cb_csv_with_gloss_header(self):
        """測試 CB CSV 解析 - 含 HEADER 行（TPEx 格式）"""
        csv_content = """TITLE,test
DATADATE,test
HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格
BODY,"35031A","TestCB1","2025/01/01","2028/12/31","100.0000"
BODY,"35032A","TestCB2","2025/06/01","2029/05/31","200.0000"
""".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "20240115")
        
        assert len(items) == 2
        assert items[0].cb_code == "35031A"
        assert items[0].cb_name == "TestCB1"
    
    def test_parse_cb_csv_empty(self):
        """測試 CB CSV 解析 - 空內容"""
        csv_content = """TITLE,test
DATADATE,test
HEADER,債券代碼,債券簡稱
""".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "20240115")
        assert len(items) == 0
    
    def test_parse_cb_csv_no_data(self):
        """測試 CB CSV 解析 - 無資料行"""
        csv_content = """TITLE,test
DATADATE,test
HEADER,債券代碼,債券簡稱
""".encode("big5")
        items = self.spider.parse_cb_csv(csv_content, "20240115")
        assert len(items) == 0
    
    def test_row_to_item(self):
        """測試行轉換為 Item（使用 column_mapping 中的中文欄位名）"""
        import pandas as pd
        
        row = pd.Series({
            "債券代碼": "35031A",
            "債券簡稱": "TestCB",
            "轉換起日": "2025/01/01",
        })
        
        item = self.spider._row_to_item(row, "20240115")
        
        assert item is not None
        assert item.cb_code == "35031A"
        assert item.cb_name == "TestCB"
    
    def test_row_to_item_invalid(self):
        """測試行轉換為 Item - 無效行（無 cb_code）"""
        import pandas as pd
        
        row = pd.Series({
            "債券代碼": "",
            "債券簡稱": "Test",
        })
        
        item = self.spider._row_to_item(row, "20240115")
        assert item is None


class TestCbMasterSpiderFetch:
    """CbMasterSpider 爬取測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = CbMasterSpider(pipeline=self.pipeline)
    
    @patch('spiders.cb_master_spider.requests.get')
    def test_fetch_cb_master_success(self, mock_get):
        """測試 CB Master 抓取成功"""
        csv_content = """TITLE,test
DATADATE,test
HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格
BODY,"35031A","TestCB","2025/01/01","2028/12/31","100.0000"
""".encode("big5")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = csv_content
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_cb_master("20240115")
        
        assert response.success is True
        assert len(self.spider.items) == 1
    
    @patch('spiders.cb_master_spider.requests.get')
    def test_fetch_cb_master_404(self, mock_get):
        """測試 CB Master 404 錯誤"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        response = self.spider.fetch_cb_master("20240115")
        
        assert response.success is False
    
    @patch('spiders.cb_master_spider.requests.get')
    def test_fetch_cb_master_error(self, mock_get):
        """測試 CB Master 網路錯誤"""
        mock_get.side_effect = Exception("Connection timeout")
        
        response = self.spider.fetch_cb_master("20240115")
        
        assert response.success is False
        assert "Connection timeout" in response.error
    
    def test_fetch_all(self):
        """測試 fetch_all"""
        with patch.object(self.spider, 'fetch_cb_master') as mock_fetch:
            mock_fetch.return_value = Mock(success=True)
            
            results = self.spider.fetch_all()
            
            assert "dates" in results
            assert "items_count" in results
            assert "errors" in results


class TestCbMasterSpiderCsvPipeline:
    """CbMasterSpider CSV Pipeline 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """測試後清理"""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_csv_pipeline_manual(self):
        """測試手動寫入 CSV"""
        import os
        
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        spider = CbMasterSpider(pipeline=pipeline)
        
        item = CbMasterItem(
            cb_code="35031A",
            cb_name="TestCB",
            underlying_stock="2330",
            market_type="TPEx",
            source_url="https://example.com",
            source_type="tpex_cb"
        )
        
        spider.pipeline.save_items(item)
        spider.pipeline.flush_all()
        
        csv_path = os.path.join(self.test_dir, "cb_master.csv")
        assert os.path.exists(csv_path)


class TestCbMasterSpiderDeduplication:
    """CbMasterSpider 去重測試"""
    
    def test_unique_key(self):
        """測試 unique key"""
        item = CbMasterItem(
            cb_code="35031A",
            cb_name="TestCB",
            underlying_stock="2330",
            market_type="TPEx",
            source_url="https://example.com",
            source_type="tpex_cb"
        )
        
        assert item.get_unique_key() == "35031A_2330"


class TestSpiderClose:
    """爬蟲關閉測試"""
    
    def test_stock_spider_close(self):
        """測試 StockMasterSpider 關閉"""
        pipeline = MemoryPipeline()
        spider = StockMasterSpider(pipeline=pipeline)
        
        spider.close()
    
    def test_cb_spider_close(self):
        """測試 CbMasterSpider 關閉"""
        pipeline = MemoryPipeline()
        spider = CbMasterSpider(pipeline=pipeline)
        
        spider.close()


class TestSpiderDeduplication:
    """去重測試"""
    
    def test_deduplication_concept(self):
        """測試去重概念"""
        pipeline = MemoryPipeline()
        spider = StockMasterSpider(pipeline=pipeline)
        
        item1 = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE",
            source_url="https://example.com",
            source_type="twse"
        )
        
        item2 = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE",
            source_url="https://example.com",
            source_type="twse"
        )
        
        pipeline.save_items(item1)
        pipeline.save_items(item2)
        
        assert item1.get_unique_key() == item2.get_unique_key()
