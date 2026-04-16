"""
BatchSpider & CheckpointManager 單元測試
"""
import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "src")

from spiders.checkpoint_manager import CheckpointManager
from spiders.batch_spider import BatchSpider
from spiders.stock_daily_spider import StockDailySpider
from framework.pipelines import MemoryPipeline


class TestCheckpointManager:
    """CheckpointManager 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.json',
            mode='w'
        )
        self.temp_file.close()
        self.manager = CheckpointManager(self.temp_file.name)
        self.manager.reset()
    
    def teardown_method(self):
        """測試後清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_initialization(self):
        """測試初始化"""
        assert self.manager is not None
        assert self.manager.checkpoint_file == self.temp_file.name
        assert self.manager.data["status"] == "pending"
    
    def test_initialization_existing_file(self):
        """測試初始化-已有檔案"""
        with open(self.temp_file.name, 'w') as f:
            json.dump({
                "task_id": "test_001",
                "status": "running",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "progress": {"total": 10, "completed": 5, "failed": 1},
                "completed_keys": ["key1", "key2", "key3", "key4", "key5"],
                "failed_keys": [{"key": "key6", "error": "test error"}],
                "last_processed": {"key": "key5"}
            }, f)
        
        manager = CheckpointManager(self.temp_file.name)
        assert manager.data["task_id"] == "test_001"
        assert manager.data["progress"]["completed"] == 5
    
    def test_mark_completed(self):
        """測試標記完成"""
        self.manager.mark_completed("key_001")
        assert self.manager.is_completed("key_001") is True
        assert self.manager.data["progress"]["completed"] == 1
    
    def test_mark_completed_multiple(self):
        """測試標記多個完成"""
        self.manager.mark_completed("key_001")
        self.manager.mark_completed("key_002")
        self.manager.mark_completed("key_003")
        
        assert len(self.manager._completed_set) == 3
        assert self.manager.data["progress"]["completed"] == 3
    
    def test_mark_failed(self):
        """測試標記失敗"""
        self.manager.mark_failed("key_001", "Network error")
        
        assert self.manager.is_failed("key_001") is True
        assert self.manager._failed_dict["key_001"] == "Network error"
        assert self.manager.data["progress"]["failed"] == 1
    
    def test_is_completed(self):
        """測試檢查完成狀態"""
        self.manager.mark_completed("key_001")
        
        assert self.manager.is_completed("key_001") is True
        assert self.manager.is_completed("key_002") is False
    
    def test_get_pending(self):
        """測試取得待處理清單"""
        all_keys = ["key_001", "key_002", "key_003", "key_004"]
        
        self.manager.mark_completed("key_001")
        self.manager.mark_failed("key_002", "error")
        
        pending = self.manager.get_pending(all_keys)
        
        assert len(pending) == 2
        assert "key_001" not in pending
        assert "key_002" not in pending
        assert "key_003" in pending
        assert "key_004" in pending
    
    def test_save_and_load(self):
        """測試保存與載入"""
        self.manager.mark_completed("key_001")
        self.manager.mark_completed("key_002")
        self.manager.mark_failed("key_003", "Test error")
        self.manager.save()
        
        manager2 = CheckpointManager(self.temp_file.name)
        assert manager2.is_completed("key_001") is True
        assert manager2.is_completed("key_002") is True
        assert manager2.is_failed("key_003") is True
    
    def test_reset(self):
        """測試重置"""
        self.manager.mark_completed("key_001")
        self.manager.mark_failed("key_002", "error")
        self.manager.reset()
        
        assert len(self.manager._completed_set) == 0
        assert len(self.manager._failed_dict) == 0
        assert self.manager.data["status"] == "pending"
    
    def test_set_status(self):
        """測試設定狀態"""
        self.manager.set_status("running")
        assert self.manager.data["status"] == "running"
        
        self.manager.set_status("completed")
        assert self.manager.data["status"] == "completed"
    
    def test_set_total(self):
        """測試設定總數"""
        self.manager.set_total(100)
        assert self.manager.data["progress"]["total"] == 100
    
    def test_get_progress(self):
        """測試取得進度"""
        self.manager.set_total(100)
        self.manager.mark_completed("key_001")
        self.manager.mark_completed("key_002")
        self.manager.mark_failed("key_003", "error")
        
        progress = self.manager.get_progress()
        
        assert progress["total"] == 100
        assert progress["completed"] == 2
        assert progress["failed"] == 1
        assert progress["pending"] == 97
    
    def test_get_summary(self):
        """測試取得摘要"""
        self.manager.set_total(10)
        self.manager.mark_completed("key_001")
        self.manager.mark_completed("key_002")
        self.manager.mark_failed("key_003", "error")
        
        summary = self.manager.get_summary()
        
        assert "task_id" in summary
        assert summary["total"] == 10
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] > 0
    
    def test_repr(self):
        """測試 __repr__"""
        repr_str = repr(self.manager)
        assert "CheckpointManager" in repr_str


class TestBatchSpider:
    """BatchSpider 測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.json',
            mode='w'
        )
        self.temp_file.close()
        self.pipeline = MemoryPipeline()
    
    def teardown_method(self):
        """測試後清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_initialization(self):
        """測試初始化"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            pipeline=self.pipeline,
            max_workers=2
        )
        
        assert batch.spider_class == StockDailySpider
        assert batch.max_workers == 2
        assert batch.pipeline == self.pipeline
    
    def test_initialization_with_checkpoint(self):
        """測試初始化-含斷點"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name,
            max_workers=2
        )
        
        assert batch.checkpoint is not None
        assert hasattr(batch.checkpoint, 'is_completed')
        assert hasattr(batch.checkpoint, 'mark_completed')
    
    def test_generate_keys(self):
        """測試生成 keys"""
        batch = BatchSpider(spider_class=StockDailySpider)
        
        keys = batch._generate_keys(
            symbols=["2330", "2317"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert len(keys) == 2
        assert "2330_2024_01" in keys
        assert "2317_2024_01" in keys
    
    def test_parse_key(self):
        """測試解析 key"""
        batch = BatchSpider(spider_class=StockDailySpider)
        
        parsed = batch._parse_key("2330_2024_01")
        assert parsed["symbol"] == "2330"
        assert parsed["year"] == 2024
        assert parsed["month"] == 1
        
        parsed2 = batch._parse_key("daily_2024-01-15")
        assert parsed2["date"] == "2024-01-15"
    
    def test_get_progress(self):
        """測試取得進度"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name
        )
        
        progress = batch.get_progress()
        assert "total" in progress
        assert "completed" in progress
        assert "failed" in progress
    
    def test_get_progress_no_checkpoint(self):
        """測試無斷點時取得進度"""
        batch = BatchSpider(spider_class=StockDailySpider)
        
        progress = batch.get_progress()
        assert progress["total"] == 0
    
    def test_repr(self):
        """測試 __repr__"""
        batch = BatchSpider(spider_class=StockDailySpider)
        repr_str = repr(batch)
        assert "BatchSpider" in repr_str
        assert "StockDailySpider" in repr_str
    
    def test_generate_keys_different_dates(self):
        """測試生成 keys - 不同月份"""
        batch = BatchSpider(spider_class=StockDailySpider)
        
        keys = batch._generate_keys(
            symbols=["2330"],
            start_date="2024-01-01",
            end_date="2024-03-31"
        )
        
        assert len(keys) == 3
        assert "2330_2024_01" in keys
        assert "2330_2024_02" in keys
        assert "2330_2024_03" in keys
    
    def test_generate_keys_same_month(self):
        """測試生成 keys - 同月份"""
        batch = BatchSpider(spider_class=StockDailySpider)
        
        keys = batch._generate_keys(
            symbols=["2330"],
            start_date="2024-01-01",
            end_date="2024-01-15"
        )
        
        assert len(keys) == 1
        assert "2330_2024_01" in keys
    
    def test_checkpoint_mark_completed(self):
        """測試斷點標記完成"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name
        )
        
        batch.checkpoint.mark_completed("test_key")
        batch.checkpoint.save()
        
        assert batch.checkpoint.is_completed("test_key")


class TestBatchConcurrency:
    """並發控制測試"""
    
    def test_thread_pool_size(self):
        """測試執行緒池大小"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            max_workers=4
        )
        assert batch.max_workers == 4
    
    def test_request_interval(self):
        """測試請求間隔"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            request_interval=0.5
        )
        assert batch.request_interval == 0.5
    
    def test_max_retries(self):
        """測試最大重試次數"""
        batch = BatchSpider(
            spider_class=StockDailySpider,
            max_retries=3
        )
        assert batch.max_retries == 3


class TestBatchSpiderIntegration:
    """批次爬蟲整合測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix='.json',
            mode='w'
        )
        self.temp_file.close()
    
    def teardown_method(self):
        """測試後清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @patch('spiders.stock_daily_spider.requests.get')
    def test_backfill_mock(self, mock_get):
        """測試批次補檔 - Mock"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "stat": "OK",
            "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
            "data": [["113/01/15", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"]]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        batch = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name,
            max_workers=1
        )
        
        results = batch.backfill(
            symbols=["2330"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        assert "success" in results
        assert "failed" in results
    
    def test_checkpoint_persistence(self):
        """測試斷點持久化"""
        batch1 = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name
        )
        batch1.checkpoint.mark_completed("test_key")
        batch1.checkpoint.save()
        
        batch2 = BatchSpider(
            spider_class=StockDailySpider,
            checkpoint_file=self.temp_file.name
        )
        assert batch2.checkpoint.is_completed("test_key")
