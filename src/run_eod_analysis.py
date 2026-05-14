"""
run_eod_analysis.py - EOD 盤後分析啟動腳本

依序執行 4 階段 EOD Pipeline:
  1. 爬蟲階段 (spiders)
  2. 分析階段 (PremiumCalculator + TechnicalAnalyzer)
  3. 風險階段 (RiskAssessor)
  4. 報表階段 (MarkdownReporter + Notifiers)

用法:
    python src/run_eod_analysis.py                    # 執行全部 4 階段
    python src/run_eod_analysis.py --stage 1          # 只跑爬蟲
    python src/run_eod_analysis.py --stage 4          # 只跑報表
    python src/run_eod_analysis.py --date 2026-05-11  # 指定日期
    python src/run_eod_analysis.py --date 2026-05-11 --stage 2  # 指定日期+階段
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
    parser.add_argument(
        "--date",
        help="日期 (YYYY-MM-DD，預設今天)"
    )
    parser.add_argument(
        "--stage",
        type=int,
        choices=[1, 2, 3, 4],
        help="只執行指定階段 (1:爬蟲 2:分析 3:風險 4:報表)"
    )
    args = parser.parse_args()

    pipeline = EODPipeline()
    pipeline.run(date=args.date, stage=args.stage)


if __name__ == "__main__":
    main()
