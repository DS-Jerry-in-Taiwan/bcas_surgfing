from typing import List, Dict, Tuple, Optional
import re
from .rules import ValidationRule, RuleSeverity, create_rule

def check_structure_required_fields(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查必要欄位"""
    required = ['symbol', 'date', 'close_price', 'volume']
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
    """檢查 close_price > 0 (handles string/numeric values)"""
    if not records:
        return False, "No records provided"
    
    invalid = []
    for i, r in enumerate(records):
        raw = r.get('close_price')
        if raw is not None:
            try:
                price = float(raw)
                if price <= 0:
                    invalid.append((i, r.get('symbol'), price))
            except (ValueError, TypeError):
                invalid.append((i, r.get('symbol'), raw))
    
    if invalid:
        return False, f"Found {len(invalid)} records with close_price <= 0: {invalid[:5]}"
    return True, f"All {len(records)} records have positive close_price"

def check_value_volume_non_negative(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 volume >= 0"""
    if not records:
        return False, "No records provided"
    
    invalid = []
    for i, r in enumerate(records):
        vol = r.get('volume')
        if vol is not None and vol < 0:
            invalid.append((i, r.get('symbol'), vol))
    
    if invalid:
        return False, f"Found {len(invalid)} records with volume < 0: {invalid[:5]}"
    return True, f"All {len(records)} records have non-negative volume"

def check_completeness_row_count(records: List[Dict], expected_dates: Optional[List[str]] = None, **kwargs) -> Tuple[bool, str]:
    """檢查行數是否等於 expected_dates × unique_symbols"""
    if expected_dates is None:
        return (None, "expected_dates not provided, skipping completeness check")
    
    if not records:
        return False, "No records provided"
    
    unique_symbols = len(set(r.get('symbol') for r in records if r.get('symbol')))
    expected_rows = len(expected_dates) * unique_symbols
    actual_rows = len(records)
    
    if actual_rows != expected_rows:
        return False, f"Row count mismatch: expected {expected_rows} ({len(expected_dates)} dates × {unique_symbols} symbols), got {actual_rows}"
    return True, f"Row count correct: {actual_rows} rows"

def check_consistency_symbol_in_master(records: List[Dict], expected_symbols: Optional[List[str]] = None, **kwargs) -> Tuple[bool, str]:
    """檢查所有 symbol 都在 expected_symbols 中"""
    if expected_symbols is None:
        return (None, "expected_symbols not provided, skipping consistency check")
    
    if not records:
        return False, "No records provided"
    
    actual_symbols = set(r.get('symbol') for r in records if r.get('symbol'))
    expected_symbols_set = set(expected_symbols)
    
    missing_symbols = actual_symbols - expected_symbols_set
    if missing_symbols:
        return False, f"Found symbols not in master: {missing_symbols}"
    
    return True, f"All {len(actual_symbols)} symbols exist in master"

def check_format_date(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 date 格式為 YYYY-MM-DD"""
    if not records:
        return False, "No records provided"
    
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    invalid = []
    
    for i, r in enumerate(records):
        date_val = r.get('date')
        if date_val and not re.match(date_pattern, str(date_val)):
            invalid.append((i, r.get('symbol'), date_val))
    
    if invalid:
        return False, f"Found {len(invalid)} records with invalid date format: {invalid[:5]}"
    return True, f"All {len(records)} dates in YYYY-MM-DD format"

def check_value_price_range_warning(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查單日漲跌幅 > 10% 的記錄"""
    if not records:
        return False, "No records provided"
    
    high_change_records = []
    
    for i, r in enumerate(records):
        open_price = r.get('open_price')
        close_price = r.get('close_price')
        price_change = r.get('price_change')
        
        # 優先使用 price_change 欄位，否則計算
        if price_change is not None:
            pct_change = price_change
        elif open_price and close_price:
            pct_change = ((close_price - open_price) / open_price) * 100
        else:
            continue
        
        if abs(pct_change) > 10:
            high_change_records.append((i, r.get('symbol'), pct_change))
    
    if high_change_records:
        return False, f"Found {len(high_change_records)} records with price change > 10%: {high_change_records[:5]}"
    return True, f"No records with price change > 10%"

# 規則清單
STOCK_DAILY_RULES = [
    create_rule(
        rule_id="stock_daily_structure_required_fields",
        table_name="stock_daily",
        description="Check all required fields are present (symbol, date, close_price, volume)",
        severity=RuleSeverity.ERROR,
        checker_fn=check_structure_required_fields,
        example_pass="Records contain: symbol, date, close_price, volume",
        example_fail="Records missing: volume",
    ),
    create_rule(
        rule_id="stock_daily_value_price_positive",
        table_name="stock_daily",
        description="close_price must be > 0",
        severity=RuleSeverity.ERROR,
        checker_fn=check_value_price_positive,
        example_pass="All close_price > 0",
        example_fail="close_price = 0",
    ),
    create_rule(
        rule_id="stock_daily_value_volume_non_negative",
        table_name="stock_daily",
        description="volume must be >= 0",
        severity=RuleSeverity.ERROR,
        checker_fn=check_value_volume_non_negative,
        example_pass="All volume >= 0",
        example_fail="volume = -100",
    ),
    create_rule(
        rule_id="stock_daily_completeness_row_count",
        table_name="stock_daily",
        description="Row count should equal expected_dates × unique_symbols",
        severity=RuleSeverity.ERROR,
        checker_fn=check_completeness_row_count,
        example_pass="21 trading days × 3 symbols = 63 rows",
        example_fail="60 rows (missing 3 rows)",
    ),
    create_rule(
        rule_id="stock_daily_consistency_symbol_in_master",
        table_name="stock_daily",
        description="All symbols must exist in stock_master",
        severity=RuleSeverity.ERROR,
        checker_fn=check_consistency_symbol_in_master,
        example_pass="All symbols from stock_daily exist in master",
        example_fail="Symbol 9999 not in master",
    ),
    create_rule(
        rule_id="stock_daily_format_date",
        table_name="stock_daily",
        description="date must be in YYYY-MM-DD format",
        severity=RuleSeverity.ERROR,
        checker_fn=check_format_date,
        example_pass="2026-04-01",
        example_fail="2026/04/01",
    ),
    create_rule(
        rule_id="stock_daily_value_price_range_warning",
        table_name="stock_daily",
        description="Single day price change > 10% should be flagged (warning only)",
        severity=RuleSeverity.WARNING,
        checker_fn=check_value_price_range_warning,
        example_pass="No records with change > 10%",
        example_fail="5 records with change > 10%",
    ),
]
