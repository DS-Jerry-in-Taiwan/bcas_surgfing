"""
ExampleSpider 單元測試
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "src")

from spiders.example_spider import ExampleSpider
from framework.base_item import StockDailyItem
from framework.pipelines import MemoryPipeline, CsvPipeline


class TestExampleSpider:
    """ExampleSpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = ExampleSpider(pipeline=self.pipeline)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.spider is not None
        assert self.spider.success_count == 0
        assert self.spider.error_count == 0
    
    def test_parse_price(self):
        """測試價格解析"""
        assert self.spider._parse_price("1,000.50") == 1000.5
        assert self.spider._parse_price("100") == 100.0
        assert self.spider._parse_price("") == 0.0
        assert self.spider._parse_price("invalid") == 0.0
    
    def test_parse_volume(self):
        """測試成交量解析"""
        assert self.spider._parse_volume("1,000,000") == 1000000
        assert self.spider._parse_volume("1000") == 1000
        assert self.spider._parse_volume("") == 0
    
    def test_convert_date(self):
        """測試民國年轉換"""
        result = self.spider._convert_date("113/01/15")
        assert result == "2024-01-15"
        
        result = self.spider._convert_date("112/12/31")
        assert result == "2023-12-31"
    
    def test_get_items(self):
        """測試取得 Items"""
        items = self.spider.get_items()
        assert isinstance(items, list)
        assert len(items) == 0
    
    def test_get_statistics(self):
        """測試取得統計"""
        stats = self.spider.get_statistics()
        
        assert "request_count" in stats
        assert "success_count" in stats
        assert "error_count" in stats
        assert "success_rate" in stats
        assert "items_collected" in stats
        
        assert stats["success_count"] == 0
        assert stats["error_count"] == 0
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.spider)
        assert "ExampleSpider" in repr_str


class TestExampleSpiderFetch:
    """ExampleSpider 爬取測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.spider = ExampleSpider(pipeline=self.pipeline)
    
    def test_parse_record(self):
        """測試記錄解析"""
        record = ["113/01/02", "1,000,000", "10,000,000", "100", "105", "99", "103"]
        
        item = self.spider._parse_record(record, "2330", 2024, 1)
        
        assert item is not None
        assert item.symbol == "2330"
        assert item.open_price == 100.0
        assert item.high_price == 105.0
        assert item.low_price == 99.0
        assert item.close_price == 103.0
        assert item.volume == 1000000
    
    def test_batch_fetch(self):
        """測試批次爬取"""
        with patch.object(self.spider, 'fetch_stock') as mock_fetch:
            mock_fetch.return_value = Mock(success=True)
            
            stocks = ["2330", "2317", "2454"]
            self.spider.batch_fetch(stocks, 2024, 1)
            
            assert mock_fetch.call_count == 3


class TestExampleSpiderCsvPipeline:
    """ExampleSpider CSV Pipeline 測試"""
    
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
        
        # 手動添加 Item
        item = StockDailyItem(
            symbol="2330",
            date="2024-01-02",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        pipeline.save_items(item)
        pipeline.flush_all()
        
        csv_path = os.path.join(self.test_dir, "stock_daily.csv")
        assert os.path.exists(csv_path)
        
        with open(csv_path, "r") as f:
            content = f.read()
            assert "symbol" in content
            assert "2330" in content


class TestExampleSpiderDeduplication:
    """去重測試"""
    
    def test_deduplication_concept(self):
        """測試去重概念"""
        pipeline = MemoryPipeline()
        
        item1 = StockDailyItem(
            symbol="2330",
            date="2024-01-02",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        item2 = StockDailyItem(
            symbol="2330",
            date="2024-01-02",  # 相同鍵
            open_price=101.0,
            high_price=106.0,
            low_price=100.0,
            close_price=104.0,
            volume=1100000
        )
        
        pipeline.save_items(item1)
        pipeline.save_items(item2)
        
        # 驗證 unique key 相同
        assert item1.get_unique_key() == item2.get_unique_key()
        assert len(pipeline.get_items()) == 2  # Pipeline 不自動去重，需由 DB 層處理


class TestExampleSpiderStatistics:
    """統計追蹤測試"""
    
    def test_statistics_tracking(self):
        """測試統計追蹤"""
        spider = ExampleSpider()
        
        # 模擬增加統計
        spider.success_count = 10
        spider.error_count = 2
        
        stats = spider.get_statistics()
        
        assert stats["request_count"] == 12
        assert stats["success_count"] == 10
        assert stats["error_count"] == 2
        assert stats["success_rate"] == pytest.approx(83.33, rel=0.1)
        assert stats["items_collected"] == 0
    
    def test_statistics_zero_division(self):
        """測試零除保護"""
        spider = ExampleSpider()
        
        stats = spider.get_statistics()
        
        # 零請求時應返回 100% 成功率
        assert stats["success_rate"] == 100.0
