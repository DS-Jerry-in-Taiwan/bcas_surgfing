"""
EOD Pipeline - 盤後分析主管道

依序執行 4 階段 (非阻斷設計，單一階段失敗不影響後續):
  1. 爬蟲階段 - 執行 run_daily 爬蟲
  2. 分析階段 - PremiumCalculator + TechnicalAnalyzer
  3. 風險階段 - RiskAssessor (含 ChipProfiler)
  4. 報表階段 - MarkdownReporter + Notifiers (Telegram/Terminal)

用法:
    from src.pipeline.eod_pipeline import EODPipeline
    EODPipeline().run(date="2026-05-11")
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EODPipeline:
    """EOD 分析管道（非阻斷設計）"""

    def __init__(self):
        self.stages = {
            1: ("爬蟲階段", self._run_spiders),
            2: ("分析階段", self._run_analytics),
            3: ("風險階段", self._run_risk),
            4: ("報表階段", self._run_reporting),
        }

    def _run_spiders(self, date: str):
        """Stage 1: 爬蟲 (呼叫 run_daily.spiders + flush)

        Args:
            date: 日期字串，此階段未使用 (從 run_daily 內部取得)
        """
        from run_daily import step_spiders, flush_pipelines
        results, records, pipelines = step_spiders()
        flush_pipelines(pipelines)
        return results

    def _run_analytics(self, date: str):
        """Stage 2: 分析 (PremiumCalculator + TechnicalAnalyzer)

        Args:
            date: 日期 (YYYY-MM-DD)
        """
        from analytics.premium_calculator import PremiumCalculator
        from analytics.technical_analyzer import TechnicalAnalyzer

        pc = PremiumCalculator()
        results = pc.analyze(date)
        pc.save_results(date, results)
        logger.info(f"  ✅ PremiumCalculator: {len(results)} 筆")

        ta = TechnicalAnalyzer()
        results = ta.analyze(date, results)
        logger.info(f"  ✅ TechnicalAnalyzer: {len(results)} 筆")

    def _run_risk(self, date: str):
        """Stage 3: 風險評級 (RiskAssessor)

        Args:
            date: 日期 (YYYY-MM-DD)
        """
        from analytics.risk_assessor import RiskAssessor

        ra = RiskAssessor()
        results = ra.run_analysis(date)
        logger.info(f"  ✅ RiskAssessor: {len(results)} 筆")

    def _run_reporting(self, date: str) -> str:
        """Stage 4: 報表 + 推播 (MarkdownReporter + Notifiers)

        Args:
            date: 日期 (YYYY-MM-DD)

        Returns:
            產出的報表字串
        """
        from reporters.markdown_reporter import MarkdownReporter
        from notifiers.terminal_notifier import TerminalNotifier
        from notifiers.telegram_notifier import TelegramNotifier

        reporter = MarkdownReporter()
        report = reporter.generate_report(date)
        logger.info(f"  ✅ MarkdownReporter: {len(report)} chars")

        # 終端輸出
        TerminalNotifier().send(report)

        # Telegram 推播
        TelegramNotifier().send(report)

        return report

    def run(self, date: str = None, stage: int = None):
        """執行 EOD Pipeline

        Args:
            date: 日期 (YYYY-MM-DD)，預設今天
            stage: 指定只執行某一階段 (1-4)，預設 None 表示全部執行
        """
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
