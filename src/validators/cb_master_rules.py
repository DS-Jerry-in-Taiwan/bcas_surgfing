from typing import List, Dict, Tuple, Optional
from .rules import ValidationRule, RuleSeverity, create_rule

def check_structure_required_fields(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查必要欄位"""
    required = ['cb_code', 'cb_name', 'conversion_price']
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

def check_uniqueness_cb_code(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 cb_code 唯一性"""
    if not records:
        return False, "No records provided"
    
    cb_codes = [r.get('cb_code') for r in records if r.get('cb_code')]
    unique_count = len(set(cb_codes))
    total_count = len(records)
    
    if unique_count != total_count:
        duplicates = [s for s in cb_codes if cb_codes.count(s) > 1]
        return False, f"Duplicate cb_codes found: {set(duplicates)}"
    return True, f"All {unique_count} cb_codes unique"

def check_value_conversion_price_positive(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 conversion_price > 0 (handles string values from CSV)"""
    if not records:
        return False, "No records provided"
    
    invalid = []
    for i, r in enumerate(records):
        raw = r.get('conversion_price')
        if raw is not None:
            try:
                price = float(raw)
                if price <= 0:
                    invalid.append((i, r.get('cb_code'), raw))
            except (ValueError, TypeError):
                invalid.append((i, r.get('cb_code'), raw))
    
    if invalid:
        return False, f"Found {len(invalid)} records with conversion_price <= 0: {invalid[:5]}"
    return True, f"All {len(records)} records have positive conversion_price"

def check_completeness_min_rows(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查至少有 10 rows"""
    if not records:
        return False, "No records provided"
    
    row_count = len(records)
    threshold = 10
    
    if row_count < threshold:
        return False, f"Too few records: {row_count} < {threshold}"
    return True, f"Record count OK: {row_count} records"

def check_value_cb_name_not_empty(records: List[Dict], **kwargs) -> Tuple[bool, str]:
    """檢查 cb_name 應非空"""
    if not records:
        return False, "No records provided"
    
    empty_count = sum(1 for r in records if not r.get('cb_name') or r.get('cb_name') == "")
    
    if empty_count > 0:
        return False, f"Found {empty_count} records with empty cb_name"
    return True, f"All {len(records)} records have non-empty cb_name"

# 規則清單
CB_MASTER_RULES = [
    create_rule(
        rule_id="cb_master_structure_required_fields",
        table_name="cb_master",
        description="Check all required fields are present (cb_code, cb_name, conversion_price)",
        severity=RuleSeverity.ERROR,
        checker_fn=check_structure_required_fields,
        example_pass="Records contain: cb_code, cb_name, conversion_price",
        example_fail="Records missing: conversion_price",
    ),
    create_rule(
        rule_id="cb_master_uniqueness_cb_code",
        table_name="cb_master",
        description="cb_code values should be unique",
        severity=RuleSeverity.ERROR,
        checker_fn=check_uniqueness_cb_code,
        example_pass="100 unique cb_codes, 100 records",
        example_fail="100 unique cb_codes, 101 records (duplicate)",
    ),
    create_rule(
        rule_id="cb_master_value_conversion_price_positive",
        table_name="cb_master",
        description="conversion_price must be > 0",
        severity=RuleSeverity.ERROR,
        checker_fn=check_value_conversion_price_positive,
        example_pass="All conversion_price > 0",
        example_fail="conversion_price = 0",
    ),
    create_rule(
        rule_id="cb_master_completeness_min_rows",
        table_name="cb_master",
        description="Should have at least 10 records",
        severity=RuleSeverity.WARNING,
        checker_fn=check_completeness_min_rows,
        example_pass="150 rows",
        example_fail="5 rows",
    ),
    create_rule(
        rule_id="cb_master_value_cb_name_not_empty",
        table_name="cb_master",
        description="cb_name should not be empty",
        severity=RuleSeverity.WARNING,
        checker_fn=check_value_cb_name_not_empty,
        example_pass="All cb_name non-empty",
        example_fail="Some cb_name empty",
    ),
]
