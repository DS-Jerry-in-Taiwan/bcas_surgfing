# Slack 告警機制規範

## 1. 概述

本規範定義在 Feapder 框架中實作 Slack 告警機制的標準方式，確保爬蟲系統的異常狀態能即時通知相關人員。

---

## 2. 告警觸發點

### 2.1 觸發點位置

| 觸發點 | Feapder 方法 | 告警等級 | 說明 |
|--------|-------------|----------|------|
| 請求異常 | `on_exception` | ERROR | 網路錯誤、超時 |
| 解析失敗 | `parse` 返回空 | WARNING | 無法解析資料 |
| Pipeline 錯誤 | `save_item` 異常 | ERROR | 資料寫入失敗 |
| 速率限制 | 收到 429 | WARNING | 被目標網站限制 |
| 任務完成 | `end_callback` | INFO | 批次完成通知 |
| 嚴重錯誤 | 未捕獲異常 | CRITICAL | 程式崩潰 |

### 2.2 觸發點示意圖

```
┌─────────────────────────────────────────────────────────────┐
│                     Feapder Spider                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │ on_start │───▶│ requests │───▶│  parse   │───▶│save_item││
│  └──────────┘    └──────────┘    └──────────┘    └────┬───┘│
│       │              │              │                 │    │
│       ▼              ▼              ▼                 ▼    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │  INFO    │    │ ERROR*   │    │ WARNING* │    │ ERROR* ││
│  └──────────┘    └──────────┘    └──────────┘    └────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  SlackAlertBot   │
                    │  (webhook 發送)   │
                    └──────────────────┘
```

---

## 3. AlertLevel 定義

### 3.1 等級層級

```python
# src/framework/alerts.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


class AlertLevel(Enum):
    """告警等級枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    # 等級優先順序
    PRIORITY = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4,
    }
    
    def __ge__(self, other):
        return self.PRIORITY[self.value] >= self.PRIORITY[other.value]
    
    def __gt__(self, other):
        return self.PRIORITY[self.value] > self.PRIORITY[other.value]
    
    def __le__(self, other):
        return self.PRIORITY[self.value] <= self.PRIORITY[other.value]
    
    def __lt__(self, other):
        return self.PRIORITY[self.value] < self.PRIORITY[other.value]
```

---

## 4. SlackAlertBot 實作

### 4.1 核心類別

```python
# src/framework/alerts.py
import requests
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from src.settings.feapder_settings import settings, SlackAlertConfig

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警等級枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    PRIORITY = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


@dataclass
class AlertMessage:
    """告警訊息"""
    level: AlertLevel
    title: str
    message: str
    spider_name: str = ""
    spider_id: str = ""
    request_url: str = ""
    error_details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_slack_blocks(self) -> List[Dict]:
        """轉換為 Slack Block Kit 格式"""
        # 顏色映射
        color_map = {
            AlertLevel.DEBUG: "#95A5A6",
            AlertLevel.INFO: "#3498DB",
            AlertLevel.WARNING: "#F39C12",
            AlertLevel.ERROR: "#E74C3C",
            AlertLevel.CRITICAL: "#8E44AD",
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {self.title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Level:*\n{self.level.value}"},
                    {"type": "mrkdwn", "text": f"*Spider:*\n{self.spider_name}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"},
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n```{self.message}```"
                }
            }
        ]
        
        # 可選欄位
        if self.request_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Request URL:*\n<{self.request_url}|{self.request_url}>"
                }
            })
        
        if self.error_details:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error Details:*\n```{self.error_details}```"
                }
            })
        
        # Metadata
        if self.metadata:
            meta_text = "\n".join([f"• {k}: {v}" for k, v in self.metadata.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Metadata:*\n{meta_text}"
                }
            })
        
        blocks.append({"type": "divider"})
        
        return blocks
    
    def to_attachment(self) -> Dict:
        """轉換為 Slack Attachment 格式（向後相容）"""
        color_map = {
            AlertLevel.DEBUG: "#95A5A6",
            AlertLevel.INFO: "#3498DB",
            AlertLevel.WARNING: "#F39C12",
            AlertLevel.ERROR: "#E74C3C",
            AlertLevel.CRITICAL: "#8E44AD",
        }
        
        text = f"*{self.spider_name}*\n{self.message}"
        if self.error_details:
            text += f"\n```\n{self.error_details}\n```"
        
        return {
            "color": color_map[self.level],
            "title": self.title,
            "text": text,
            "footer": f"Spider ID: {self.spider_id}",
            "ts": self.timestamp.timestamp()
        }


class BaseAlertBackend(ABC):
    """告警後端抽象類"""
    
    @abstractmethod
    def send(self, message: AlertMessage) -> bool:
        """發送告警"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """檢查是否已配置"""
        pass


class SlackAlertBackend(BaseAlertBackend):
    """Slack 告警後端"""
    
    def __init__(self, config: SlackAlertConfig):
        self.config = config
        self.session = requests.Session()
    
    def is_configured(self) -> bool:
        return self.config.is_configured
    
    def send(self, message: AlertMessage) -> bool:
        """發送 Slack 訊息"""
        if not self.is_configured():
            logger.warning("Slack alert not configured, skipping")
            return False
        
        try:
            # 檢查是否達到最小告警等級
            if message.level < AlertLevel[self.config.min_level]:
                logger.debug(f"Message level {message.level.value} below minimum {self.config.min_level}")
                return False
            
            # 發送請求
            payload = {
                "channel": self.config.channel,
                "blocks": message.to_slack_blocks(),
                "attachments": [message.to_attachment()]
            }
            
            response = self.session.post(
                self.config.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack alert sent: {message.title}")
                return True
            else:
                logger.error(f"Slack alert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class AlertManager:
    """
    告警管理器
    
    統一管理所有告警後端，提供單一入口發送告警
    """
    
    def __init__(self):
        self.backends: List[BaseAlertBackend] = []
        self._init_backends()
    
    def _init_backends(self):
        """初始化後端"""
        # Slack
        if settings.slack_alert.is_configured:
            self.backends.append(SlackAlertBackend(settings.slack_alert))
            logger.info("Slack alert backend initialized")
    
    def alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        spider_name: str = "",
        spider_id: str = "",
        request_url: str = "",
        error_details: str = "",
        **metadata
    ) -> bool:
        """
        發送告警
        
        Args:
            level: 告警等級
            title: 標題
            message: 訊息內容
            spider_name: 爬蟲名稱
            spider_id: 爬蟲 ID
            request_url: 請求 URL
            error_details: 錯誤詳情
            **metadata: 額外元數據
        
        Returns:
            是否發送成功
        """
        msg = AlertMessage(
            level=level,
            title=title,
            message=message,
            spider_name=spider_name,
            spider_id=spider_id,
            request_url=request_url,
            error_details=error_details,
            metadata=metadata
        )
        
        success = True
        for backend in self.backends:
            if not backend.send(msg):
                success = False
        
        return success
    
    def debug(self, title: str, message: str, **kwargs):
        self.alert(AlertLevel.DEBUG, title, message, **kwargs)
    
    def info(self, title: str, message: str, **kwargs):
        self.alert(AlertLevel.INFO, title, message, **kwargs)
    
    def warning(self, title: str, message: str, **kwargs):
        self.alert(AlertLevel.WARNING, title, message, **kwargs)
    
    def error(self, title: str, message: str, **kwargs):
        self.alert(AlertLevel.ERROR, title, message, **kwargs)
    
    def critical(self, title: str, message: str, **kwargs):
        self.alert(AlertLevel.CRITICAL, title, message, **kwargs)


# 全域實例
alert_manager = AlertManager()
```

### 4.2 與 BaseSpider 整合

```python
# src/framework/base_spider.py (擴展)

from .alerts import alert_manager, AlertLevel


class BaseSpider(FeapderAirSpider):
    """帶告警功能的 BaseSpider"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.alert_enabled = settings.slack_alert.enabled
    
    def on_exception(self, exception: Exception, request: Request = None):
        """處理請求異常"""
        # 記錄並發送告警
        if self.alert_enabled:
            alert_manager.error(
                title=f"Spider Exception: {self.__class__.__name__}",
                message=str(exception),
                spider_name=self.__class__.__name__,
                spider_id=getattr(self, "spider_id", ""),
                request_url=request.url if request else "",
                error_details=traceback.format_exc()
            )
        
        return super().on_exception(exception, request)
    
    def end_callback(self):
        """任務完成回調"""
        if self.alert_enabled:
            alert_manager.info(
                title=f"Spider Completed: {self.__class__.__name__}",
                message=f"Total requests: {self.request_count}, Errors: {self.error_count}",
                spider_name=self.__class__.__name__,
                spider_id=getattr(self, "spider_id", ""),
                metadata={
                    "request_count": self.request_count,
                    "error_count": self.error_count,
                    "success_rate": self.get_statistics().get("success_rate", 0)
                }
            )
        
        return super().end_callback()
```

### 4.3 與 Pipeline 整合

```python
# src/framework/pipelines.py (擴展)

from .alerts import alert_manager, AlertLevel


class PostgresPipeline(BasePipeline):
    """帶告警功能的 PostgresPipeline"""
    
    def __init__(self, alert_enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.alert_enabled = alert_enabled and settings.slack_alert.enabled
    
    def _handle_error(self, error: Exception, item: BaseItem = None):
        """處理錯誤並發送告警"""
        self.error_count += 1
        
        if self.alert_enabled:
            alert_manager.error(
                title="Pipeline Save Error",
                message=f"Failed to save item: {type(error).__name__}",
                spider_name=getattr(item, "source_type", ""),
                error_details=str(error),
                metadata={
                    "item_type": type(item).__name__ if item else "Unknown",
                    "item_key": item.get_unique_key() if item else "Unknown"
                }
            )
```

---

## 5. 訊息格式範例

### 5.1 請求異常

```
🚨 Spider Exception: TpexCbCrawler

Level: ERROR
Spider: TpexCbCrawler
Time: 2026-04-15 10:30:00

Message:
Connection timeout while fetching data

Request URL: https://www.tpex.org.tw/web/bond/...

Error Details:
requests.exceptions.Timeout: Connection timeout
```

### 5.2 Pipeline 錯誤

```
🚨 Pipeline Save Error

Level: ERROR
Spider: StockDailyCrawler
Time: 2026-04-15 10:35:00

Message:
Failed to save item: DuplicateKeyError

Error Details:
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
```

### 5.3 任務完成

```
🚨 Spider Completed: TpexCbCrawler

Level: INFO
Spider: TpexCbCrawler
Time: 2026-04-15 11:00:00

Message:
Total requests: 150, Errors: 2

Metadata:
• request_count: 150
• error_count: 2
• success_rate: 98.7
```

---

## 6. 測試規範

### 6.1 單元測試

```python
# tests/test_framework/test_alerts.py
import pytest
from unittest.mock import Mock, patch
from src.framework.alerts import (
    AlertLevel, 
    AlertMessage, 
    SlackAlertBackend,
    AlertManager
)

class TestAlertMessage:
    """AlertMessage 測試"""
    
    def test_to_slack_blocks(self):
        """測試 Slack Block 格式"""
        msg = AlertMessage(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="Test message",
            spider_name="TestSpider",
            error_details="Error traceback"
        )
        
        blocks = msg.to_slack_blocks()
        
        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
    
    def test_to_attachment(self):
        """測試 Attachment 格式"""
        msg = AlertMessage(
            level=AlertLevel.WARNING,
            title="Warning",
            message="Warning message"
        )
        
        attachment = msg.to_attachment()
        
        assert "color" in attachment
        assert attachment["title"] == "Warning"


class TestAlertManager:
    """AlertManager 測試"""
    
    @patch('src.framework.alerts.settings')
    def test_alert_levels(self, mock_settings):
        """測試告警等級比較"""
        mock_settings.slack_alert.is_configured = True
        mock_settings.slack_alert.webhook_url = "http://test"
        mock_settings.slack_alert.min_level = "WARNING"
        
        assert AlertLevel.ERROR >= AlertLevel.WARNING
        assert AlertLevel.DEBUG < AlertLevel.INFO
```

### 6.2 整合測試

```python
# tests/test_framework/test_alert_integration.py

class TestSlackAlertIntegration:
    """Slack 告警整合測試"""
    
    @patch('requests.Session.post')
    def test_send_alert(self, mock_post):
        """測試發送告警"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # 測試發送
        alert_manager.info(
            title="Test",
            message="Test message",
            spider_name="TestSpider"
        )
        
        mock_post.assert_called_once()
```

---

## 7. 驗證清單

- [ ] `AlertLevel` 枚舉正確實作
- [ ] `AlertMessage` 可轉換為 Slack 格式
- [ ] `SlackAlertBackend` 正確發送請求
- [ ] `AlertManager` 管理多後端
- [ ] `BaseSpider` 在 `on_exception` 觸發告警
- [ ] `BaseSpider` 在 `end_callback` 發送完成通知
- [ ] `PostgresPipeline` 在錯誤時觸發告警
- [ ] 單元測試通過
- [ ] 整合測試通過

---

*文件版本：1.0.0*
*建立時間：2026-04-15*
