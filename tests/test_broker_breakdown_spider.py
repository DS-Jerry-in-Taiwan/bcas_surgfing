"""BrokerBreakdownSpider 單元測試（mock BsrClient，無真實網路請求）"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
from src.spiders.broker_breakdown_spider import BrokerBreakdownSpider
from src.spiders.bsr_client import (
    BsrConnectionError,
    BsrCaptchaError,
    BsrParseError,
    BsrCircuitBreakerOpen,
)
from src.framework.base_item import BrokerBreakdownItem


SAMPLE_BSR_DATA = [
    {
        "seq": 1,
        "broker_name": "凱基-台北",
        "broker_id": "9200",
        "buy_volume": 1234567,
        "sell_volume": 567890,
        "net_volume": 666677,
    },
    {
        "seq": 2,
        "broker_name": "美商高盛",
        "broker_id": "1020",
        "buy_volume": 987654,
        "sell_volume": 432100,
        "net_volume": 555554,
    },
]


class TestBrokerBreakdownSpiderInit:
    """測試 __init__ 模式合規"""

    def test_init_accepts_pipeline(self):
        """__init__ 接受 pipeline=None 參數"""
        spider = BrokerBreakdownSpider()
        assert spider.pipeline is None
        assert spider.collect_only is True
        assert isinstance(spider.items, list)

    def test_init_with_pipeline(self):
        """__init__ 接受 pipeline 參數"""
        mock_pipeline = MagicMock()
        spider = BrokerBreakdownSpider(pipeline=mock_pipeline)
        assert spider.pipeline is mock_pipeline

    def test_items_empty(self):
        """self.items 初始化為空"""
        spider = BrokerBreakdownSpider()
        assert len(spider.items) == 0


class TestBrokerBreakdownSpiderFetch:
    """測試 fetch_broker_breakdown"""

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_successful_fetch(self, mock_bsr_client):
        """成功抓取時回傳正確資料"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")

        assert result.success is True
        assert result.data["count"] == 2
        assert len(spider.get_items()) == 2

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_add_item_called(self, mock_bsr_client):
        """確認 add_item() 被每筆資料呼叫"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        original_add_item = spider.add_item
        with patch.object(spider, 'add_item', wraps=original_add_item) as mock:
            spider.fetch_broker_breakdown("20260509", "2330")
            assert mock.call_count == 2

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_items_type(self, mock_bsr_client):
        """get_items() 回傳 BrokerBreakdownItem 列表"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")

        for item in spider.get_items():
            assert isinstance(item, BrokerBreakdownItem)

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_items_cleared(self, mock_bsr_client):
        """每次 fetch 前 items 被清空"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")
        count1 = len(spider.get_items())
        spider.fetch_broker_breakdown("20260510", "2330")
        count2 = len(spider.get_items())

        assert count1 == 2
        assert count2 == 2


class TestBrokerBreakdownSpiderError:
    """測試 BsrClient 異常處理"""

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_bsr_connection_error(self, mock_bsr_client):
        """BsrConnectionError 時回傳失敗"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.side_effect = BsrConnectionError("Network error")

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")

        assert result.success is False
        assert "BSR 查詢失敗" in result.error

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_bsr_captcha_error(self, mock_bsr_client):
        """BsrCaptchaError 時回傳失敗"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.side_effect = BsrCaptchaError("Captcha failed")

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")

        assert result.success is False
        assert "BSR 查詢失敗" in result.error

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_bsr_parse_error(self, mock_bsr_client):
        """BsrParseError 時回傳失敗"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.side_effect = BsrParseError("Parse failed")

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")

        assert result.success is False
        assert "BSR 查詢失敗" in result.error

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_bsr_circuit_breaker_open(self, mock_bsr_client):
        """BsrCircuitBreakerOpen 時回傳失敗"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.side_effect = BsrCircuitBreakerOpen("Circuit open")

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")

        assert result.success is False
        assert "BSR 查詢失敗" in result.error


class TestBrokerBreakdownSpiderItem:
    """測試 BrokerBreakdownItem 資料正確性"""

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_item_fields(self, mock_bsr_client):
        """Item 欄位正確"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")
        items = spider.get_items()

        assert items[0].broker_id == "9200"
        assert items[0].broker_name == "凱基-台北"
        assert items[0].rank == 1
        assert items[0].date == "20260509"
        assert items[0].symbol == "2330"
        assert items[0].buy_volume == 1234567
        assert items[0].sell_volume == 567890
        assert items[0].net_volume == 666677

        assert items[1].broker_id == "1020"
        assert items[1].broker_name == "美商高盛"
        assert items[1].rank == 2
        assert items[1].buy_volume == 987654
        assert items[1].sell_volume == 432100
        assert items[1].net_volume == 555554

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_item_source_bsr(self, mock_bsr_client):
        """Item source_type 為 bsr，source_url 為 BSR 網站"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")
        items = spider.get_items()

        for item in items:
            assert item.source_type == "bsr"
            assert item.source_url == "https://bsr.twse.com.tw/bshtm/"

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_rank_from_seq(self, mock_bsr_client):
        """rank 直接來自 BSR 的 seq 欄位"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")
        items = spider.get_items()

        assert items[0].rank == 1
        assert items[1].rank == 2


class TestBrokerBreakdownSpiderStatistics:
    """測試 get_statistics"""

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_statistics_includes_total(self, mock_bsr_client):
        """get_statistics() 包含 total_items"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")
        stats = spider.get_statistics()

        assert "total_items" in stats
        assert stats["total_items"] == 2

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_statistics_empty(self, mock_bsr_client):
        """無資料時 statistics total_items 為 0"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = []

        spider = BrokerBreakdownSpider()
        result = spider.fetch_broker_breakdown("20260509", "2330")
        assert result.success is True

        stats = spider.get_statistics()
        assert stats["total_items"] == 0


class TestBrokerBreakdownSpiderCollectOnly:
    """測試 collect_only 模式"""

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_pending_items(self, mock_bsr_client):
        """collect_only 模式下，item 被加入 _pending_items"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        spider.fetch_broker_breakdown("20260509", "2330")

        assert spider.get_pending_count() == 2
        assert len(spider._pending_items) == 2

    @patch('src.spiders.broker_breakdown_spider.BsrClient')
    def test_no_pipeline_no_save(self, mock_bsr_client):
        """無 pipeline 時不觸發 save_items"""
        mock_instance = mock_bsr_client.return_value
        mock_instance.fetch_broker_data.return_value = SAMPLE_BSR_DATA

        spider = BrokerBreakdownSpider()
        assert spider.pipeline is None

        spider.fetch_broker_breakdown("20260509", "2330")
