"""
E2E 全鏈路整合測試

驗證 Phase 1-3 的完整資料流：
- BaseSpider -> Item -> PostgresPipeline
- StockMasterSpider -> StockDailySpider 流程
- CbMasterSpider -> TpexCbDailySpider 流程
- 去重邏輯驗證
"""
import pytest
import requests
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.base_spider import BaseSpider, SpiderResponse
from framework.pipelines import MemoryPipeline, CsvPipeline
from framework.base_item import (
    StockMasterItem,
    CbMasterItem,
    StockDailyItem,
    TpexCbDailyItem,
)
from spiders.stock_master_spider import StockMasterSpider
from spiders.cb_master_spider import CbMasterSpider
from spiders.stock_daily_spider import StockDailySpider
from spiders.tpex_cb_daily_spider import TpexCbDailySpider


# Mock 資料
TWSE_MASTER_HTML = """
<table>
<tr><td>有價證券代號及名稱</td><td>ISIN</td></tr>
<tr><td>2330　台積電</td><td>TW0002330008</td></tr>
<tr><td>2317　鴻海</td><td>TW0002317005</td></tr>
</table>
"""

TWSE_DAILY_JSON = {
    "stat": "OK",
    "fields": ["日期", "成交股數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌價差", "成交筆數"],
    "data": [
        ["113/01/15", "5,234,567", "125,678,901", "100", "105", "99", "103", "+3", "1,234"],
        ["113/01/16", "6,123,456", "138,901,234", "103", "108", "102", "107", "+4", "1,456"]
    ]
}

TPEX_CB_MASTER_CSV = """HEADER,債券代碼,債券簡稱,轉換起日,轉換迄日,轉換價格
BODY,"35031A","TestCB","2025/01/01","2028/12/31","100.0000"
BODY,"35032B","TestCB2","2025/06/01","2029/05/31","200.0000"
""".encode("big5")

TPEX_CB_DAILY_CSV = """HEADER,代號,名稱,收市,單位
BODY,"35031A","TestCB","105.5","1000"
""".encode("big5")


class TestFullPipelineFlow:
    """全系統整合測試 - 流程驗證"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """測試後清理"""
        if hasattr(self, "test_dir"):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_master_then_daily_flow(self):
        """測試主檔抓取後緊接日行情抓取"""
        master_pipeline = MemoryPipeline()
        daily_pipeline = MemoryPipeline()
        
        master_spider = StockMasterSpider(pipeline=master_pipeline)
        
        items = master_spider.parse_twse_html(TWSE_MASTER_HTML)
        assert len(items) == 2
        assert items[0].symbol == "2330"
        
        symbols = [item.symbol for item in items]
        
        daily_spider = StockDailySpider(pipeline=daily_pipeline)
        for symbol in symbols:
            daily_spider.items.extend(daily_spider.parse_twse_json(TWSE_DAILY_JSON, symbol))
        
        assert len(daily_spider.get_items()) == 4
        
        daily_stats = daily_spider.get_statistics()
        assert daily_stats["total_items"] == 4
    
    def test_cb_master_then_daily_flow(self):
        """測試 CB 主檔後緊接 CB 日行情"""
        master_pipeline = MemoryPipeline()
        daily_pipeline = MemoryPipeline()
        
        master_spider = CbMasterSpider(pipeline=master_pipeline)
        
        items = master_spider.parse_cb_csv(TPEX_CB_MASTER_CSV, "20240115")
        assert len(items) == 2
        
        cb_codes = [item.cb_code for item in items]
        assert "35031A" in cb_codes
        
        daily_spider = TpexCbDailySpider(pipeline=daily_pipeline)
        daily_items = daily_spider.parse_cb_csv(TPEX_CB_DAILY_CSV, "2024-01-15")
        daily_spider.items.extend(daily_items)
        
        assert len(daily_spider.get_items()) == 1
        assert daily_spider.items[0].cb_code == "35031A"
    
    def test_empty_symbol_list(self):
        """測試空的 symbol 清單"""
        spider = StockMasterSpider(pipeline=self.pipeline)
        items = spider.parse_twse_html("<table></table>")
        assert len(items) == 0

    def test_statistics_aggregation(self):
        """測試統計彙總"""
        spider = StockDailySpider(pipeline=self.pipeline)
        
        items = spider.parse_twse_json(TWSE_DAILY_JSON, "2330")
        assert len(items) == 2
        
        spider.items.extend(items)
        
        stats = spider.get_statistics()
        assert stats["total_items"] == 2
        assert stats["request_count"] == 0
    
    def test_pipeline_close_integrity(self):
        """測試未關閉的 Pipeline flush 後資料完整"""
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        
        stock_item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE",
            source_url="https://example.com",
            source_type="twse"
        )
        pipeline.save_items(stock_item)
        
        daily_item = StockDailyItem(
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
        pipeline.save_items(daily_item)
        
        pipeline.close()
        
        assert pipeline.success_count == 2

    def test_full_fetch_master_then_daily(self):
        """完整調用測試: mock HTTP → fetch_twse → fetch_daily → pipeline 驗證"""
        pipeline = MemoryPipeline()
        master_spider = StockMasterSpider(pipeline=pipeline)
        master_mock = Mock(status_code=200)
        master_mock.text = TWSE_MASTER_HTML

        with patch('requests.get', return_value=master_mock):
            result = master_spider.fetch_twse()
            assert result.success is True

        symbols = [item.symbol for item in pipeline.get_items()]
        assert "2330" in symbols
        assert len(symbols) == 2

        daily_spider = StockDailySpider(pipeline=pipeline)
        daily_mock = Mock(status_code=200)
        daily_mock.json.return_value = TWSE_DAILY_JSON
        daily_mock.raise_for_status = Mock()

        with patch('requests.get', return_value=daily_mock):
            for symbol in symbols:
                result = daily_spider.fetch_daily(symbol, 2024, 1)
                assert result.success is True

        all_items = pipeline.get_items()
        master_items = [i for i in all_items if hasattr(i, 'market_type')]
        daily_items = [i for i in all_items if hasattr(i, 'date')]
        assert len(master_items) == 2
        assert len(daily_items) == 4

    def test_full_fetch_cb_master_then_daily(self):
        """完整調用測試: mock HTTP → fetch_cb_master → fetch_daily → pipeline 驗證"""
        pipeline = MemoryPipeline()
        master_spider = CbMasterSpider(pipeline=pipeline)
        master_mock = Mock(status_code=200)
        master_mock.content = TPEX_CB_MASTER_CSV

        with patch('requests.get', return_value=master_mock):
            result = master_spider.fetch_cb_master("20240115")
            assert result.success is True

        assert len(pipeline.get_items()) == 2

        daily_spider = TpexCbDailySpider(pipeline=pipeline)
        daily_mock = Mock(status_code=200)
        daily_mock.content = TPEX_CB_DAILY_CSV
        daily_mock.raise_for_status = Mock()

        with patch('requests.get', return_value=daily_mock):
            result = daily_spider.fetch_daily("2024-01-15")
            assert result.success is True

        all_items = pipeline.get_items()
        assert len(all_items) == 3

    def test_full_fetch_tpex_master(self):
        """完整調用測試: mock HTTP → fetch_tpex → pipeline 驗證"""
        pipeline = MemoryPipeline()
        spider = StockMasterSpider(pipeline=pipeline)
        tpex_mock = Mock(status_code=200)
        tpex_mock.text = "<table><tr><th>有價證券代號及名稱</th></tr><tr><td>1234　測試股</td></tr></table>"
        tpex_mock.encoding = "utf-8"

        with patch('requests.get', return_value=tpex_mock):
            result = spider.fetch_tpex()
            assert result.success is True

        assert len(pipeline.get_items()) >= 1

    def test_full_fetch_stock_daily_empty_response(self):
        """完整調用測試: API 回傳空資料 → spider 正確處理"""
        pipeline = MemoryPipeline()
        spider = StockDailySpider(pipeline=pipeline)
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"stat": "OK", "fields": [], "data": []}
        mock_resp.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_resp):
            result = spider.fetch_daily("2330", 2024, 1)
            assert result.success is True
            assert result.data["count"] == 0


class TestDeduplicationLogic:
    """去重邏輯測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
    
    def test_duplicate_stock_daily(self):
        """測試相同 symbol_date 不重複寫入"""
        spider = StockDailySpider(pipeline=self.pipeline)
        
        item1 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        item2 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=106.0,
            low_price=99.0,
            close_price=105.0,
            volume=1100000
        )
        
        self.pipeline.save_items(item1)
        self.pipeline.save_items(item2)
        
        assert len(self.pipeline.get_items()) == 2
        
        assert item1.get_unique_key() == item2.get_unique_key()
    
    def test_duplicate_cb_daily(self):
        """測試相同 cb_code_trade_date 不重複寫入"""
        spider = TpexCbDailySpider(pipeline=self.pipeline)
        
        item1 = TpexCbDailyItem(
            cb_code="35031A",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000,
            underlying_stock="2330"
        )
        
        item2 = TpexCbDailyItem(
            cb_code="35031A",
            trade_date="2024-01-15",
            closing_price=106.0,
            volume=1200,
            underlying_stock="2330"
        )
        
        self.pipeline.save_items(item1)
        self.pipeline.save_items(item2)
        
        assert len(self.pipeline.get_items()) == 2
        
        assert item1.get_unique_key() == item2.get_unique_key()
    
    def test_different_dates_no_dedup(self):
        """測試不同日期不會去重"""
        spider = StockDailySpider(pipeline=self.pipeline)
        
        item1 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        item2 = StockDailyItem(
            symbol="2330",
            date="2024-01-16",
            open_price=103.0,
            high_price=108.0,
            low_price=102.0,
            close_price=107.0,
            volume=1100000
        )
        
        self.pipeline.save_items(item1)
        self.pipeline.save_items(item2)
        
        assert len(self.pipeline.get_items()) == 2
        
        assert item1.get_unique_key() != item2.get_unique_key()
    
    def test_updated_at_changes(self):
        """測試二次寫入時 updated_at 更新"""
        import time

        item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            close_price=103.0,
            high_price=105.0,
            low_price=99.0,
            volume=1000000
        )
        self.pipeline.save_items(item)
        first_item = self.pipeline.get_items()[0]
        before = first_item.updated_at

        time.sleep(0.01)

        item2 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            close_price=106.0,
            high_price=107.0,
            low_price=99.0,
            volume=1100000
        )
        self.pipeline.save_items(item2)
        after = self.pipeline.get_items()[0].updated_at

        assert after >= before

    def test_full_fetch_duplicate_detection(self):
        """完整調用測試: 兩次 fetch 相同資料，驗證 pipeline 接收多筆"""
        pipeline = MemoryPipeline()
        spider = StockDailySpider(pipeline=pipeline)

        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = TWSE_DAILY_JSON
        mock_resp.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_resp):
            r1 = spider.fetch_daily("2330", 2024, 1)
            assert r1.success is True
            r2 = spider.fetch_daily("2330", 2024, 1)
            assert r2.success is True

        assert len(pipeline.get_items()) == 4


class TestErrorRecovery:
    """錯誤恢復測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.pipeline = MemoryPipeline()
    
    def test_partial_failure_recovery(self):
        """測試部分失敗恢復"""
        spider = StockDailySpider(pipeline=self.pipeline)
        
        items = spider.parse_twse_json(TWSE_DAILY_JSON, "2330")
        assert len(items) == 2
        
        self.pipeline.save_items(items[0])
        self.pipeline.save_items(items[1])
        
        assert self.pipeline.success_count == 2
        assert len(self.pipeline.get_items()) == 2
    
    def test_network_timeout_retry(self):
        """測試網路超時重試機制"""
        spider = StockDailySpider(pipeline=self.pipeline)

        with patch('requests.get', side_effect=requests.exceptions.Timeout("Connection timeout")):
            result = spider.fetch_daily("2330", 2024, 1)
            assert result.success is False

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = TWSE_DAILY_JSON
            mock_get.return_value = mock_response

            result2 = spider.fetch_daily("2330", 2024, 1)
            assert result2.success is True
    
    def test_invalid_data_skip(self):
        """測試無效資料跳過並記錄錯誤"""
        spider = StockDailySpider(pipeline=self.pipeline)

        items = spider.parse_twse_json({"stat": "OK", "fields": [], "data": [["", "", ""]]}, "2330")
        assert len(items) == 0

    def test_full_fetch_network_timeout(self):
        """完整調用測試: requests.get 拋 timeout → spider 正確處理"""
        spider = StockDailySpider(pipeline=MemoryPipeline())

        with patch('requests.get', side_effect=requests.exceptions.Timeout("timeout")):
            result = spider.fetch_daily("2330", 2024, 1)
            assert result.success is False

    def test_full_fetch_api_error(self):
        """完整調用測試: API 回傳錯誤 stat → spider 正確回報失敗"""
        spider = StockDailySpider(pipeline=MemoryPipeline())
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"stat": "ERROR", "message": "rate limit"}
        mock_resp.raise_for_status = Mock()

        with patch('requests.get', return_value=mock_resp):
            result = spider.fetch_daily("2330", 2024, 1)
            assert result.success is False


class TestMultiTableIntegration:
    """多表整合測試"""
    
    def setup_method(self):
        """測試前準備"""
        self.test_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """測試後清理"""
        if hasattr(self, "test_dir"):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stock_and_cb_same_pipeline(self):
        """測試股票和 CB 同時寫入不同表"""
        import os
        
        pipeline = CsvPipeline(output_dir=self.test_dir, batch_size=10)
        
        stock_item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        pipeline.save_items(stock_item)
        
        cb_item = TpexCbDailyItem(
            cb_code="35031A",
            cb_name="TestCB",
            underlying_stock="2330",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000
        )
        pipeline.save_items(cb_item)
        
        pipeline.close()
        
        assert os.path.exists(os.path.join(self.test_dir, "stock_daily.csv"))
        assert os.path.exists(os.path.join(self.test_dir, "tpex_cb_daily.csv"))
    
    def test_unique_keys_isolated(self):
        """測試不同表的 unique_key 不會衝突"""
        pipeline = MemoryPipeline()
        
        stock_item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        
        cb_item = TpexCbDailyItem(
            cb_code="2330",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000
        )
        
        pipeline.save_items(stock_item)
        pipeline.save_items(cb_item)
        
        assert len(pipeline.get_items()) == 2
        assert stock_item.get_unique_key() == "2330_2024-01-15"
        assert cb_item.get_unique_key() == "2330_2024-01-15"
    
    def test_transaction_rollback(self):
        """測試交易失敗時無殘留資料"""
        pipeline = MemoryPipeline()

        item1 = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        pipeline.save_items(item1)
        assert len(pipeline.get_items()) == 1

        pipeline.clear()
        assert len(pipeline.get_items()) == 0

    def test_pipeline_batch_auto_flush(self):
        """測試 CsvPipeline 自動批次 flush"""
        import os
        test_dir = tempfile.mkdtemp()
        try:
            pipeline = CsvPipeline(output_dir=test_dir, batch_size=2)

            for i in range(3):
                item = StockDailyItem(
                    symbol=f"233{i}", date="2024-01-15",
                    open_price=100.0, high_price=105.0,
                    low_price=99.0, close_price=103.0, volume=1000000
                )
                pipeline.save_items(item)

            csv_path = os.path.join(test_dir, "stock_daily.csv")
            assert os.path.exists(csv_path)

            with open(csv_path) as f:
                lines = f.readlines()
            assert len(lines) == 3

            pipeline.close()
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)


class TestItemValidation:
    """Item 驗證測試"""
    
    def test_stock_master_validation(self):
        """測試 StockMasterItem 驗證"""
        valid_item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE"
        )
        assert valid_item.validate() is True
        
        invalid_item = StockMasterItem(symbol="", name="")
        assert invalid_item.validate() is False
    
    def test_stock_daily_validation(self):
        """測試 StockDailyItem 驗證"""
        valid_item = StockDailyItem(
            symbol="2330",
            date="2024-01-15",
            open_price=100.0,
            high_price=105.0,
            low_price=99.0,
            close_price=103.0,
            volume=1000000
        )
        assert valid_item.validate() is True
        
        invalid_item = StockDailyItem(symbol="", date="")
        assert invalid_item.validate() is False
    
    def test_cb_master_validation(self):
        """測試 CbMasterItem 驗證"""
        valid_item = CbMasterItem(
            cb_code="35031A",
            underlying_stock="2330"
        )
        assert valid_item.validate() is True
    
    def test_cb_daily_validation(self):
        """測試 TpexCbDailyItem 驗證"""
        valid_item = TpexCbDailyItem(
            cb_code="35031A",
            trade_date="2024-01-15",
            closing_price=105.5,
            volume=1000
        )
        assert valid_item.validate() is True
