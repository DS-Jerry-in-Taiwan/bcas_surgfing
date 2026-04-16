"""
Pipeline 单元测试
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, "src")

from framework.pipelines import (
    BasePipeline,
    CsvPipeline,
    PostgresPipeline,
    MemoryPipeline,
)
from framework.base_item import StockDailyItem, TpexCbDailyItem
from framework.exceptions import PipelineError


class TestCsvPipeline:
    """CsvPipeline 测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_csv_pipeline_initialization(self):
        """测试 CsvPipeline 初始化"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        
        assert pipeline.output_dir == self.test_dir
        assert pipeline.batch_size == 10
        assert pipeline.success_count == 0
        assert pipeline.error_count == 0
    
    def test_save_single_item(self):
        """测试保存单笔"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=100)
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        
        pipeline.save_items(item)
        
        assert pipeline.success_count == 1
        assert pipeline.error_count == 0
        
        # 验证文件未创建（未达到 batch_size）
        assert not Path(self.test_dir, "stock_daily.csv").exists()
    
    def test_batch_flush(self):
        """测试批次写出"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=2)
        
        for i in range(3):
            item = StockDailyItem(
                symbol=f"233{i}",
                date="2026-01-01",
                open_price=100.0,
                close_price=105.0,
                high_price=106.0,
                low_price=99.0,
                volume=1000000
            )
            pipeline.save_items(item)
        
        # 触发 flush
        pipeline.flush_all()
        
        # 验证文件创建
        filepath = Path(self.test_dir, "stock_daily.csv")
        assert filepath.exists()
        
        # 验证内容
        content = filepath.read_text()
        assert "symbol" in content
        assert "2330" in content
    
    def test_multiple_tables(self):
        """测试多表支持"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=1)
        
        stock_item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        
        cb_item = TpexCbDailyItem(
            cb_code="12345",
            trade_date="2026-01-01",
            closing_price=110.0
        )
        
        pipeline.save_items(stock_item)
        pipeline.save_items(cb_item)
        pipeline.flush_all()
        
        assert Path(self.test_dir, "stock_daily.csv").exists()
        assert Path(self.test_dir, "tpex_cb_daily.csv").exists()
    
    def test_get_statistics(self):
        """测试统计功能"""
        pipeline = CsvPipeline(output_dir=self.test_dir)
        
        stats = pipeline.get_statistics()
        assert "success" in stats
        assert "errors" in stats
        assert "total" in stats
    
    def test_close(self):
        """测试关闭 Pipeline"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        pipeline.save_items(item)
        
        pipeline.close()
        
        # 验证文件已创建
        filepath = Path(self.test_dir, "stock_daily.csv")
        assert filepath.exists()


class TestMemoryPipeline:
    """MemoryPipeline 测试"""
    
    def test_memory_pipeline_initialization(self):
        """测试 MemoryPipeline 初始化"""
        pipeline = MemoryPipeline()
        
        assert pipeline.success_count == 0
        assert pipeline.error_count == 0
        assert len(pipeline.items) == 0
    
    def test_save_items(self):
        """测试保存 Items"""
        pipeline = MemoryPipeline()
        
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        
        pipeline.save_items(item)
        
        assert len(pipeline.items) == 1
        assert pipeline.success_count == 1
        assert pipeline.items[0].symbol == "2330"
    
    def test_get_items(self):
        """测试获取 Items"""
        pipeline = MemoryPipeline()
        
        item1 = StockDailyItem(symbol="2330", date="2026-01-01", open_price=100.0, close_price=105.0, high_price=106.0, low_price=99.0, volume=1000000)
        item2 = TpexCbDailyItem(cb_code="12345", trade_date="2026-01-01", closing_price=110.0)
        
        pipeline.save_items(item1)
        pipeline.save_items(item2)
        
        items = pipeline.get_items()
        assert len(items) == 2
    
    def test_clear(self):
        """测试清空"""
        pipeline = MemoryPipeline()
        
        item = StockDailyItem(symbol="2330", date="2026-01-01", open_price=100.0, close_price=105.0, high_price=106.0, low_price=99.0, volume=1000000)
        pipeline.save_items(item)
        
        pipeline.clear()
        
        assert len(pipeline.items) == 0
        assert pipeline.success_count == 0
        assert pipeline.error_count == 0


class TestPostgresPipeline:
    """PostgresPipeline 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        pipeline = PostgresPipeline(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass",
            batch_size=50
        )
        
        assert pipeline.host == "localhost"
        assert pipeline.database == "test_db"
        assert pipeline.batch_size == 50
        assert pipeline._conn is None
    
    def test_initialization_from_env(self):
        """测试从环境变量初始化"""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("POSTGRES_HOST", "env_host")
            mp.setenv("POSTGRES_DB", "env_db")
            
            pipeline = PostgresPipeline()
            
            assert pipeline.host == "env_host"
            assert pipeline.database == "env_db"
    
    def test_save_items_no_connection(self):
        """测试保存时不建立连线"""
        pipeline = PostgresPipeline(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0,
            high_price=106.0,
            low_price=99.0,
            volume=1000000
        )
        
        # 不会立即保存（批次）
        pipeline.save_items(item)
        
        # 连线仍未建立
        assert pipeline._conn is None
        assert pipeline.success_count == 1
        assert len(pipeline._batch_buffer) == 1
    
    def test_get_statistics(self):
        """测试统计"""
        pipeline = PostgresPipeline(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        
        stats = pipeline.get_statistics()
        assert "success" in stats
        assert "errors" in stats
        assert "total" in stats
