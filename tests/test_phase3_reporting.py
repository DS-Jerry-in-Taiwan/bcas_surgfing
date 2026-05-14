"""Phase 3.3 報表與推播測試

測試範圍:
  - MarkdownReporter: 報表格式、S/A/B/C 分組
  - TelegramNotifier: 發送成功/disabled 狀態
  - TerminalNotifier: stdout 輸出
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock


class TestMarkdownReporter:
    """MarkdownReporter 單元測試"""

    def test_generate_report_structure(self):
        """報表包含 S/A/B/C 分段及正確的標的資料"""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("2330", 452.0, 0.012, 5.3, "S", "BUY"),
                ("2454", 350.0, 0.025, 8.1, "A", "BUY"),
                ("3680", 78.5, 0.068, 12.1, "C", "AVOID"),
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            from src.reporters.markdown_reporter import MarkdownReporter
            report = MarkdownReporter().generate_report("2026-05-11")

            # 基本結構
            assert "CBAS 次日交易戰略清單" in report
            assert "2026-05-11" in report

            # S/A/B/C 分段
            assert "S 級" in report
            assert "A 級" in report
            assert "C 級" in report

            # 標的資料
            assert "2330" in report
            assert "2454" in report
            assert "3680" in report

            # 溢價率與風險格式
            assert "%" in report

    def test_generate_report_empty(self):
        """無資料時回傳只有 header 的報表"""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            from src.reporters.markdown_reporter import MarkdownReporter
            report = MarkdownReporter().generate_report("2026-05-11")

            assert "CBAS 次日交易戰略清單" in report
            # 沒有明細資料
            assert "|" not in report

    def test_rating_section_order(self):
        """S/A/B/C 分組順序正確"""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("2330", 452.0, 0.012, 5.3, "S", "BUY"),
                ("3680", 78.5, 0.068, 12.1, "C", "AVOID"),
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            from src.reporters.markdown_reporter import MarkdownReporter
            report = MarkdownReporter().generate_report("2026-05-11")

            # S 級出現在 C 級前面
            s_pos = report.index("S 級")
            c_pos = report.index("C 級")
            assert s_pos < c_pos

    def test_report_has_correct_rating_groups(self):
        """確認報表分組與 DB 資料一致"""
        with patch('psycopg2.connect') as mock_connect:
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [
                ("2330", 452.0, 0.012, 5.3, "S", "BUY"),
                ("3680", 78.5, 0.068, 12.1, "C", "AVOID"),
            ]
            mock_conn = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            from src.reporters.markdown_reporter import MarkdownReporter
            report = MarkdownReporter().generate_report("2026-05-11")

            # 2330 在 S 區段，3680 在 C 區段
            s_section_start = report.index("S 級")
            c_section_start = report.index("C 級")
            assert "2330" in report[s_section_start:c_section_start]
            assert "3680" in report[c_section_start:]


class TestTelegramNotifier:
    """TelegramNotifier 單元測試"""

    @patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token_123',
        'TELEGRAM_CHAT_ID': '-123456789'
    })
    def test_send_success(self):
        """正常發送時回傳 True"""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            mock_post.return_value = mock_resp

            from src.notifiers.telegram_notifier import TelegramNotifier
            result = TelegramNotifier().send("test message")
            assert result is True

    @patch.dict('os.environ', {
        'TELEGRAM_BOT_TOKEN': 'test_token_123',
        'TELEGRAM_CHAT_ID': '-123456789'
    })
    def test_send_api_failure(self):
        """API 失敗時回傳 False 不拋錯"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("API timeout")

            from src.notifiers.telegram_notifier import TelegramNotifier
            result = TelegramNotifier().send("test message")
            assert result is False

    def test_disabled_when_no_token(self):
        """無環境變數時 enabled 為 False"""
        from src.notifiers.telegram_notifier import TelegramNotifier
        notifier = TelegramNotifier()
        assert notifier.enabled is False

    @patch.dict('os.environ', {}, clear=True)
    def test_disabled_when_empty_env(self):
        """所有環境變數為空時 enabled 為 False"""
        from src.notifiers.telegram_notifier import TelegramNotifier
        notifier = TelegramNotifier()
        assert notifier.enabled is False
        result = notifier.send("test")
        assert result is False


class TestTerminalNotifier:
    """TerminalNotifier 單元測試"""

    def test_send(self, capsys):
        """輸出至 stdout"""
        from src.notifiers.terminal_notifier import TerminalNotifier
        result = TerminalNotifier().send("hello world")
        captured = capsys.readouterr()
        assert "hello world" in captured.out
        assert result is True

    def test_send_empty_string(self, capsys):
        """空字串也能正常輸出"""
        from src.notifiers.terminal_notifier import TerminalNotifier
        result = TerminalNotifier().send("")
        captured = capsys.readouterr()
        assert result is True
        # Empty string still prints with separators
        assert "=" in captured.out
