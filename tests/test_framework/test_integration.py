"""
整合测试 - 测试 Spider -> Pipeline 流程
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.base_spider import BaseSpider, SpiderResponse
from framework.pipelines import CsvPipeline, MemoryPipeline
from framework.base_item import (
    StockDailyItem,
    TpexCbDailyItem,
    CbMasterItem,
)


class TestSpiderToPipelineIntegration:
    """Spider -> Pipeline 整合测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, "test_dir") and shutil.os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_spider_response_to_item_flow(self):
        """测试 SpiderResponse -> Item -> Pipeline 流程"""
        # 1. 模拟 Spider 解析响应
        spider = BaseSpider()
        
        mock_response = Mock()
        mock_response.url = "https://api.twse.com.tw/daily"
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                ["2330", "2026-01-01", "100", "105", "99", "106", "1000000"]
            ]
        }
        
        response = spider.parse_response(mock_response)
        assert response.success is True
        
        # 2. 将响应转换为 Item
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            high_price=106.0,
            low_price=99.0,
            close_price=105.0,
            volume=1000000,
            source_url=response.url,
            source_type="twse"
        )
        
        assert item.symbol == "2330"
        assert item.validate() is True
        
        # 3. 通过 Pipeline 保存
        pipeline = MemoryPipeline()
        pipeline.save_items(item)
        
        assert pipeline.success_count == 1
        assert len(pipeline.get_items()) == 1
    
    def test_batch_crawl_save_flow(self):
        """测试批量爬取保存流程"""
        spider = BaseSpider()
        pipeline = MemoryPipeline()
        
        symbols = ["2330", "2317", "2454"]
        date = "2026-01-01"
        
        for symbol in symbols:
            # 模拟爬取
            response = SpiderResponse(
                success=True,
                data={"symbol": symbol, "price": 100.0},
                url=f"https://api.example.com/{symbol}"
            )
            
            # 转换为 Item
            item = StockDailyItem(
                symbol=symbol,
                date=date,
                open_price=100.0,
                close_price=100.0,
                high_price=100.0,
                low_price=100.0,
                volume=1000000,
                source_url=response.url
            )
            
            pipeline.save_items(item)
        
        assert pipeline.success_count == 3
        assert len(pipeline.get_items()) == 3
        
        # 验证唯一键
        unique_keys = [item.get_unique_key() for item in pipeline.get_items()]
        assert len(unique_keys) == len(set(unique_keys))
    
    def test_csv_pipeline_full_flow(self):
        """测试 CSV Pipeline 完整流程"""
        spider = BaseSpider()
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=2)
        
        items = [
            StockDailyItem(
                symbol="2330",
                date="2026-01-01",
                open_price=100.0,
                close_price=105.0,
                high_price=106.0,
                low_price=99.0,
                volume=1000000
            ),
            StockDailyItem(
                symbol="2317",
                date="2026-01-01",
                open_price=200.0,
                close_price=205.0,
                high_price=206.0,
                low_price=199.0,
                volume=2000000
            ),
        ]
        
        for item in items:
            pipeline.save_items(item)
        
        pipeline.close()
        
        # 验证 CSV 文件
        import os
        assert os.path.exists(os.path.join(self.test_dir, "stock_daily.csv"))
        
        with open(os.path.join(self.test_dir, "stock_daily.csv"), "r") as f:
            content = f.read()
            assert "2330" in content
            assert "2317" in content
    
    def test_error_handling_flow(self):
        """测试错误处理流程"""
        spider = BaseSpider()
        
        # 模拟失败的响应
        response = SpiderResponse(
            success=False,
            error="Connection timeout",
            url="https://api.example.com"
        )
        
        assert response.success is False
        assert response.error is not None
        
        # 验证错误不写入 Pipeline
        pipeline = MemoryPipeline()
        # 不会保存失败的响应
        assert len(pipeline.get_items()) == 0
    
    def test_proxy_rotation_flow(self):
        """测试 Proxy 轮换流程"""
        spider = BaseSpider(proxy_enable=True)
        spider.proxy_list = [
            "http://proxy1.com:8080",
            "http://proxy2.com:8080",
            "http://proxy3.com:8080"
        ]
        
        proxies = []
        for i in range(5):
            proxy = spider.get_next_proxy()
            proxies.append(proxy)
            spider.request_count += 1
        
        # 验证轮换
        assert proxies[0] == "http://proxy1.com:8080"
        assert proxies[1] == "http://proxy2.com:8080"
        assert proxies[2] == "http://proxy3.com:8080"
        assert proxies[3] == "http://proxy1.com:8080"
        assert proxies[4] == "http://proxy2.com:8080"
    
    def test_item_transformation_flow(self):
        """测试 Item 转换流程"""
        # 模拟 API 原始数据
        raw_data = {
            "symbol": "12345",
            "name": "测试转债",
            "underlying_stock": "2330",
            "price": 110.0,
            "date": "2026-01-01"
        }
        
        # 转换为 Item
        item = CbMasterItem(
            cb_code=raw_data["symbol"],
            cb_name=raw_data["name"],
            underlying_stock=raw_data["underlying_stock"],
            market_type="TPEx",
            conversion_price=raw_data["price"]
        )
        
        # 验证转换
        assert item.cb_code == "12345"
        assert item.underlying_stock == "2330"
        assert item.get_unique_key() == "12345_2330"
        
        # 转换为字典
        item_dict = item.to_dict()
        assert "cb_code" in item_dict
        assert item_dict["underlying_stock"] == "2330"


class TestMultiTableIntegration:
    """多表整合测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, "test_dir") and shutil.os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_stock_and_cb_daily_flow(self):
        """测试股票和转债日报流程"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=1)
        
        # 股票日报
        stock_item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        
        # 可转债日报
        cb_item = TpexCbDailyItem(
            cb_code="12345",
            cb_name="测试转债",
            underlying_stock="2330",
            trade_date="2026-01-01",
            closing_price=110.0,
            volume=5000
        )
        
        pipeline.save_items(stock_item)
        pipeline.save_items(cb_item)
        pipeline.close()
        
        # 验证两个文件
        import os
        assert os.path.exists(os.path.join(self.test_dir, "stock_daily.csv"))
        assert os.path.exists(os.path.join(self.test_dir, "tpex_cb_daily.csv"))
