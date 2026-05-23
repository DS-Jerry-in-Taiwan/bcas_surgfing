"""
BaseSpider 单元测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.base_spider import BaseSpider, SpiderResponse

import requests


class TestSpiderResponse:
    """SpiderResponse 测试"""
    
    def test_successful_response(self):
        """测试成功响应"""
        response = SpiderResponse(
            success=True,
            data={"key": "value"},
            url="https://example.com"
        )
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.url == "https://example.com"
        assert response.error is None
    
    def test_failed_response(self):
        """测试失败响应"""
        response = SpiderResponse(
            success=False,
            error="Connection timeout",
            url="https://example.com"
        )
        assert response.success is False
        assert response.error == "Connection timeout"
    
    def test_to_dict(self):
        """测试转换为字典"""
        response = SpiderResponse(
            success=True,
            data={"key": "value"},
            url="https://example.com",
            metadata={"status_code": 200}
        )
        result = response.to_dict()
        
        assert result["success"] is True
        assert result["data"] == {"key": "value"}
        assert result["url"] == "https://example.com"
        assert "timestamp" in result


class TestBaseSpider:
    """BaseSpider 测试"""
    
    def test_spider_initialization_default(self):
        """测试爬虫默认初始化"""
        spider = BaseSpider()
        
        assert spider.thread_count == 1
        assert spider.redis_key is None
        assert spider.proxy_enable is True
        assert spider.requests_interval == 1.0
        assert "User-Agent" in spider.headers
    
    def test_spider_initialization_custom(self):
        """测试爬虫自定义初始化"""
        spider = BaseSpider(
            thread_count=4,
            redis_key="my_spider:redis",
            proxy_enable=False,
            requests_interval=2.0
        )
        
        assert spider.thread_count == 4
        assert spider.redis_key == "my_spider:redis"
        assert spider.proxy_enable is False
        assert spider.requests_interval == 2.0
    
    def test_default_headers(self):
        """测试默认 Header"""
        headers = BaseSpider.DEFAULT_HEADERS
        
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
    
    def test_proxy_loading_empty(self):
        """测试无 Proxy 配置"""
        spider = BaseSpider(proxy_enable=True)
        assert spider.proxy_list == []
        assert spider.get_random_proxy() is None
    
    def test_proxy_loading_from_env(self):
        """测试从环境变量加载 Proxy"""
        with patch.dict("os.environ", {"PROXY_LIST": "http://proxy1.com:8080,http://proxy2.com:8080"}):
            spider = BaseSpider(proxy_enable=True)
            assert len(spider.proxy_list) == 2
            assert "http://proxy1.com:8080" in spider.proxy_list
    
    def test_get_random_proxy(self):
        """测试随机获取 Proxy"""
        spider = BaseSpider(proxy_enable=True)
        spider.proxy_list = ["http://proxy1.com:8080", "http://proxy2.com:8080"]
        
        proxy = spider.get_random_proxy()
        assert proxy in spider.proxy_list
    
    def test_get_next_proxy(self):
        """测试轮换获取 Proxy"""
        spider = BaseSpider(proxy_enable=True)
        spider.proxy_list = ["http://proxy1.com:8080", "http://proxy2.com:8080"]
        spider.request_count = 0
        
        proxy1 = spider.get_next_proxy()
        assert proxy1 == "http://proxy1.com:8080"
        
        spider.request_count = 1
        proxy2 = spider.get_next_proxy()
        assert proxy2 == "http://proxy2.com:8080"
    
    def test_make_headers_default(self):
        """测试生成默认 Header"""
        spider = BaseSpider()
        headers = spider.make_headers()
        
        assert "User-Agent" in headers
        assert headers == spider.DEFAULT_HEADERS
    
    def test_make_headers_with_extra(self):
        """测试生成带额外 Header"""
        spider = BaseSpider()
        headers = spider.make_headers({"Referer": "https://example.com"})
        
        assert "Referer" in headers
        assert headers["Referer"] == "https://example.com"
    
    def test_make_proxy_dict(self):
        """测试生成 Proxy 字典"""
        spider = BaseSpider()
        proxy_dict = spider.make_proxy_dict("http://proxy.com:8080")
        
        assert proxy_dict is not None
        assert proxy_dict["http"] == "http://proxy.com:8080"
        assert proxy_dict["https"] == "http://proxy.com:8080"
    
    def test_make_proxy_dict_none(self):
        """测试无 Proxy 时返回 None"""
        spider = BaseSpider()
        proxy_dict = spider.make_proxy_dict(None)
        assert proxy_dict is None
    
    def test_parse_response_success(self):
        """测试解析响应 - 成功"""
        spider = BaseSpider()
        
        mock_response = Mock()
        mock_response.url = "https://example.com"
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        result = spider.parse_response(mock_response)
        
        assert result.success is True
        assert result.data == {"data": "test"}
        assert result.url == "https://example.com"
        assert result.metadata["status_code"] == 200
    
    def test_parse_response_failure(self):
        """测试解析响应 - 失败"""
        spider = BaseSpider()
        
        mock_response = Mock()
        mock_response.url = "https://example.com"
        mock_response.status_code = 404
        mock_response.json.side_effect = Exception("JSON decode error")
        
        result = spider.parse_response(mock_response)
        
        assert result.success is False
        assert result.error is not None
    
    def test_parse_response_none(self):
        """测试解析空响应"""
        spider = BaseSpider()
        result = spider.parse_response(None)
        
        assert result.success is False
        assert "Empty response" in result.error
    
    def test_create_request_kwargs(self):
        """测试创建请求参数"""
        spider = BaseSpider(proxy_enable=True)
        spider.proxy_list = ["http://proxy.com:8080"]  # 确保有 proxy
        
        kwargs = spider.create_request_kwargs(
            url="https://example.com",
            method="POST",
            timeout=30
        )
        
        assert kwargs["url"] == "https://example.com"
        assert kwargs["method"] == "POST"
        assert kwargs["timeout"] == 30
        assert "headers" in kwargs
        assert "proxies" in kwargs  # 有 Proxy 时才会添加
    
    def test_create_request_kwargs_no_proxy(self):
        """测试创建请求参数 - 无 Proxy"""
        spider = BaseSpider(proxy_enable=True)
        spider.proxy_list = []  # 无 Proxy
        
        kwargs = spider.create_request_kwargs(
            url="https://example.com",
            method="GET"
        )
        
        assert kwargs["url"] == "https://example.com"
        assert "proxies" not in kwargs  # 无 Proxy 时不添加
    
    def test_record_request(self):
        """测试记录请求统计"""
        spider = BaseSpider()
        
        spider.record_request(success=True)
        assert spider.request_count == 1
        assert spider.error_count == 0
        
        spider.record_request(success=False)
        assert spider.request_count == 2
        assert spider.error_count == 1
    
    def test_get_statistics(self):
        """测试获取统计"""
        spider = BaseSpider()
        spider.request_count = 10
        spider.error_count = 2
        
        stats = spider.get_statistics()
        
        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert stats["success_rate"] == 80.0
    
    def test_repr(self):
        """测试 __repr__"""
        spider = BaseSpider(thread_count=2, proxy_enable=True)
        spider.request_count = 5
        
        repr_str = repr(spider)
        
        assert "BaseSpider" in repr_str
        assert "thread_count=2" in repr_str
        assert "proxy_enable=True" in repr_str
        assert "requests=5" in repr_str


class TestRetryMechanism:
    """BaseSpider Retry 機制測試"""

    def test_default_retry_params(self):
        """預設 retry 參數"""
        spider = BaseSpider()
        assert spider.max_retries == 3
        assert spider.retry_delay == 1.0
        assert spider.retry_backoff == 2.0

    def test_custom_retry_params(self):
        """自訂 retry 參數"""
        spider = BaseSpider(max_retries=5, retry_delay=2.0, retry_backoff=1.5)
        assert spider.max_retries == 5
        assert spider.retry_delay == 2.0
        assert spider.retry_backoff == 1.5

    def test_should_retry_on_failure(self):
        """失敗時 _should_retry 回傳 True"""
        spider = BaseSpider(max_retries=3)
        resp = SpiderResponse(success=False, error="timeout")
        assert spider._should_retry(resp, 1) is True
        assert spider._should_retry(resp, 2) is True

    def test_should_not_retry_on_success(self):
        """成功時 _should_retry 回傳 False"""
        spider = BaseSpider()
        resp = SpiderResponse(success=True, data={"ok": True})
        assert spider._should_retry(resp, 1) is False

    def test_should_not_retry_exhausted(self):
        """嘗試次數耗盡時 _should_retry 回傳 False"""
        spider = BaseSpider(max_retries=3)
        resp = SpiderResponse(success=False, error="timeout")
        assert spider._should_retry(resp, 3) is False  # attempt=3, max=3 → False

    @patch('framework.base_spider.requests.request')
    def test_request_with_retry_success(self, mock_request):
        """請求一次成功"""
        spider = BaseSpider(max_retries=3)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.json.return_value = {"key": "value"}
        mock_request.return_value = mock_response

        result = spider._request_with_retry("https://example.com")

        assert result.success is True
        assert result.data == {"key": "value"}
        assert mock_request.call_count == 1

    @patch('framework.base_spider.requests.request')
    def test_request_with_retry_retry_then_succeed(self, mock_request):
        """前 2 次失敗，第 3 次成功"""
        spider = BaseSpider(max_retries=3, retry_delay=0.01)  # 快速重試

        # 前 2 次 raise 例外，第 3 次成功
        mock_request.side_effect = [
            requests.exceptions.ConnectionError("timeout"),
            requests.exceptions.ConnectionError("timeout"),
            Mock(status_code=200, url="https://example.com", json=lambda: {"ok": True}),
        ]

        result = spider._request_with_retry("https://example.com")

        assert result.success is True
        assert result.data == {"ok": True}
        assert mock_request.call_count == 3

    @patch('framework.base_spider.requests.request')
    def test_request_with_retry_all_fail(self, mock_request):
        """全部失敗"""
        spider = BaseSpider(max_retries=3, retry_delay=0.01)

        mock_request.side_effect = requests.exceptions.ConnectionError("network down")

        result = spider._request_with_retry("https://example.com")

        assert result.success is False
        assert "network down" in result.error or "All 3 attempts failed" in result.error
        assert mock_request.call_count == 3

    @patch('framework.base_spider.requests.request')
    def test_request_with_retry_zero_max_retries(self, mock_request):
        """max_retries=0 時不重試"""
        spider = BaseSpider(max_retries=0)

        result = spider._request_with_retry("https://example.com")

        # max_retries=0 → for loop 不執行 → 直接回傳 failure
        assert result.success is False
        assert mock_request.call_count == 0

    @patch('framework.base_spider.requests.request')
    def test_request_with_retry_http_error(self, mock_request):
        """HTTP 500 錯誤應重試"""
        spider = BaseSpider(max_retries=3, retry_delay=0.01)

        # HTTP 500 (raise_for_status 會拋出)
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.url = "https://example.com"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")

        mock_request.return_value = mock_response

        result = spider._request_with_retry("https://example.com")

        assert result.success is False
        assert mock_request.call_count == 3
