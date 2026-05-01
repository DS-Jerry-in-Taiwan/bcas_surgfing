from typing import List, Dict, Tuple, Optional
import re
from .rules import ValidationRule, RuleSeverity, create_rule

def check_structure_required_fields(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查必要欄位"""
    required = ['cb_code', 'trade_date', 'closing_price']
    if not records:
        return False, "No records provided"
    
    missing_fields = set()
    for field in required:
        if all(field not in r for r in records):
            missing_fields.add(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(sorted(missing_fields))}"
    
    # Check if all records have required fields
    for i, record in enumerate(records):
        for field in required:
            if field not in record:
                return False, f"Record {i} missing field: {field}"
    
    return True, "All required fields present"

def check_value_price_positive(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 closing_price > 0
    
    Note: closing_price = 0 is valid for CBs that did not trade on that day.
    Non-positive prices are treated as WARNING since 0 is common for non-trading days.
    """
    if not records:
        return False, "No records provided"
    
    invalid = []
    for i, r in enumerate(records):
        price = r.get('closing_price')
        if price is not None:
            try:
                p = float(price)
                if p <= 0:
                    invalid.append((i, r.get('cb_code'), price))
            except (ValueError, TypeError):
                invalid.append((i, r.get('cb_code'), price))
    
    if invalid:
        return False, f"Found {len(invalid)} records with closing_price <= 0: {invalid[:5]}"
    return True, f"All {len(records)} records have positive closing_price"

def check_value_volume_non_negative(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 volume >= 0"""
    if not records:
        return False, "No records provided"
    
    invalid = []
    for i, r in enumerate(records):
        vol = r.get('volume')
        if vol is not None and vol < 0:
            invalid.append((i, r.get('cb_code'), vol))
    
    if invalid:
        return False, f"Found {len(invalid)} records with volume < 0: {invalid[:5]}"
    return True, f"All {len(records)} records have non-negative volume"

def check_consistency_cb_code_in_master(records: List[Dict], expected_cb_codes: Optional[List[str]] = None, **kwargs) -> Tuple[bool, str]:
    """檢查所有 cb_code 都在 expected_cb_codes 中"""
    if expected_cb_codes is None:
        return (None, "expected_cb_codes not provided, skipping consistency check")
    
    if not records:
        return False, "No records provided"
    
    actual_cb_codes = set(r.get('cb_code') for r in records if r.get('cb_code'))
    expected_cb_codes_set = set(expected_cb_codes)
    
    missing_cb_codes = actual_cb_codes - expected_cb_codes_set
    if missing_cb_codes:
        return False, f"Found cb_codes not in master: {missing_cb_codes}"
    
    return True, f"All {len(actual_cb_codes)} cb_codes exist in master"

def check_format_date(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 trade_date 格式為 YYYY-MM-DD"""
    if not records:
        return False, "No records provided"
    
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    invalid = []
    
    for i, r in enumerate(records):
        date_val = r.get('trade_date')
        if date_val and not re.match(date_pattern, str(date_val)):
            invalid.append((i, r.get('cb_code'), date_val))
    
    if invalid:
        return False, f"Found {len(invalid)} records with invalid trade_date format: {invalid[:5]}"
    return True, f"All {len(records)} dates in YYYY-MM-DD format"

def check_completeness_at_least_one_record(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查至少有 1 筆交易紀錄"""
    if not records:
        return False, "No trading records found (may be normal if no CB trading on this date)"
    
    row_count = len(records)
    return True, f"Found {row_count} trading records"

# 規則清單
TPEX_CB_DAILY_RULES = [
    create_rule(
        rule_id="tpex_cb_daily_structure_required_fields",
        table_name="tpex_cb_daily",
        description="Check all required fields are present (cb_code, trade_date, closing_price)",
        severity=RuleSeverity.ERROR,
        checker_fn=check_structure_required_fields,
        example_pass="Records contain: cb_code, trade_date, closing_price",
        example_fail="Records missing: closing_price",
    ),
    create_rule(
        rule_id="tpex_cb_daily_value_price_positive",
        table_name="tpex_cb_daily",
        description="closing_price must be > 0 (WARNING: 0 is valid for non-trading days)",
        severity=RuleSeverity.WARNING,
        checker_fn=check_value_price_positive,
        example_pass="All closing_price > 0",
        example_fail="closing_price = 0",
    ),
    create_rule(
        rule_id="tpex_cb_daily_value_volume_non_negative",
        table_name="tpex_cb_daily",
        description="volume must be >= 0",
        severity=RuleSeverity.ERROR,
        checker_fn=check_value_volume_non_negative,
        example_pass="All volume >= 0",
        example_fail="volume = -100",
    ),
    create_rule(
        rule_id="tpex_cb_daily_consistency_cb_code_in_master",
        table_name="tpex_cb_daily",
        description="All cb_codes must exist in cb_master",
        severity=RuleSeverity.ERROR,
        checker_fn=check_consistency_cb_code_in_master,
        example_pass="All cb_codes from tpex_cb_daily exist in master",
        example_fail="cb_code INVALID not in master",
    ),
    create_rule(
        rule_id="tpex_cb_daily_format_date",
        table_name="tpex_cb_daily",
        description="trade_date must be in YYYY-MM-DD format",
        severity=RuleSeverity.ERROR,
        checker_fn=check_format_date,
        example_pass="2026-04-01",
        example_fail="2026/04/01",
    ),
    create_rule(
        rule_id="tpex_cb_daily_completeness_at_least_one_record",
        table_name="tpex_cb_daily",
        description="Should have at least 1 trading record (warning if empty, as some dates may have no CB trading)",
        severity=RuleSeverity.WARNING,
        checker_fn=check_completeness_at_least_one_record,
        example_pass="> 0 records",
        example_fail="0 records",
    ),
]
