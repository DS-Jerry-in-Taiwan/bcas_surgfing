"""
TerminalNotifier - 終端輸出通知

將訊息輸出至 stdout，適用於本地開發與除錯。

用法:
    from src.notifiers.terminal_notifier import TerminalNotifier
    TerminalNotifier().send("Hello from BCAS!")
"""
import logging

logger = logging.getLogger(__name__)


class TerminalNotifier:
    """直接輸出至終端"""

    def send(self, message: str) -> bool:
        """輸出至 stdout

        Args:
            message: 要輸出的內容

        Returns:
            永遠回傳 True
        """
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60 + "\n")
        logger.info("Report printed to terminal")
        return True
