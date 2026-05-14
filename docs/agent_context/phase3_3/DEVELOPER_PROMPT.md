# Phase 3.3 Developer Prompt - 報表輸出 & 排程自動化

## 🎯 任務概述
實作 EOD Analytics 最終階段：報表輸出 (ReportFormatter) + 推播通知 (Notifiers) + EOD Pipeline + 排程整合。
對應盤後階段四 (17:30)。

## 📁 參考文件
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_3/01_dev_goal_context.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_3/arch_design.md`
- `/home/ubuntu/projects/bcas_quant/docs/agent_context/phase3_3/05_validation_checklist.md`

## 📁 既有資源 (直接使用，不需重寫)

### Slack AlertManager (既有)
```python
from src.framework.alerts import AlertManager, SlackAlertBackend
# SlackAlertBackend 已存在，webhook_url/channel 從環境變數讀取
```

### DB 資料表 (Phase 3.0)
- `daily_analysis_results` — date, symbol, close_price, premium_ratio, risk_score, final_rating
- `trading_signals` — date, symbol, signal_type, confidence

### Phase 3.1~3.2 模組
```python
from src.analytics.premium_calculator import PremiumCalculator
from src.analytics.technical_analyzer import TechnicalAnalyzer
from src.analytics.chip_profiler import ChipProfiler
from src.analytics.risk_assessor import RiskAssessor
```

### DB_CONFIG
```python
from src.run_daily import DB_CONFIG
```

## 📋 實作項目

### 1. src/reporters/markdown_reporter.py

```python
"""
MarkdownReporter - 產出 Markdown 格式報表
"""
from typing import List, Dict, Any
import psycopg2
from src.run_daily import DB_CONFIG


class MarkdownReporter:
    """Markdown 格式報表產生器"""
    
    REPORT_HEADER = """# CBAS 次日交易戰略清單
📅 日期: {date}

"""
    
    SECTION_HEADER = """
## {icon} {title}
| 標的 | 收盤價 | 溢價率 | 風險佔比 | 評級 | 信號 |
|------|--------|--------|---------|------|------|
"""
    
    RATING_CONFIG = [
        ("S", "🟢 S 級 (強烈買入)"),
        ("A", "🔵 A 級 (可布局)"),
        ("B", "🟡 B 級 (觀察)"),
        ("C", "🔴 C 級 (避開)"),
    ]
    
    def generate_report(self, date: str) -> str:
        """
        從 DB 讀取資料，產出完整報表
        
        Args:
            date: 日期 (YYYY-MM-DD)
        
        Returns:
            Markdown 報表字串
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            # 讀取分析結果
            cursor.execute("""
                SELECT d.symbol, d.close_price, d.premium_ratio, 
                       d.broker_risk_pct, d.final_rating,
                       t.signal_type
                FROM daily_analysis_results d
                LEFT JOIN trading_signals t 
                    ON d.date = t.date AND d.symbol = t.symbol
                WHERE d.date = %s AND d.is_junk = false
                ORDER BY d.final_rating, d.symbol
            """, (date,))
            rows = cursor.fetchall()
            
            # 依評級分組
            by_rating = {r: [] for r, _ in self.RATING_CONFIG}
            for row in rows:
                rating = row[4] or "C"
                if rating in by_rating:
                    by_rating[rating].append(row)
            
            # 產生報表
            lines = [self.REPORT_HEADER.format(date=date)]
            
            for rating, title in self.RATING_CONFIG:
                items = by_rating.get(rating, [])
                if not items:
                    continue
                lines.append(self.SECTION_HEADER.format(icon=rating, title=title))
                for row in items:
                    symbol, close, premium, risk, _, signal = row
                    premium_str = f"{float(premium)*100:.2f}%" if premium else "N/A"
                    risk_str = f"{float(risk):.1f}%" if risk else "N/A"
                    close_str = f"{float(close):.2f}" if close else "N/A"
                    signal_str = signal or "HOLD"
                    lines.append(f"| {symbol} | {close_str} | {premium_str} | {risk_str} | {rating} | {signal_str} |\n")
            
            return "".join(lines)
            
        finally:
            cursor.close()
            conn.close()
```

### 2. src/reporters/formatter.py (Rich 格式)

```python
"""
RichFormatter - 使用 Rich 在終端機輸出彩色報表
"""
from rich.console import Console
from rich.table import Table
from rich.style import Style
import psycopg2
from src.run_daily import DB_CONFIG


class RichFormatter:
    """終端機 Rich 格式化輸出"""
    
    RATING_STYLES = {
        "S": Style(color="green", bold=True),
        "A": Style(color="blue", bold=True),
        "B": Style(color="yellow", bold=True),
        "C": Style(color="red", bold=True),
    }
    
    def __init__(self):
        self.console = Console()
    
    def print_report(self, date: str):
        """輸出彩色報表至終端"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT d.symbol, d.close_price, d.premium_ratio,
                       d.broker_risk_pct, d.final_rating,
                       t.signal_type
                FROM daily_analysis_results d
                LEFT JOIN trading_signals t
                    ON d.date = t.date AND d.symbol = t.symbol
                WHERE d.date = %s AND d.is_junk = false
                ORDER BY d.final_rating, d.symbol
            """, (date,))
            rows = cursor.fetchall()
            
            # 依評級分組
            from collections import defaultdict
            groups = defaultdict(list)
            for row in rows:
                groups[row[4] or "C"].append(row)
            
            self.console.print(f"\n[bold]📅 CBAS 次日交易戰略清單 - {date}[/bold]\n")
            
            for rating, title, icon in [
                ("S", "強烈買入", "🟢"),
                ("A", "可布局", "🔵"),
                ("B", "觀察", "🟡"),
                ("C", "避開", "🔴"),
            ]:
                items = groups.get(rating, [])
                if not items:
                    continue
                
                table = Table(title=f"{icon} {rating} 級 ({title})", 
                              style=self.RATING_STYLES.get(rating))
                table.add_column("標的", style="bold")
                table.add_column("收盤價", justify="right")
                table.add_column("溢價率", justify="right")
                table.add_column("風險", justify="right")
                table.add_column("信號")
                
                for row in items:
                    symbol, close, premium, risk, _, signal = row
                    table.add_row(
                        symbol,
                        f"{float(close):.2f}" if close else "N/A",
                        f"{float(premium)*100:.2f}%" if premium else "N/A",
                        f"{float(risk):.1f}%" if risk else "N/A",
                        signal or "HOLD",
                    )
                
                self.console.print(table)
                self.console.print()
        
        finally:
            cursor.close()
            conn.close()
```

### 3. src/notifiers/telegram_notifier.py

```python
"""
TelegramNotifier - Telegram 推播
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
            logger.warning("Telegram notifier disabled: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    
    def send(self, message: str) -> bool:
        """發送 Telegram 訊息"""
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
```

### 4. src/notifiers/terminal_notifier.py

```python
"""
TerminalNotifier - 終端輸出
"""
import logging

logger = logging.getLogger(__name__)


class TerminalNotifier:
    """直接輸出至終端"""
    
    def send(self, message: str) -> bool:
        """輸出至 stdout"""
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60 + "\n")
        logger.info("Report printed to terminal")
        return True
```

### 5. src/pipeline/eod_pipeline.py

```python
"""
EOD Pipeline - 盤後分析主管道
依序執行 4 階段: 爬蟲 → 分析 → 風險 → 報表
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EODPipeline:
    """EOD 分析管道"""
    
    def __init__(self):
        self.stages = {
            1: ("爬蟲階段", self._run_spiders),
            2: ("分析階段", self._run_analytics),
            3: ("風險階段", self._run_risk),
            4: ("報表階段", self._run_reporting),
        }
    
    def _run_spiders(self, date: str):
        """Stage 1: 爬蟲 (呼叫 run_daily)"""
        from src.run_daily import step_spiders, flush_pipelines
        results, records, pipelines = step_spiders()
        flush_pipelines(pipelines)
        return results
    
    def _run_analytics(self, date: str):
        """Stage 2: 分析"""
        from src.analytics.premium_calculator import PremiumCalculator
        from src.analytics.technical_analyzer import TechnicalAnalyzer
        
        pc = PremiumCalculator()
        results = pc.analyze(date)
        pc.save_results(date, results)
        logger.info(f"  PremiumCalculator: {len(results)} 筆")
        
        ta = TechnicalAnalyzer()
        results = ta.analyze(date, results)
        logger.info(f"  TechnicalAnalyzer: {len(results)} 筆")
    
    def _run_risk(self, date: str):
        """Stage 3: 風險評級"""
        from src.analytics.risk_assessor import RiskAssessor
        
        ra = RiskAssessor()
        results = ra.run_analysis(date)
        logger.info(f"  RiskAssessor: {len(results)} 筆")
    
    def _run_reporting(self, date: str):
        """Stage 4: 報表 + 推播"""
        from src.reporters.markdown_reporter import MarkdownReporter
        from src.notifiers.terminal_notifier import TerminalNotifier
        from src.notifiers.telegram_notifier import TelegramNotifier
        
        reporter = MarkdownReporter()
        report = reporter.generate_report(date)
        
        # 終端輸出
        TerminalNotifier().send(report)
        
        # Telegram 推播
        TelegramNotifier().send(report)
        
        return report
    
    def run(self, date: str = None, stage: int = None):
        """執行 EOD Pipeline"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"🚀 EOD Pipeline 開始 - {date}")
        
        for s, (name, func) in sorted(self.stages.items()):
            if stage is not None and s != stage:
                continue
            
            logger.info(f"[{s}/4] {name} 開始")
            try:
                result = func(date)
                logger.info(f"[{s}/4] {name} 完成 ✅")
            except Exception as e:
                logger.error(f"[{s}/4] {name} 失敗 ❌: {e}")
        
        logger.info(f"🏁 EOD Pipeline 完成 - {date}")
```

### 6. src/run_eod_analysis.py

```python
"""
run_eod_analysis.py - EOD 分析啟動腳本

用法:
  python src/run_eod_analysis.py                    # 執行全部 4 階段
  python src/run_eod_analysis.py --stage 1          # 只跑爬蟲
  python src/run_eod_analysis.py --stage 4          # 只跑報表
  python src/run_eod_analysis.py --date 2026-05-11  # 指定日期
"""
import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from pipeline.eod_pipeline import EODPipeline


def main():
    parser = argparse.ArgumentParser(description="BCAS EOD 盤後分析")
    parser.add_argument("--date", help="日期 (YYYY-MM-DD，預設今天)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4],
                        help="只執行指定階段 (1:爬蟲 2:分析 3:風險 4:報表)")
    args = parser.parse_args()
    
    pipeline = EODPipeline()
    pipeline.run(date=args.date, stage=args.stage)


if __name__ == "__main__":
    main()
```

### 7. tests/test_phase3_reporting.py

```python
"""Phase 3.3 報表與推播測試"""
import sys
sys.path.insert(0, 'src')

from unittest.mock import patch, MagicMock


class TestMarkdownReporter:
    
    @patch('src.reporters.markdown_reporter.psycopg2')
    def test_generate_report_structure(self, mock_db):
        """報表包含 S/A/B/C 分段"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2330", 452.0, 0.012, 5.3, "S", "BUY"),
            ("3680", 78.5, 0.068, 12.1, "C", "AVOID"),
        ]
        mock_db.connect.return_value.cursor.return_value = mock_cursor
        
        from src.reporters.markdown_reporter import MarkdownReporter
        report = MarkdownReporter().generate_report("2026-05-11")
        
        assert "CBAS 次日交易戰略清單" in report
        assert "S 級" in report
        assert "C 級" in report
        assert "2330" in report
        assert "3680" in report


class TestTelegramNotifier:
    
    @patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': 'test', 'TELEGRAM_CHAT_ID': 'test'})
    @patch('src.notifiers.telegram_notifier.requests')
    def test_send_success(self, mock_requests):
        from src.notifiers.telegram_notifier import TelegramNotifier
        mock_requests.post.return_value.raise_for_status.return_value = None
        result = TelegramNotifier().send("test message")
        assert result is True
    
    def test_disabled_when_no_token(self):
        from src.notifiers.telegram_notifier import TelegramNotifier
        notifier = TelegramNotifier()
        assert notifier.enabled is False


class TestTerminalNotifier:
    def test_send(self, capsys):
        from src.notifiers.terminal_notifier import TerminalNotifier
        TerminalNotifier().send("hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out
```

### 8. tests/test_eod_pipeline.py (基本測試)

```python
"""EOD Pipeline 測試"""
import sys
sys.path.insert(0, 'src')


class TestEODPipeline:
    
    def test_stages_defined(self):
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        assert len(p.stages) == 4
        assert 1 in p.stages
        assert "爬蟲階段" == p.stages[1][0]
        assert "報表階段" == p.stages[4][0]
```

## ✅ 驗收清單
- [ ] MarkdownReporter 產生正確格式報表 (S/A/B/C 分組)
- [ ] TelegramNotifier 成功發送 (mock)
- [ ] TelegramNotifier token 不存在時 disabled
- [ ] TerminalNotifier 輸出至 stdout
- [ ] EODPipeline 有 4 個階段
- [ ] run_eod_analysis.py CLI 可執行 (`--help`)

## 完成後驗證
```bash
python -m pytest tests/test_phase3_reporting.py tests/test_eod_pipeline.py -v
python -m pytest tests/ -v  # 全部回歸
python -m src.run_eod_analysis.py --help
```
