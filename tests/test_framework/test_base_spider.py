"""
BaseSpider 单元测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.base_spider import BaseSpider, SpiderResponse


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
