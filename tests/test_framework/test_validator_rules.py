import pytest
from src.validators.rules import ValidationRule, RuleSeverity
from src.validators import stock_master_rules, stock_daily_rules, cb_master_rules, tpex_cb_daily_rules


class TestStockMasterRules:
    """Test stock_master rules"""
    
    def test_structure_required_fields_pass(self):
        """正常資料應 PASS"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
            {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"}
        ]
        passed, msg = stock_master_rules.check_structure_required_fields(records)
        assert passed, msg

    def test_structure_required_fields_fail_missing_field(self):
        """缺少必要欄位應 FAIL"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE"}  # 缺 industry
        ]
        passed, msg = stock_master_rules.check_structure_required_fields(records)
        assert not passed
        assert "industry" in msg

    def test_uniqueness_symbol_pass(self):
        """symbol 不重複應 PASS"""
        records = [
            {"symbol": "2330"},
            {"symbol": "2454"},
        ]
        passed, msg = stock_master_rules.check_uniqueness_symbol(records)
        assert passed, msg

    def test_uniqueness_symbol_fail(self):
        """symbol 重複應 FAIL"""
        records = [
            {"symbol": "2330"},
            {"symbol": "2330"},
        ]
        passed, msg = stock_master_rules.check_uniqueness_symbol(records)
        assert not passed
        assert "2330" in msg

    def test_value_market_type_pass(self):
        """有效的 market_type 應 PASS"""
        records = [
            {"symbol": "2330", "market_type": "TWSE"},
            {"symbol": "0050", "market_type": "TPEx"},
        ]
        passed, msg = stock_master_rules.check_value_market_type(records)
        assert passed, msg

    def test_value_market_type_fail(self):
        """無效的 market_type 應 FAIL"""
        records = [
            {"symbol": "2330", "market_type": "NYSE"}
        ]
        passed, msg = stock_master_rules.check_value_market_type(records)
        assert not passed
        assert "NYSE" in msg


class TestStockDailyRules:
    """Test stock_daily rules"""
    
    def test_structure_required_fields_pass(self):
        """正常資料應 PASS"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 850.5, "volume": 10000}
        ]
        passed, msg = stock_daily_rules.check_structure_required_fields(records)
        assert passed, msg

    def test_structure_required_fields_fail(self):
        """缺少必要欄位應 FAIL"""
        records = [
            {"symbol": "2330", "date": "2026-04-01"}  # 缺 close_price, volume
        ]
        passed, msg = stock_daily_rules.check_structure_required_fields(records)
        assert not passed

    def test_value_price_positive_pass(self):
        """正價格應 PASS"""
        records = [
            {"symbol": "2330", "close_price": 100.0},
            {"symbol": "2454", "close_price": 50.5},
        ]
        passed, msg = stock_daily_rules.check_value_price_positive(records)
        assert passed, msg

    def test_value_price_positive_fail_zero(self):
        """0 元應 FAIL"""
        records = [
            {"symbol": "2330", "close_price": 0}
        ]
        passed, msg = stock_daily_rules.check_value_price_positive(records)
        assert not passed
        assert "0" in msg

    def test_value_price_positive_fail_negative(self):
        """負價格應 FAIL"""
        records = [
            {"symbol": "2330", "close_price": -10.5}
        ]
        passed, msg = stock_daily_rules.check_value_price_positive(records)
        assert not passed

    def test_value_volume_non_negative_pass(self):
        """非負成交量應 PASS"""
        records = [
            {"symbol": "2330", "volume": 1000},
            {"symbol": "2330", "volume": 0},  # 0 是允許的
        ]
        passed, msg = stock_daily_rules.check_value_volume_non_negative(records)
        assert passed, msg

    def test_value_volume_non_negative_fail(self):
        """負成交量應 FAIL"""
        records = [
            {"symbol": "2330", "volume": -100}
        ]
        passed, msg = stock_daily_rules.check_value_volume_non_negative(records)
        assert not passed
        assert "-100" in msg

    def test_format_date_pass(self):
        """正確格式的日期應 PASS"""
        records = [
            {"symbol": "2330", "date": "2026-04-01"},
            {"symbol": "2330", "date": "2026-12-31"},
        ]
        passed, msg = stock_daily_rules.check_format_date(records)
        assert passed, msg

    def test_format_date_fail_wrong_format(self):
        """錯誤的日期格式應 FAIL"""
        records = [
            {"symbol": "2330", "date": "2026/04/01"}
        ]
        passed, msg = stock_daily_rules.check_format_date(records)
        assert not passed
        assert "2026/04/01" in msg

    def test_completeness_row_count_skip(self):
        """未提供 expected_dates 應 skip"""
        records = [{"symbol": "2330", "date": "2026-04-01"}]
        passed, msg = stock_daily_rules.check_completeness_row_count(records)
        assert passed is None  # skip
        assert "expected_dates not provided" in msg

    def test_consistency_symbol_in_master_skip(self):
        """未提供 expected_symbols 應 skip"""
        records = [{"symbol": "2330"}]
        passed, msg = stock_daily_rules.check_consistency_symbol_in_master(records)
        assert passed is None  # skip
        assert "expected_symbols not provided" in msg

    def test_consistency_symbol_in_master_pass(self):
        """symbol 在 master 中應 PASS"""
        records = [
            {"symbol": "2330"},
            {"symbol": "2454"},
        ]
        expected_symbols = ["2330", "2454", "3008"]
        passed, msg = stock_daily_rules.check_consistency_symbol_in_master(records, expected_symbols=expected_symbols)
        assert passed, msg

    def test_consistency_symbol_in_master_fail(self):
        """symbol 不在 master 中應 FAIL"""
        records = [
            {"symbol": "9999"},
        ]
        expected_symbols = ["2330", "2454"]
        passed, msg = stock_daily_rules.check_consistency_symbol_in_master(records, expected_symbols=expected_symbols)
        assert not passed
        assert "9999" in msg


class TestCbMasterRules:
    """Test cb_master rules"""
    
    def test_structure_required_fields_pass(self):
        """正常資料應 PASS"""
        records = [
            {"cb_code": "2330A", "cb_name": "台積電轉債", "conversion_price": 50.0}
        ]
        passed, msg = cb_master_rules.check_structure_required_fields(records)
        assert passed, msg

    def test_structure_required_fields_fail(self):
        """缺少必要欄位應 FAIL"""
        records = [
            {"cb_code": "2330A", "cb_name": "台積電轉債"}  # 缺 conversion_price
        ]
        passed, msg = cb_master_rules.check_structure_required_fields(records)
        assert not passed

    def test_uniqueness_cb_code_pass(self):
        """cb_code 不重複應 PASS"""
        records = [
            {"cb_code": "2330A"},
            {"cb_code": "2454A"},
        ]
        passed, msg = cb_master_rules.check_uniqueness_cb_code(records)
        assert passed, msg

    def test_uniqueness_cb_code_fail(self):
        """cb_code 重複應 FAIL"""
        records = [
            {"cb_code": "2330A"},
            {"cb_code": "2330A"},
        ]
        passed, msg = cb_master_rules.check_uniqueness_cb_code(records)
        assert not passed

    def test_value_conversion_price_positive_pass(self):
        """正轉換價應 PASS"""
        records = [
            {"cb_code": "2330A", "conversion_price": 50.0},
        ]
        passed, msg = cb_master_rules.check_value_conversion_price_positive(records)
        assert passed, msg

    def test_value_conversion_price_positive_fail(self):
        """0 或負轉換價應 FAIL"""
        records = [
            {"cb_code": "2330A", "conversion_price": 0}
        ]
        passed, msg = cb_master_rules.check_value_conversion_price_positive(records)
        assert not passed

    def test_completeness_min_rows_pass(self):
        """足夠筆數應 PASS"""
        records = [{"cb_code": f"CB{i}"} for i in range(15)]
        passed, msg = cb_master_rules.check_completeness_min_rows(records)
        assert passed, msg

    def test_completeness_min_rows_fail(self):
        """筆數不足應 FAIL"""
        records = [{"cb_code": f"CB{i}"} for i in range(5)]
        passed, msg = cb_master_rules.check_completeness_min_rows(records)
        assert not passed
        assert "5" in msg

    def test_value_cb_name_not_empty_pass(self):
        """所有名稱非空應 PASS"""
        records = [
            {"cb_code": "2330A", "cb_name": "台積電轉債"},
            {"cb_code": "2454A", "cb_name": "聯發科轉債"},
        ]
        passed, msg = cb_master_rules.check_value_cb_name_not_empty(records)
        assert passed, msg

    def test_value_cb_name_not_empty_fail(self):
        """某個名稱為空應 FAIL"""
        records = [
            {"cb_code": "2330A", "cb_name": ""},
        ]
        passed, msg = cb_master_rules.check_value_cb_name_not_empty(records)
        assert not passed


class TestTpexCbDailyRules:
    """Test tpex_cb_daily rules"""
    
    def test_structure_required_fields_pass(self):
        """正常資料應 PASS"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01", "closing_price": 50.5}
        ]
        passed, msg = tpex_cb_daily_rules.check_structure_required_fields(records)
        assert passed, msg

    def test_structure_required_fields_fail(self):
        """缺少必要欄位應 FAIL"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01"}  # 缺 closing_price
        ]
        passed, msg = tpex_cb_daily_rules.check_structure_required_fields(records)
        assert not passed

    def test_value_price_positive_pass(self):
        """正價格應 PASS"""
        records = [
            {"cb_code": "2330A", "closing_price": 50.5}
        ]
        passed, msg = tpex_cb_daily_rules.check_value_price_positive(records)
        assert passed, msg

    def test_value_price_positive_fail(self):
        """0 或負價格應 FAIL"""
        records = [
            {"cb_code": "2330A", "closing_price": 0}
        ]
        passed, msg = tpex_cb_daily_rules.check_value_price_positive(records)
        assert not passed

    def test_value_volume_non_negative_pass(self):
        """非負成交量應 PASS"""
        records = [
            {"cb_code": "2330A", "volume": 1000}
        ]
        passed, msg = tpex_cb_daily_rules.check_value_volume_non_negative(records)
        assert passed, msg

    def test_value_volume_non_negative_fail(self):
        """負成交量應 FAIL"""
        records = [
            {"cb_code": "2330A", "volume": -100}
        ]
        passed, msg = tpex_cb_daily_rules.check_value_volume_non_negative(records)
        assert not passed

    def test_format_date_pass(self):
        """正確格式的日期應 PASS"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026-04-01"}
        ]
        passed, msg = tpex_cb_daily_rules.check_format_date(records)
        assert passed, msg

    def test_format_date_fail(self):
        """錯誤的日期格式應 FAIL"""
        records = [
            {"cb_code": "2330A", "trade_date": "2026/04/01"}
        ]
        passed, msg = tpex_cb_daily_rules.check_format_date(records)
        assert not passed

    def test_consistency_cb_code_in_master_skip(self):
        """未提供 expected_cb_codes 應 skip"""
        records = [{"cb_code": "2330A"}]
        passed, msg = tpex_cb_daily_rules.check_consistency_cb_code_in_master(records)
        assert passed is None  # skip
        assert "expected_cb_codes not provided" in msg

    def test_consistency_cb_code_in_master_pass(self):
        """cb_code 在 master 中應 PASS"""
        records = [{"cb_code": "2330A"}]
        expected_cb_codes = ["2330A", "2454A"]
        passed, msg = tpex_cb_daily_rules.check_consistency_cb_code_in_master(records, expected_cb_codes=expected_cb_codes)
        assert passed, msg

    def test_consistency_cb_code_in_master_fail(self):
        """cb_code 不在 master 中應 FAIL"""
        records = [{"cb_code": "INVALID"}]
        expected_cb_codes = ["2330A", "2454A"]
        passed, msg = tpex_cb_daily_rules.check_consistency_cb_code_in_master(records, expected_cb_codes=expected_cb_codes)
        assert not passed
        assert "INVALID" in msg

    def test_completeness_at_least_one_record_pass(self):
        """有交易紀錄應 PASS"""
        records = [{"cb_code": "2330A"}]
        passed, msg = tpex_cb_daily_rules.check_completeness_at_least_one_record(records)
        assert passed, msg

    def test_completeness_at_least_one_record_fail(self):
        """無交易紀錄應 FAIL"""
        records = []
        passed, msg = tpex_cb_daily_rules.check_completeness_at_least_one_record(records)
        assert not passed


class TestRuleStructure:
    """Test rule structure and metadata"""
    
    def test_all_rules_have_unique_ids(self):
        """所有 rule 應有唯一 ID"""
        all_rules = (
            stock_master_rules.STOCK_MASTER_RULES +
            stock_daily_rules.STOCK_DAILY_RULES +
            cb_master_rules.CB_MASTER_RULES +
            tpex_cb_daily_rules.TPEX_CB_DAILY_RULES
        )
        rule_ids = [r.rule_id for r in all_rules]
        assert len(rule_ids) == len(set(rule_ids)), "Duplicate rule IDs found"

    def test_all_rules_have_descriptions(self):
        """所有 rule 應有描述"""
        all_rules = (
            stock_master_rules.STOCK_MASTER_RULES +
            stock_daily_rules.STOCK_DAILY_RULES +
            cb_master_rules.CB_MASTER_RULES +
            tpex_cb_daily_rules.TPEX_CB_DAILY_RULES
        )
        for rule in all_rules:
            assert rule.description, f"Rule {rule.rule_id} missing description"

    def test_all_rules_have_valid_severity(self):
        """所有 rule 應有有效的 severity"""
        all_rules = (
            stock_master_rules.STOCK_MASTER_RULES +
            stock_daily_rules.STOCK_DAILY_RULES +
            cb_master_rules.CB_MASTER_RULES +
            tpex_cb_daily_rules.TPEX_CB_DAILY_RULES
        )
        for rule in all_rules:
            assert rule.severity in [RuleSeverity.ERROR, RuleSeverity.WARNING]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
