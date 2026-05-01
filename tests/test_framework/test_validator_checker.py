import pytest
from src.validators.checker import DataValidator
from src.validators.report import ValidationReport, RuleResult

class TestDataValidator:
    """Test DataValidator and report generation"""
    
    def test_stock_master_normal(self):
        """正常的 stock_master 資料"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"},
        ]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        assert len(report.failed_rules) == 0, f"Should pass but failed: {report.failed_rules}"
        assert len(report.passed_rules) > 0

    def test_stock_master_missing_field(self):
        """缺少必要欄位的 stock_master 應失敗"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE"}  # 缺 industry
        ]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        assert len(report.failed_rules) > 0

    def test_stock_daily_zero_price_fail(self):
        """0 元資料應失敗"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 0, "volume": 1000},
        ]
        validator = DataValidator("stock_daily", records)
        report = validator.run()
        
        assert len(report.failed_rules) > 0
        assert any(r.rule_id == "stock_daily_value_price_positive" for r in report.failed_rules)

    def test_stock_daily_with_expected_dates_skip(self):
        """未提供 expected_dates 時應 skip completeness 檢查"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 100, "volume": 1000},
        ]
        validator = DataValidator("stock_daily", records)
        report = validator.run()
        
        # 應該有 skipped rule
        completeness_skipped = [r for r in report.skipped_rules if "completeness" in r.rule_id]
        assert len(completeness_skipped) > 0

    def test_stock_daily_with_expected_dates_provided(self):
        """提供 expected_dates，檢查 completeness"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 100, "volume": 1000},
            {"symbol": "2330", "date": "2026-04-02", "close_price": 101, "volume": 1100},
        ]
        expected_dates = ["2026-04-01", "2026-04-02"]
        validator = DataValidator("stock_daily", records, expected_dates=expected_dates)
        report = validator.run()
        
        # 應該有通過的 completeness rule
        completeness_passed = [r for r in report.passed_rules if "completeness" in r.rule_id]
        assert len(completeness_passed) > 0

    def test_stock_daily_inconsistent_symbols(self):
        """symbol 不在 expected_symbols 中應失敗"""
        records = [
            {"symbol": "9999", "date": "2026-04-01", "close_price": 100, "volume": 1000},
        ]
        expected_symbols = ["2330", "2454"]
        validator = DataValidator("stock_daily", records, expected_symbols=expected_symbols)
        report = validator.run()
        
        # 應該有失敗的 consistency rule
        consistency_failed = [r for r in report.failed_rules if "consistency" in r.rule_id]
        assert len(consistency_failed) > 0

    def test_cb_master_normal(self):
        """正常的 cb_master 資料"""
        records = [
            {"cb_code": "2330A", "cb_name": "台積電轉債", "conversion_price": 50.0},
            {"cb_code": "2454A", "cb_name": "聯發科轉債", "conversion_price": 45.0},
        ]
        validator = DataValidator("cb_master", records)
        report = validator.run()
        
        assert len(report.failed_rules) == 0

    def test_tpex_cb_daily_normal(self):
        """正常的 tpex_cb_daily 資料"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01", "closing_price": 50.5},
            {"cb_code": "2330A", "trade_date": "2026-04-02", "closing_price": 51.0},
        ]
        validator = DataValidator("tpex_cb_daily", records)
        report = validator.run()
        
        assert len(report.failed_rules) == 0

    def test_tpex_cb_daily_no_records_warning(self):
        """無交易紀錄應 warning（不是 error）"""
        records = []
        validator = DataValidator("tpex_cb_daily", records)
        report = validator.run()
        
        # 應該有 warning
        assert len(report.warning_rules) > 0

    def test_invalid_table_name(self):
        """無效的 table_name 應 raise"""
        records = []
        with pytest.raises(ValueError):
            DataValidator("invalid_table", records)

    def test_report_summary(self):
        """Report 摘要應正確"""
        records = [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        summary = report.summary
        assert summary["total_rules"] > 0
        assert summary["passed"] + summary["failed"] + summary["warnings"] + summary["skipped"] == summary["total_rules"]

    def test_report_to_dict(self):
        """Report 可序列化為 dict（便於 JSON）"""
        records = [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        report_dict = report.to_dict()
        assert isinstance(report_dict, dict)
        assert "table_name" in report_dict
        assert "summary" in report_dict
        assert "timestamp" in report_dict
        assert report_dict["table_name"] == "stock_master"

    def test_report_has_errors(self):
        """has_errors() 應正確判斷"""
        # 正常資料
        records_pass = [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}]
        validator = DataValidator("stock_master", records_pass)
        report = validator.run()
        assert not report.has_errors()
        
        # 異常資料
        records_fail = [{"symbol": "2330", "name": "TSMC"}]  # 缺 market_type
        validator = DataValidator("stock_master", records_fail)
        report = validator.run()
        assert report.has_errors()

    def test_rule_result_to_dict(self):
        """RuleResult 可序列化"""
        result = RuleResult(
            rule_id="test_rule",
            status="PASS",
            detail="Test passed",
            count=10
        )
        result_dict = result.to_dict()
        assert result_dict["rule_id"] == "test_rule"
        assert result_dict["status"] == "PASS"

    def test_warning_rules_dont_fail(self):
        """WARNING 規則失敗時應放到 warning_rules，不是 failed_rules"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}
        ]
        # 只有 1 個 TWSE record，應觸發 warning
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        # 應該有 warning，不應該有 failed
        assert len(report.warning_rules) > 0
        # 結構性檢查應該 failed（因為 TWSE 數量不足是 WARNING）
        # 但是結構性檢查應該 pass
        assert len(report.failed_rules) == 0

    def test_multiple_tables_validation(self):
        """測試多個 table 的驗證"""
        stock_master_records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
        ]
        stock_daily_records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 100, "volume": 1000},
        ]
        
        validator_master = DataValidator("stock_master", stock_master_records)
        report_master = validator_master.run()
        assert isinstance(report_master, ValidationReport)
        
        validator_daily = DataValidator("stock_daily", stock_daily_records)
        report_daily = validator_daily.run()
        assert isinstance(report_daily, ValidationReport)

    def test_large_dataset(self):
        """測試大量資料的驗證"""
        # 創建 1000 筆記錄
        records = [
            {"symbol": f"SYM{i:04d}", "name": f"Company{i}", "market_type": "TWSE", "industry": "技術"}
            for i in range(1000)
        ]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        assert report.total_checked == 1000
        assert len(report.passed_rules) > 0

    def test_cb_code_consistency_skip_when_not_provided(self):
        """未提供 expected_cb_codes 時應 skip cb_code consistency 檢查"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01", "closing_price": 50.5}
        ]
        validator = DataValidator("tpex_cb_daily", records)
        report = validator.run()
        
        # 應該有 skipped consistency rule
        consistency_skipped = [r for r in report.skipped_rules if "consistency" in r.rule_id]
        assert len(consistency_skipped) > 0

    def test_cb_code_consistency_provided(self):
        """提供 expected_cb_codes 時應進行檢查"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01", "closing_price": 50.5}
        ]
        expected_cb_codes = ["2330A", "2454A"]
        validator = DataValidator("tpex_cb_daily", records, expected_cb_codes=expected_cb_codes)
        report = validator.run()
        
        # 應該有通過的 consistency rule
        consistency_passed = [r for r in report.passed_rules if "consistency" in r.rule_id]
        assert len(consistency_passed) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
