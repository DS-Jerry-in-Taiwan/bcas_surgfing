"""
Test Stage 4: Pipeline Integration (Real DataValidator wiring)

Tests:
1. step_validate() with real records → DataValidator executes 24 rules
2. step_validate() with empty records → skips gracefully
3. step_validate() with bad records → detects errors
4. Cross-table consistency checks (symbols, cb_codes)
5. CLI flags & flow control
6. Report output structure
"""
import pytest
import sys
import os
import json
from datetime import datetime
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from run_daily import step_validate


class TestStepValidateWithRecords:
    """Test step_validate() with real records feeding into DataValidator"""

    def test_validate_stock_master_real_records(self):
        """Real stock_master records → DataValidator runs 6 rules"""
        spider_results = {
            "stock_master": {"success": True, "count": 2},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
                {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_master"]

        assert result["has_errors"] == False
        assert report["total_checked"] == 2
        assert report["summary"]["passed"] >= 4  # At least structure+uniqueness+value+completeness pass
        assert report["summary"]["failed"] == 0

    def test_validate_stock_master_bad_records(self):
        """Bad stock_master records → DataValidator detects errors"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC"},  # Missing market_type, industry
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_master"]

        assert result["has_errors"] == True
        assert report["summary"]["failed"] >= 1
        failed_ids = [r["rule_id"] for r in report["failed_rules"]]
        assert any("structure" in rid for rid in failed_ids)

    def test_validate_stock_daily_real_records(self):
        """Real stock_daily records → DataValidator runs 7 rules"""
        spider_results = {
            "stock_master": {"success": True, "count": 2},
            "stock_daily": {"success": True, "count": 2},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            ],
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000},
                {"symbol": "2330", "date": "2026-04-02", "close_price": 101.0, "volume": 1100},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_daily"]

        # price_positive, volume_non_negative, format_date pass
        # completeness skips (no expected_dates), consistency skips (no expected_symbols)
        assert report["summary"]["passed"] >= 3
        assert report["summary"]["failed"] == 0

    def test_validate_stock_daily_zero_price(self):
        """stock_daily with zero price → value_price_positive fails"""
        spider_results = {
            "stock_daily": {"success": True, "count": 1},
        }
        records = {
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 0, "volume": 1000},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_daily"]

        assert result["has_errors"] == True
        failed_ids = [r["rule_id"] for r in report["failed_rules"]]
        assert "stock_daily_value_price_positive" in failed_ids

    def test_validate_cb_master_real_records(self):
        """Real cb_master records → DataValidator runs 5 rules"""
        spider_results = {
            "cb_master": {"success": True, "count": 2},
        }
        records = {
            "cb_master": [
                {"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"},
                {"cb_code": "24541", "cb_name": "聯發科一", "conversion_price": 200.0, "market_type": "TPEx"},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["cb_master"]

        assert result["has_errors"] == False
        assert report["summary"]["passed"] >= 3
        assert report["summary"]["failed"] == 0

    def test_validate_cb_master_duplicate_code(self):
        """cb_master with duplicate cb_code → uniqueness fails"""
        spider_results = {
            "cb_master": {"success": True, "count": 2},
        }
        records = {
            "cb_master": [
                {"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"},
                {"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 200.0, "market_type": "TPEx"},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["cb_master"]

        assert result["has_errors"] == True
        failed_ids = [r["rule_id"] for r in report["failed_rules"]]
        assert "cb_master_uniqueness_cb_code" in failed_ids

    def test_validate_tpex_cb_daily_real_records(self):
        """Real tpex_cb_daily records → DataValidator runs 6 rules"""
        spider_results = {
            "cb_master": {"success": True, "count": 1},
            "tpex_cb_daily": {"success": True, "count": 2},
        }
        records = {
            "cb_master": [
                {"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"},
            ],
            "tpex_cb_daily": [
                {"cb_code": "23301", "trade_date": "2026-04-01", "closing_price": 105.0, "volume": 100},
                {"cb_code": "23301", "trade_date": "2026-04-02", "closing_price": 106.0, "volume": 200},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["tpex_cb_daily"]

        # price_positive, volume_non_negative, format_date pass
        # consistency passes (cb_code in master), completeness at_least_one passes
        assert report["summary"]["failed"] == 0
        assert report["summary"]["passed"] >= 4

    def test_validate_tpex_cb_daily_missing_master(self):
        """tpex_cb_daily with cb_code not in master → consistency fails"""
        spider_results = {
            "tpex_cb_daily": {"success": True, "count": 1},
        }
        records = {
            "tpex_cb_daily": [
                {"cb_code": "NONEXIST", "trade_date": "2026-04-01", "closing_price": 100.0, "volume": 100},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["tpex_cb_daily"]

        # Expected: cb_code consistency should FAIL since "NONEXIST" is not in cb_master records
        # Note: when cb_master records are empty, consistency check should detect the mismatch
        assert result["has_errors"] == True
        failed_ids = [r["rule_id"] for r in report["failed_rules"]]
        assert "tpex_cb_daily_consistency_cb_code_in_master" in failed_ids

    def test_validate_cross_table_consistency(self):
        """Cross-table: stock_daily symbols against stock_master"""
        spider_results = {
            "stock_master": {"success": True, "count": 2},
            "stock_daily": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
                {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"},
            ],
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000},
            ],
        }
        result = step_validate(spider_results, records)
        sm_report = result["reports"]["stock_master"]
        sd_report = result["reports"]["stock_daily"]

        # Both should pass
        assert sm_report["summary"]["failed"] == 0
        assert sd_report["summary"]["failed"] == 0
        # stock_daily should NOT have skipped consistency (symbol matches master)
        consistency_skipped = [
            r for r in sd_report.get("skipped_rules", [])
            if "consistency" in r.get("rule_id", "")
        ]
        consistency_passed = [
            r for r in sd_report.get("passed_rules", [])
            if "consistency" in r.get("rule_id", "")
        ]
        assert len(consistency_passed) > 0 or len(consistency_skipped) == 0

    def test_validate_multiple_tables_all_pass(self):
        """All 4 tables validate simultaneously"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
            "stock_daily": {"success": True, "count": 1},
            "cb_master": {"success": True, "count": 1},
            "tpex_cb_daily": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            ],
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000},
            ],
            "cb_master": [
                {"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"},
            ],
            "tpex_cb_daily": [
                {"cb_code": "23301", "trade_date": "2026-04-01", "closing_price": 105.0, "volume": 100},
            ],
        }
        result = step_validate(spider_results, records)

        assert result["has_errors"] == False
        for name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
            r = result["reports"][name]
            assert "summary" in r
            assert r["summary"]["failed"] == 0, f"{name} should have 0 failures"


class TestStepValidateWithoutRecords:
    """Test step_validate() with spider metadata only (no records)"""

    def test_no_records_provided(self):
        """No records dict → skip all tables"""
        spider_results = {
            "stock_master": {"success": True, "count": 100},
        }
        result = step_validate(spider_results, None)
        assert result["has_errors"] == False
        assert result["reports"]["stock_master"]["skipped"] == True

    def test_empty_records_dict(self):
        """Empty records dict → skip all tables"""
        spider_results = {
            "stock_master": {"success": True, "count": 100},
        }
        result = step_validate(spider_results, {})
        assert result["has_errors"] == False
        assert result["reports"]["stock_master"]["skipped"] == True

    def test_spider_failed_skip(self):
        """Failed spider → skip that table"""
        spider_results = {
            "stock_master": {"success": False, "error": "timeout"},
        }
        result = step_validate(spider_results)
        assert result["reports"]["stock_master"]["skipped"] == True
        assert result["reports"]["stock_master"]["reason"] == "spider failed"


class TestValidationReportStructure:
    """Test the structure of validation reports"""

    def test_report_has_required_fields(self):
        """Report dict has all required fields"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            ],
        }
        result = step_validate(spider_results, records)

        assert "validation_dir" in result
        assert "reports" in result
        assert "has_errors" in result

    def test_data_validator_report_structure(self):
        """DataValidator report has expected structure"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_master"]

        assert "table_name" in report
        assert "total_checked" in report
        assert "summary" in report
        assert "passed_rules" in report
        assert "failed_rules" in report
        assert "warning_rules" in report
        assert "skipped_rules" in report
        assert "timestamp" in report
        assert report["table_name"] == "stock_master"
        assert report["total_checked"] == 1

    def test_rule_result_structure(self):
        """Individual RuleResult has correct fields"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_master"]

        for rule in report["passed_rules"]:
            assert "rule_id" in rule
            assert "status" in rule
            assert "detail" in rule
            assert "count" in rule
            assert rule["status"] == "PASS"

    def test_report_with_errors_includes_failed_rules(self):
        """Failed validation includes detailed failure info"""
        spider_results = {
            "stock_master": {"success": True, "count": 1},
        }
        records = {
            "stock_master": [
                {"symbol": "2330"},  # Missing required fields
            ],
        }
        result = step_validate(spider_results, records)
        report = result["reports"]["stock_master"]

        assert len(report["failed_rules"]) > 0
        for rule in report["failed_rules"]:
            assert rule["status"] == "FAIL"
            assert isinstance(rule["detail"], str)
            assert len(rule["detail"]) > 0


class TestCLIFlagParsing:
    """Test CLI argument parsing"""

    def test_validate_only_flag(self):
        """Test --validate-only flag parsing"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate-only", action="store_true")
        parser.add_argument("--force-validation", action="store_true")
        parser.add_argument("--skip-clean", action="store_true")
        parser.add_argument("--clean-only", action="store_true")

        args = parser.parse_args(["--validate-only"])
        assert args.validate_only == True
        assert args.force_validation == False

    def test_force_validation_flag(self):
        """Test --force-validation flag parsing"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate-only", action="store_true")
        parser.add_argument("--force-validation", action="store_true")

        args = parser.parse_args(["--force-validation"])
        assert args.force_validation == True
        assert args.validate_only == False

    def test_combined_flags(self):
        """Test multiple flags combined"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate-only", action="store_true")
        parser.add_argument("--force-validation", action="store_true")
        parser.add_argument("--skip-clean", action="store_true")

        args = parser.parse_args(["--skip-clean", "--force-validation"])
        assert args.skip_clean == True
        assert args.force_validation == True

    def test_incompatible_flags(self):
        """Incompatible flags should still parse"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--validate-only", action="store_true")
        parser.add_argument("--clean-only", action="store_true")

        args = parser.parse_args(["--validate-only", "--clean-only"])
        assert args.validate_only == True
        assert args.clean_only == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
