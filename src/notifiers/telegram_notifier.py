"""
TelegramNotifier - Telegram 推播通知

透過 Telegram Bot API 發送 Markdown 格式訊息。
從環境變數讀取 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID。

用法:
    from src.notifiers.telegram_notifier import TelegramNotifier
    TelegramNotifier().send("Hello from BCAS!")

環境變數:
    TELEGRAM_BOT_TOKEN: Bot token (from @BotFather)
    TELEGRAM_CHAT_ID:   目標聊天室 ID
"""
import os
import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram Bot 推播"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning(
                "Telegram notifier disabled: "
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"
            )

    def send(self, message: str) -> bool:
        """發送 Telegram 訊息

        Args:
            message: 訊息內容 (支援 Markdown 格式)

        Returns:
            True 表示發送成功，False 表示未啟用或發送失敗
        """
        if not self.enabled:
            logger.info("Telegram notifier disabled, message not sent")
            return False

        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown",
            }, timeout=10)
            resp.raise_for_status()
            logger.info(f"Telegram message sent ({len(message)} chars)")
            return True
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
