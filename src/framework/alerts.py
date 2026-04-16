"""
Feapder Framework - 告警模組

支援 Slack 告警通知
"""
from __future__ import annotations

import requests
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警等級枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    PRIORITY = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    
    def __ge__(self, other):
        return self.PRIORITY[self.value] >= self.PRIORITY[other.value]
    
    def __gt__(self, other):
        return self.PRIORITY[self.value] > self.PRIORITY[other.value]
    
    def __le__(self, other):
        return self.PRIORITY[self.value] <= self.PRIORITY[other.value]
    
    def __lt__(self, other):
        return self.PRIORITY[self.value] < self.PRIORITY[other.value]


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
                    "text": f"{self._get_emoji()} {self.title}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Level:*\n{self.level.value}"},
                    {"type": "mrkdwn", "text": f"*Spider:*\n{self.spider_name or 'N/A'}"},
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
    
    def _get_emoji(self) -> str:
        """取得等級對應的表情"""
        emoji_map = {
            AlertLevel.DEBUG: "🔍",
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }
        return emoji_map.get(self.level, "📢")
    
    def to_attachment(self) -> Dict:
        """轉換為 Slack Attachment 格式"""
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
            "footer": f"Spider ID: {self.spider_id}" if self.spider_id else "Feapder Alert",
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
    
    def __init__(self, webhook_url: str = "", channel: str = "#crawler-alerts", min_level: str = "ERROR"):
        self.webhook_url = webhook_url
        self.channel = channel
        self.min_level = AlertLevel[min_level.upper()]
        self.session = requests.Session()
    
    def is_configured(self) -> bool:
        return bool(self.webhook_url)
    
    def send(self, message: AlertMessage) -> bool:
        """發送 Slack 訊息"""
        if not self.is_configured():
            logger.debug("Slack alert not configured, skipping")
            return False
        
        try:
            if message.level < self.min_level:
                logger.debug(f"Message level {message.level.value} below minimum {self.min_level.value}")
                return False
            
            payload = {
                "channel": self.channel,
                "blocks": message.to_slack_blocks(),
                "attachments": [message.to_attachment()]
            }
            
            response = self.session.post(
                self.webhook_url,
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
        try:
            from src.settings.feapder_settings import settings
            
            if settings.slack_alert.is_configured:
                self.backends.append(SlackAlertBackend(
                    webhook_url=settings.slack_alert.webhook_url,
                    channel=settings.slack_alert.channel,
                    min_level=settings.slack_alert.min_level
                ))
                logger.info("Slack alert backend initialized")
        except ImportError:
            logger.warning("Settings module not available, alerts disabled")
    
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
        """發送告警"""
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


alert_manager = AlertManager()
