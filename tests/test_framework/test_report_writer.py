"""Test report_writer and rules edge cases for coverage"""
import pytest
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from validators.rules import RuleSeverity, ValidationRule, create_rule, is_error_rule, is_warning_rule
from validators.report import ValidationReport, RuleResult
from validators.report_writer import ReportWriter


class TestRulesEdgeCases:
    """Edge cases in rules.py"""

    def test_rule_empty_rule_id_raises(self):
        with pytest.raises(ValueError, match="rule_id"):
            ValidationRule(
                rule_id="", table_name="test", description="test",
                severity=RuleSeverity.ERROR, checker_fn=lambda x: (True, "ok"),
            )

    def test_rule_empty_table_name_raises(self):
        with pytest.raises(ValueError, match="table_name"):
            ValidationRule(
                rule_id="test", table_name="", description="test",
                severity=RuleSeverity.ERROR, checker_fn=lambda x: (True, "ok"),
            )

    def test_is_error_rule(self):
        rule = create_rule("test", "t", "d", RuleSeverity.ERROR, lambda x: (True, ""))
        assert is_error_rule(rule) == True
        assert is_warning_rule(rule) == False

    def test_is_warning_rule(self):
        rule = create_rule("test", "t", "d", RuleSeverity.WARNING, lambda x: (True, ""))
        assert is_warning_rule(rule) == True
        assert is_error_rule(rule) == False


class TestReportWriter:
    """Direct tests for ReportWriter"""

    def test_save_report(self, tmp_path):
        report = ValidationReport("stock_master", total_checked=10)
        filepath = ReportWriter.save_report(report, str(tmp_path))
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert data["table_name"] == "stock_master"
        assert data["total_checked"] == 10
        assert "timestamp" in data

    def test_save_report_with_results(self, tmp_path):
        report = ValidationReport("stock_daily", total_checked=5)
        report.passed_rules.append(
            RuleResult("test_rule", "PASS", "all good", 5)
        )
        report.failed_rules.append(
            RuleResult("fail_rule", "FAIL", "bad data", 1)
        )
        filepath = ReportWriter.save_report(report, str(tmp_path))
        with open(filepath) as f:
            data = json.load(f)
        assert len(data["passed_rules"]) == 1
        assert len(data["failed_rules"]) == 1

    def test_save_summary(self, tmp_path):
        r1 = ValidationReport("stock_master", total_checked=10)
        r1.passed_rules.append(RuleResult("r1", "PASS", "", 10))
        r2 = ValidationReport("stock_daily", total_checked=5)
        r2.passed_rules.append(RuleResult("r2", "PASS", "", 5))

        filepath = ReportWriter.save_summary(
            {"stock_master": r1, "stock_daily": r2}, str(tmp_path)
        )
        with open(filepath) as f:
            data = json.load(f)
        assert "tables" in data
        assert "overall_pass" in data
        assert data["overall_pass"] == True

    def test_save_summary_with_failures(self, tmp_path):
        r = ValidationReport("test", total_checked=1)
        r.failed_rules.append(RuleResult("f", "FAIL", "error", 1))
        filepath = ReportWriter.save_summary({"test": r}, str(tmp_path))
        with open(filepath) as f:
            data = json.load(f)
        assert data["overall_pass"] == False
