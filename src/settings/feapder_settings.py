"""
Feapder 框架配置模組

對接 .env 環境變數，提供統一的配置管理
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()

logger = logging.getLogger(__name__)


def _parse_headers(headers_str: str) -> Dict[str, str]:
    """解析 Headers 字串"""
    if not headers_str:
        return {}
    
    headers = {}
    for pair in headers_str.split(","):
        if ":" in pair:
            key, value = pair.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers


def _parse_proxy_list(proxy_str: str) -> List[str]:
    """解析 Proxy 列表"""
    if not proxy_str:
        return []
    return [p.strip() for p in proxy_str.split(",") if p.strip()]


@dataclass
class DatabaseConfig:
    """資料庫配置"""
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = field(default_factory=lambda: os.getenv("DB_NAME", "bcas_quant"))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    
    @property
    def connection_string(self) -> str:
        """取得連線字串"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def psycopg2_params(self) -> Dict[str, any]:
        """取得 psycopg2 參數"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.name,
            "user": self.user,
            "password": self.password,
        }


@dataclass
class RedisConfig:
    """Redis 配置"""
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    key_prefix: str = field(default_factory=lambda: os.getenv("REDIS_KEY", "feapder:spider"))
    
    @property
    def url(self) -> str:
        """取得 Redis URL"""
        return f"redis://{self.host}:{self.port}/0"


@dataclass
class SlackAlertConfig:
    """Slack 告警配置"""
    webhook_url: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    channel: str = field(default_factory=lambda: os.getenv("SLACK_CHANNEL", "#crawler-alerts"))
    enabled: bool = field(default_factory=lambda: os.getenv("SLACK_ALERT_ENABLED", "false").lower() == "true")
    min_level: str = field(default_factory=lambda: os.getenv("SLACK_ALERT_LEVEL", "ERROR"))
    
    LEVEL_MAP = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    
    @property
    def min_level_value(self) -> int:
        """取得最小告警等級值"""
        return self.LEVEL_MAP.get(self.min_level.upper(), 40)
    
    @property
    def is_configured(self) -> bool:
        """檢查是否已配置"""
        return bool(self.webhook_url) and self.enabled


@dataclass
class SpiderConfig:
    """爬蟲配置"""
    headers: Dict[str, str] = field(default_factory=lambda: _parse_headers(os.getenv("SPIDER_HEADERS", "")))
    thread_count: int = field(default_factory=lambda: int(os.getenv("SPIDER_THREAD_COUNT", "1")))
    retry_times: int = field(default_factory=lambda: int(os.getenv("SPIDER_RETRY_TIMES", "3")))
    retry_delay: int = field(default_factory=lambda: int(os.getenv("SPIDER_RETRY_DELAY", "5")))
    
    @property
    def headers_string(self) -> str:
        """取得 Headers 字串"""
        return os.getenv("SPIDER_HEADERS", "")


@dataclass
class ProxyConfig:
    """Proxy 配置"""
    proxy_list: List[str] = field(default_factory=lambda: _parse_proxy_list(os.getenv("PROXY_LIST", "")))
    enabled: bool = field(default_factory=lambda: os.getenv("PROXY_ENABLED", "false").lower() == "true")
    
    @property
    def is_configured(self) -> bool:
        """檢查是否已配置"""
        return self.enabled and len(self.proxy_list) > 0


@dataclass
class FeapderSettings:
    """Feapder 全域配置"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    slack_alert: SlackAlertConfig = field(default_factory=SlackAlertConfig)
    spider: SpiderConfig = field(default_factory=SpiderConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    
    @classmethod
    def load(cls) -> "FeapderSettings":
        """載入配置"""
        return cls()
    
    def validate(self) -> List[str]:
        """驗證配置完整性"""
        errors = []
        
        if not self.database.host:
            errors.append("DB_HOST is required")
        
        if not self.database.name:
            errors.append("DB_NAME is required")
        
        if self.slack_alert.enabled and not self.slack_alert.webhook_url:
            errors.append("SLACK_WEBHOOK_URL is required when alerts are enabled")
        
        return errors


settings = FeapderSettings.load()
