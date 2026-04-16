"""
Alert 單元測試
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.alerts import (
    AlertLevel, 
    AlertMessage, 
    SlackAlertBackend,
    AlertManager
)


class TestAlertLevel:
    """AlertLevel 測試"""
    
    def test_level_values(self):
        """測試等級值"""
        assert AlertLevel.DEBUG.value == "DEBUG"
        assert AlertLevel.INFO.value == "INFO"
        assert AlertLevel.WARNING.value == "WARNING"
        assert AlertLevel.ERROR.value == "ERROR"
        assert AlertLevel.CRITICAL.value == "CRITICAL"


class TestAlertMessage:
    """AlertMessage 測試"""
    
    def test_create_message(self):
        """測試創建訊息"""
        msg = AlertMessage(
            level=AlertLevel.ERROR,
            title="Test Alert",
            message="Test message",
            spider_name="TestSpider"
        )
        
        assert msg.level == AlertLevel.ERROR
        assert msg.title == "Test Alert"
        assert msg.message == "Test message"
        assert msg.spider_name == "TestSpider"
    
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
        assert "Test Alert" in blocks[0]["text"]["text"]
    
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
    
    def test_emoji_mapping(self):
        """測試表情映射"""
        msg = AlertMessage(level=AlertLevel.ERROR, title="Test", message="Test")
        assert "❌" in msg._get_emoji()
        
        msg = AlertMessage(level=AlertLevel.WARNING, title="Test", message="Test")
        assert "⚠️" in msg._get_emoji()
        
        msg = AlertMessage(level=AlertLevel.INFO, title="Test", message="Test")
        assert "ℹ️" in msg._get_emoji()


class TestSlackAlertBackend:
    """SlackAlertBackend 測試"""
    
    def test_initialization(self):
        """測試初始化"""
        backend = SlackAlertBackend(
            webhook_url="https://hooks.slack.com/test",
            channel="#test",
            min_level="ERROR"
        )
        
        assert backend.is_configured() is True
        assert backend.channel == "#test"
        assert backend.min_level == AlertLevel.ERROR
    
    def test_not_configured(self):
        """測試未配置"""
        backend = SlackAlertBackend(webhook_url="")
        assert backend.is_configured() is False


class TestAlertManager:
    """AlertManager 測試"""
    
    def test_initialization(self):
        """測試初始化"""
        manager = AlertManager()
        assert isinstance(manager.backends, list)
    
    def test_alert_levels(self):
        """測試各等級告警"""
        manager = AlertManager()
        
        # 不應拋出例外
        manager.debug(title="Debug", message="Debug test")
        manager.info(title="Info", message="Info test")
        manager.warning(title="Warning", message="Warning test")
        manager.error(title="Error", message="Error test")
        manager.critical(title="Critical", message="Critical test")
    
    def test_alert_with_metadata(self):
        """測試帶元數據的告警"""
        manager = AlertManager()
        
        manager.error(
            title="Error with metadata",
            message="Error details",
            spider_name="TestSpider",
            request_url="https://example.com",
            error_details="Traceback here",
            custom_field="custom_value"
        )
