"""
Feapder Framework - BaseSpider
整合 Proxy、統一 Header、自定義 Retry 與 Agent 回傳介面
"""
from __future__ import annotations

import os
import random
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


@dataclass
class SpiderResponse:
    """
    爬蟲回傳統一格式
    
    Attributes:
        success: 請求是否成功
        data: 響應數據
        error: 錯誤信息
        url: 請求 URL
        timestamp: 時間戳
        metadata: 額外元數據
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    url: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class BaseSpider:
    """
    Feapder AirSpider 擴展基底類
    
    功能說明:
        - 整合 Proxy 支援
        - 統一 Header 管理
        - 自動重試機制 (exponential backoff, 可自訂)
        - Agent 回傳介面
    
    Attributes:
        headers: HTTP Header 字典
        proxy_list: Proxy URL 列表
        requests_interval: 請求間隔（秒）
        thread_count: 線程數
        redis_key: Redis 鍵（用於分布式）
    
    Author: developer
    Version: 1.0.0
    """
    
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    def __init__(
        self,
        thread_count: int = 1,
        redis_key: Optional[str] = None,
        proxy_enable: bool = True,
        requests_interval: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
    ) -> None:
        """
        初始化 BaseSpider
        
        Args:
            thread_count: 線程數
            redis_key: Redis 鍵（分布式用）
            proxy_enable: 是否啟用 Proxy
            requests_interval: 請求間隔（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲（秒）
            retry_backoff: 重試退避倍數
        """
        self.thread_count = thread_count
        self.redis_key = redis_key
        self.proxy_enable = proxy_enable
        self.requests_interval = requests_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        
        # Header 配置
        self.headers = self.DEFAULT_HEADERS.copy()
        self._load_custom_headers()
        
        # Proxy 配置
        self.proxy_list: List[str] = self._load_proxies()
        
        # 統計
        self.request_count: int = 0
        self.error_count: int = 0

        # collect_only mode（延遲寫入，驗證後才 flush）
        self._pending_items: List = []
        self.collect_only: bool = False
        
        logger.info(
            f"BaseSpider initialized: thread={thread_count}, "
            f"proxy_enable={proxy_enable}, interval={requests_interval}s, "
            f"max_retries={max_retries}, retry_delay={retry_delay}, retry_backoff={retry_backoff}"
        )
    
    def _load_custom_headers(self) -> None:
        """從環境變數載入自定義 Header"""
        custom_headers = os.getenv("SPIDER_HEADERS", "")
        if custom_headers:
            try:
                for pair in custom_headers.split(","):
                    if ":" in pair:
                        key, value = pair.split(":", 1)
                        self.headers[key.strip()] = value.strip()
                logger.info(f"Loaded custom headers from SPIDER_HEADERS")
            except Exception as e:
                logger.warning(f"Failed to parse SPIDER_HEADERS: {e}")
    
    def _load_proxies(self) -> List[str]:
        """從環境變數載入 Proxy 列表"""
        proxy_str = os.getenv("PROXY_LIST", "")
        if not proxy_str:
            logger.info("No PROXY_LIST configured")
            return []
        
        proxies = [p.strip() for p in proxy_str.split(",") if p.strip()]
        logger.info(f"Loaded {len(proxies)} proxies from environment")
        return proxies
    
    def get_random_proxy(self) -> Optional[str]:
        """取得隨機 Proxy"""
        if not self.proxy_list:
            return None
        return random.choice(self.proxy_list)
    
    def get_next_proxy(self) -> Optional[str]:
        """輪換獲取下一個 Proxy"""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.request_count % len(self.proxy_list)]
        return proxy
    
    def make_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        建立請求 Header
        
        Args:
            extra_headers: 額外的 Header
        
        Returns:
            合併後的 Header 字典
        """
        headers = self.headers.copy()
        if extra_headers:
            headers.update(extra_headers)
        return headers
    
    def make_proxy_dict(self, proxy: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        建立 Proxy 字典
        
        Args:
            proxy: Proxy URL
        
        Returns:
            {'http': proxy, 'https': proxy} 或 None
        """
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}
    
    def parse_response(
        self,
        response: Any,
        response_type: str = "json"
    ) -> SpiderResponse:
        """
        解析回應為統一格式
        
        Args:
            response: 響應對象
            response_type: 響應類型 ('json', 'text', 'content')
        
        Returns:
            SpiderResponse 對象
        """
        try:
            if response is None:
                return SpiderResponse(
                    success=False,
                    error="Empty response"
                )
            
            url = getattr(response, "url", "")
            status_code = getattr(response, "status_code", 0)
            
            data = None
            if response_type == "json":
                data = response.json() if hasattr(response, "json") else None
            elif response_type == "text":
                data = response.text if hasattr(response, "text") else None
            elif response_type == "content":
                data = response.content if hasattr(response, "content") else None
            
            return SpiderResponse(
                success=status_code < 400,
                data=data,
                url=url,
                metadata={"status_code": status_code}
            )
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return SpiderResponse(
                success=False,
                error=str(e),
                url=getattr(response, "url", "") if response else ""
            )
    
    def create_request_kwargs(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: int = 30,
        use_auto_proxy: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        建立標準化的請求參數
        
        Args:
            url: 請求 URL
            method: 請求方法
            headers: 請求 Header
            proxy: Proxy URL (若為 None 且 use_auto_proxy=True，則自動獲取)
            timeout: 超時時間
            use_auto_proxy: 是否自動獲取 Proxy
            **kwargs: 其他參數
        
        Returns:
            請求參數字典
        """
        request_kwargs: Dict[str, Any] = {
            "url": url,
            "method": method,
            "headers": headers or self.make_headers(),
            "timeout": timeout,
        }
        
        # 如果未指定 proxy 且啟用自動代理，則獲取一個
        if proxy is None and use_auto_proxy:
            proxy = self.get_random_proxy()
        
        if proxy and self.proxy_enable:
            request_kwargs["proxies"] = self.make_proxy_dict(proxy)
        
        request_kwargs.update(kwargs)
        return request_kwargs
    
    def _should_retry(self, response: SpiderResponse, attempt: int) -> bool:
        """判斷是否應該重試。子類可 override 自定義條件。

        Args:
            response: 回應對象
            attempt: 當前嘗試次數 (1-based)

        Returns:
            True 表示應該重試
        """
        if response.success:
            return False
        return attempt < self.max_retries

    def _request_with_retry(
        self,
        url: str,
        method: str = "GET",
        response_type: str = "json",
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        timeout: int = 30,
        use_auto_proxy: bool = True,
        **kwargs
    ) -> SpiderResponse:
        """帶重試機制的 HTTP 請求

        流程:
            1. 建立標準化請求參數 (create_request_kwargs)
            2. 發送請求 (requests.request)
            3. 成功 → parse_response → 返回
            4. 失敗 → _should_retry → 指數退避重試
            5. 重試次數耗盡 → 返回失敗 SpiderResponse

        Args:
            url: 請求 URL
            method: 請求方法 (GET/POST/...)
            response_type: 回應解析類型 ('json', 'text', 'content')
            headers: 自訂 Header
            proxy: Proxy URL
            timeout: 超時秒數
            use_auto_proxy: 是否自動獲取 Proxy
            **kwargs: 傳遞給 requests.request 的額外參數

        Returns:
            SpiderResponse
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                request_kwargs = self.create_request_kwargs(
                    url=url, method=method, headers=headers,
                    proxy=proxy, timeout=timeout, use_auto_proxy=use_auto_proxy,
                    **kwargs
                )

                response = requests.request(**request_kwargs)
                response.raise_for_status()

                parsed = self.parse_response(response, response_type)
                self.record_request(success=True)

                if parsed.success or not self._should_retry(parsed, attempt):
                    return parsed

                last_error = parsed.error

            except requests.RequestException as e:
                last_error = str(e)
                self.record_request(success=False)

                if not self._should_retry(SpiderResponse(success=False, error=str(e)), attempt):
                    return SpiderResponse(success=False, error=str(e), url=url)

            if attempt < self.max_retries:
                delay = self.retry_delay * (self.retry_backoff ** (attempt - 1))
                logger.info("Retrying in %.1fs (attempt %d/%d)...", delay, attempt + 1, self.max_retries)
                time.sleep(delay)

        return SpiderResponse(
            success=False,
            error=f"All {self.max_retries} attempts failed: {last_error}",
            url=url,
        )

    def record_request(self, success: bool = True) -> None:
        """記錄請求統計"""
        self.request_count += 1
        if not success:
            self.error_count += 1

    # ─── collect_only mode ──────────────────────────────────────────
    
    def add_item(self, item) -> None:
        """統一的 item 儲存入口
        
        在 collect_only 模式下暫存不寫入；否則立即寫入 pipeline。
        
        Args:
            item: BaseItem 實例
        """
        self._pending_items.append(item)
        pipeline = getattr(self, 'pipeline', None)
        if pipeline and not getattr(self, 'collect_only', False):
            pipeline.save_items(item)
    
    def flush_items(self, pipeline=None) -> None:
        """將暫存的 items 寫入指定的 pipeline
        
        Args:
            pipeline: 目標 pipeline（若為 None 則使用 self.pipeline）
        """
        p = pipeline or getattr(self, 'pipeline', None)
        if not p:
            return
        for item in self._pending_items:
            p.save_items(item)
        self._pending_items.clear()
    
    def get_pending_count(self) -> int:
        """取得暫存 items 數量"""
        return len(self._pending_items)
    
    # ────────────────────────────────────────────────────────────────
    
    def get_statistics(self) -> Dict[str, Any]:
        """取得爬蟲統計"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "success_rate": (
                (self.request_count - self.error_count) / self.request_count * 100
                if self.request_count > 0 else 100.0
            ),
            "proxy_count": len(self.proxy_list),
            "requests_interval": self.requests_interval,
        }
    
    def __repr__(self) -> str:
        return (
            f"<BaseSpider "
            f"thread_count={self.thread_count} "
            f"proxy_enable={self.proxy_enable} "
            f"requests={self.request_count}>"
        )
