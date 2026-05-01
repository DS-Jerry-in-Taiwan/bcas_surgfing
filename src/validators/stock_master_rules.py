from typing import List, Dict, Tuple, Optional
from .rules import ValidationRule, RuleSeverity, create_rule

def check_structure_required_fields(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查必要欄位"""
    required = ['symbol', 'name', 'market_type', 'industry']
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

def check_uniqueness_symbol(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 symbol 唯一性"""
    if not records:
        return False, "No records provided"
    
    symbols = [r.get('symbol') for r in records if r.get('symbol')]
    unique_count = len(set(symbols))
    total_count = len(records)
    
    if unique_count != total_count:
        duplicates = [s for s in symbols if symbols.count(s) > 1]
        return False, f"Duplicate symbols found: {set(duplicates)}"
    return True, f"All {unique_count} symbols unique"

def check_value_market_type(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 market_type 值"""
    if not records:
        return False, "No records provided"
    
    valid_types = {'TWSE', 'TPEx'}
    invalid = []
    for r in records:
        mt = r.get('market_type')
        if mt and mt not in valid_types:
            invalid.append((r.get('symbol'), mt))
    
    if invalid:
        return False, f"Invalid market_type: {invalid}"
    return True, "All market_type values valid"

def check_completeness_twse_coverage(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 TWSE 覆蓋度"""
    twse_count = sum(1 for r in records if r.get('market_type') == 'TWSE')
    threshold = 1500
    if twse_count < threshold:
        return False, f"TWSE coverage too low: {twse_count} < {threshold}"
    return True, f"TWSE coverage OK: {twse_count} records"

def check_completeness_tpex_coverage(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 TPEx 覆蓋度"""
    tpex_count = sum(1 for r in records if r.get('market_type') == 'TPEx')
    threshold = 800
    if tpex_count < threshold:
        return False, f"TPEx coverage too low: {tpex_count} < {threshold}"
    return True, f"TPEx coverage OK: {tpex_count} records"

def check_value_industry_not_empty(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 industry 欄位應非空"""
    if not records:
        return False, "No records provided"
    
    empty_count = sum(1 for r in records if not r.get('industry') or r.get('industry') == "")
    empty_rate = empty_count / len(records) if records else 0
    
    threshold = 0.05  # 5%
    if empty_rate > threshold:
        return False, f"Industry empty rate too high: {empty_rate:.1%} > {threshold:.1%}"
    return True, f"Industry coverage OK: {empty_rate:.1%} empty"

# 規則清單
STOCK_MASTER_RULES = [
    create_rule(
        rule_id="stock_master_structure_required_fields",
        table_name="stock_master",
        description="Check all required fields are present (symbol, name, market_type, industry)",
        severity=RuleSeverity.ERROR,
        checker_fn=check_structure_required_fields,
        example_pass="Records contain: symbol, name, market_type, industry",
        example_fail="Records missing: industry",
    ),
    create_rule(
        rule_id="stock_master_uniqueness_symbol",
        table_name="stock_master",
        description="Symbol values should be unique",
        severity=RuleSeverity.ERROR,
        checker_fn=check_uniqueness_symbol,
        example_pass="1000 unique symbols, 1000 records",
        example_fail="1000 unique symbols, 1001 records (duplicate)",
    ),
    create_rule(
        rule_id="stock_master_value_market_type",
        table_name="stock_master",
        description="market_type must be TWSE or TPEx",
        severity=RuleSeverity.ERROR,
        checker_fn=check_value_market_type,
        example_pass="All market_type in {TWSE, TPEx}",
        example_fail="market_type = NYSE",
    ),
    create_rule(
        rule_id="stock_master_completeness_twse_coverage",
        table_name="stock_master",
        description="TWSE records should be >= 1500",
        severity=RuleSeverity.WARNING,
        checker_fn=check_completeness_twse_coverage,
        example_pass="1800 TWSE records",
        example_fail="500 TWSE records",
    ),
    create_rule(
        rule_id="stock_master_completeness_tpex_coverage",
        table_name="stock_master",
        description="TPEx records should be >= 800",
        severity=RuleSeverity.WARNING,
        checker_fn=check_completeness_tpex_coverage,
        example_pass="1000 TPEx records",
        example_fail="200 TPEx records",
    ),
    create_rule(
        rule_id="stock_master_value_industry_not_empty",
        table_name="stock_master",
        description="industry field should not be empty for > 95% of records",
        severity=RuleSeverity.WARNING,
        checker_fn=check_value_industry_not_empty,
        example_pass="< 5% industry empty",
        example_fail="> 5% industry empty",
    ),
]
