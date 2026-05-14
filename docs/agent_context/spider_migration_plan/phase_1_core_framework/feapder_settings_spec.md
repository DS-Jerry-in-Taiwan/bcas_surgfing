# Feapder 配置系統規範

## 1. 概述

本規範定義如何將 `.env` 環境變數對接到 Feapder 框架配置系統，確保敏感資訊安全管理與配置一致性。

---

## 2. 環境變數命名規範

### 2.1 前綴規則

| 前綴 | 用途 | 範例 |
|------|------|------|
| `DB_` | 資料庫相關 | `DB_HOST`, `DB_PORT` |
| `REDIS_` | Redis 相關 | `REDIS_HOST`, `REDIS_KEY` |
| `ALERT_` | 告警相關 | `SLACK_WEBHOOK_URL` |
| `SPIDER_` | 爬蟲相關 | `SPIDER_HEADERS` |
| `PROXY_` | Proxy 相關 | `PROXY_LIST` |

### 2.2 完整環境變數清單

```bash
# ===== Database =====
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bcas_quant
DB_USER=postgres
DB_PASSWORD=secret

# ===== Redis =====
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_KEY=feapder:spider

# ===== Slack Alert =====
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
SLACK_CHANNEL=#crawler-alerts
SLACK_ALERT_ENABLED=true
SLACK_ALERT_LEVEL=ERROR  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ===== Spider Settings =====
SPIDER_HEADERS=Referer:https://example.com,X-Custom:header
SPIDER_THREAD_COUNT=4
SPIDER_RETRY_TIMES=3
SPIDER_RETRY_DELAY=5

# ===== Proxy =====
PROXY_LIST=http://proxy1.com:8080,http://proxy2.com:8080
PROXY_ENABLED=false
```

---

## 3. feapder_settings.py 實作規範

### 3.1 檔案位置
```
src/
├── settings/
│   ├── __init__.py
│   └── feapder_settings.py    # 主要設定檔
```

### 3.2 程式碼結構

```python
# src/settings/feapder_settings.py
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
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)


# ===== Database Configuration =====

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


# ===== Redis Configuration =====

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


# ===== Slack Alert Configuration =====

@dataclass
class SlackAlertConfig:
    """Slack 告警配置"""
    webhook_url: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    channel: str = field(default_factory=lambda: os.getenv("SLACK_CHANNEL", "#crawler-alerts"))
    enabled: bool = field(default_factory=lambda: os.getenv("SLACK_ALERT_ENABLED", "false").lower() == "true")
    min_level: str = field(default_factory=lambda: os.getenv("SLACK_ALERT_LEVEL", "ERROR"))
    
    # 日誌等級映射
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


# ===== Spider Configuration =====

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


# ===== Proxy Configuration =====

@dataclass
class ProxyConfig:
    """Proxy 配置"""
    proxy_list: List[str] = field(default_factory=lambda: _parse_proxy_list(os.getenv("PROXY_LIST", "")))
    enabled: bool = field(default_factory=lambda: os.getenv("PROXY_ENABLED", "false").lower() == "true")
    
    @property
    def is_configured(self) -> bool:
        """檢查是否已配置"""
        return self.enabled and len(self.proxy_list) > 0


# ===== Helper Functions =====

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


# ===== Global Config Instance =====

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


# 單例實例
settings = FeapderSettings.load()
```

---

## 4. 與 Feapder AirSpider 整合

### 4.1 自訂 Settings Provider

```python
# src/settings/feapder_provider.py
"""
Feapder Settings Provider
將自訂配置提供給 Feapder 框架
"""
from .feapder_settings import settings


class AirSpiderSettings:
    """Feapder AirSpider 配置"""
    
    # Redis 配置
    REDIS_ADDRESS = settings.redis.url
    REDIS_KEY = settings.redis.key_prefix
    
    # 批次大小
    BATCH_COUNT = 100
    
    # 重試配置
    RETRY_TIMES = settings.spider.retry_times
    RETRY_DELAY = settings.spider.retry_delay
    
    # 日誌
    LOG_FILE = "logs/spider.log"
    LOG_LEVEL = "INFO"
```

### 4.2 使用範例

```python
# src/spiders/example_spider.py
from feapder import AirSpider
from src.settings.feapder_settings import settings
from src.framework import BaseSpider


class ExampleSpider(AirSpider, BaseSpider):
    """範例爬蟲"""
    
    def __init__(self, **kwargs):
        # Feapder 配置
        kwargs.setdefault("redis_key", settings.redis.key_prefix)
        kwargs.setdefault("thread_count", settings.spider.thread_count)
        
        super().__init__(**kwargs)
        
        # 自訂配置
        self.settings = settings
    
    def start_requests(self):
        # 爬取邏輯
        pass
    
    def parse(self, response, **kwargs):
        # 解析邏輯
        pass
```

---

## 5. 驗證清單

- [ ] `.env` 檔案包含所有必要變數
- [ ] `feapder_settings.py` 正確解析所有變數
- [ ] 資料庫連線測試通過
- [ ] Redis 連線測試通過（分散式模式需要）
- [ ] Slack 告警測試通過

---

*文件版本：1.0.0*
*建立時間：2026-04-15*
