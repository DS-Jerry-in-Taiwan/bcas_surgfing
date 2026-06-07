"""
run_eod_analysis.py - EOD 盤後分析啟動腳本

依序執行 3 階段 EOD Pipeline:
  1. 分析階段 (PremiumCalculator + TechnicalAnalyzer)
  2. 風險階段 (RiskAssessor)
  3. 報表階段 (MarkdownReporter + Notifiers)

用法:
    python src/run_eod_analysis.py                    # 執行全部 3 階段
    python src/run_eod_analysis.py --date 2026-05-11  # 指定日期
"""
import argparse
import logging
import sys
import os

_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _THIS_DIR)                                # src/
sys.path.insert(0, os.path.abspath(os.path.join(_THIS_DIR, "..")))  # project root (for src.xxx imports)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from pipeline.eod_pipeline import EODPipeline


def main():
    parser = argparse.ArgumentParser(description="BCAS EOD 盤後分析")
    parser.add_argument(
        "--date",
        help="日期 (YYYY-MM-DD，預設今天)"
    )
    args = parser.parse_args()

    pipeline = EODPipeline()
    pipeline.run(date=args.date)


if __name__ == "__main__":
    main()
