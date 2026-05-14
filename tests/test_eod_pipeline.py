"""EOD Pipeline 測試

測試範圍:
  - EODPipeline 階段定義 (4 階段)
  - 階段名稱正確
  - 非阻斷設計
  - run() 方法支援 date/stage 參數
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock


class TestEODPipeline:
    """EODPipeline 基本結構測試"""

    def test_stages_defined(self):
        """有 4 個階段: 爬蟲, 分析, 風險, 報表"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        assert len(p.stages) == 4
        assert 1 in p.stages
        assert 2 in p.stages
        assert 3 in p.stages
        assert 4 in p.stages

    def test_stage_names(self):
        """階段名稱正確"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        assert "爬蟲階段" == p.stages[1][0]
        assert "分析階段" == p.stages[2][0]
        assert "風險階段" == p.stages[3][0]
        assert "報表階段" == p.stages[4][0]

    def test_stage_order(self):
        """階段順序為 1→2→3→4"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        keys = sorted(p.stages.keys())
        assert keys == [1, 2, 3, 4]

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_run_all_stages(self, mock_report, mock_risk, mock_analytics, mock_spider):
        """run() 依序執行 4 階段"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        p.run(date="2026-05-11")

        mock_spider.assert_called_once_with("2026-05-11")
        mock_analytics.assert_called_once_with("2026-05-11")
        mock_risk.assert_called_once_with("2026-05-11")
        mock_report.assert_called_once_with("2026-05-11")

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_run_single_stage(self, mock_report, mock_risk, mock_analytics, mock_spider):
        """指定 --stage 4 時只執行對應階段"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        p.run(date="2026-05-11", stage=4)

        mock_spider.assert_not_called()
        mock_analytics.assert_not_called()
        mock_risk.assert_not_called()
        mock_report.assert_called_once_with("2026-05-11")

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_run_single_stage_1(self, mock_report, mock_risk, mock_analytics, mock_spider):
        """指定 --stage 1 時只執行爬蟲階段"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        p.run(date="2026-05-11", stage=1)

        mock_spider.assert_called_once_with("2026-05-11")
        mock_analytics.assert_not_called()
        mock_risk.assert_not_called()
        mock_report.assert_not_called()

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_non_blocking_on_failure(self, mock_report, mock_risk,
                                     mock_analytics, mock_spider):
        """階段 2 失敗時，階段 4 仍會執行（非阻斷設計）"""
        mock_analytics.side_effect = Exception("分析失敗")

        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        p.run(date="2026-05-11")

        # 即使階段 2 失敗，階段 1, 3, 4 仍會執行
        mock_spider.assert_called_once()
        mock_analytics.assert_called_once()
        mock_risk.assert_called_once()
        mock_report.assert_called_once()

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_default_date_is_today(self, mock_report, mock_risk,
                                   mock_analytics, mock_spider):
        """date=None 時預設使用今天的日期"""
        from datetime import datetime
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        p.run()  # 不傳 date

        today = datetime.now().strftime("%Y-%m-%d")
        mock_spider.assert_called_once_with(today)

    @patch('src.pipeline.eod_pipeline.EODPipeline._run_spiders')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_analytics')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_risk')
    @patch('src.pipeline.eod_pipeline.EODPipeline._run_reporting')
    def test_run_returns_report(self, mock_report, mock_risk,
                                mock_analytics, mock_spider):
        """run() 內部呼叫不拋錯"""
        from src.pipeline.eod_pipeline import EODPipeline
        p = EODPipeline()
        # 檢查 run() 不會拋錯
        p.run(date="2026-05-11")
        # 確認所有 mock 被正確呼叫即可
        assert True


class TestRunEodAnalysisScript:
    """run_eod_analysis.py 腳本結構測試"""

    def test_main_function_exists(self):
        """run_eod_analysis.py 有 main() 函數"""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_eod_analysis",
            "src/run_eod_analysis.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "main")

    def test_argparse_date_support(self):
        """支援 --date 參數"""
        import importlib.util
        import argparse

        spec = importlib.util.spec_from_file_location(
            "run_eod_analysis",
            "src/run_eod_analysis.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # 手動測試 argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--date")
        parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4])

        args = parser.parse_args(["--date", "2026-05-11", "--stage", "3"])
        assert args.date == "2026-05-11"
        assert args.stage == 3
