from typing import List, Dict, Optional
import logging

from .rules import ValidationRule, RuleSeverity
from .report import ValidationReport, RuleResult
from . import stock_master_rules, stock_daily_rules, cb_master_rules, tpex_cb_daily_rules

logger = logging.getLogger(__name__)

class DataValidator:
    """原始資料驗證器"""
    
    def __init__(
        self,
        table_name: str,
        records: List[Dict],
        expected_dates: Optional[List[str]] = None,
        expected_symbols: Optional[List[str]] = None,
        expected_cb_codes: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Args:
            table_name: 四種之一 (stock_master, stock_daily, cb_master, tpex_cb_daily)
            records: raw records list (list of dict)
            expected_dates: 交易日期清單（用於 completeness 檢查）
            expected_symbols: 預期 symbol 清單（用於 consistency 檢查）
            expected_cb_codes: 預期 cb_code 清單（用於 consistency 檢查）
            **kwargs: 其他自訂參數
        """
        self.table_name = table_name
        self.records = records
        self.expected_dates = expected_dates
        self.expected_symbols = expected_symbols
        self.expected_cb_codes = expected_cb_codes
        self.custom_kwargs = kwargs
        self.rules = self._load_rules()
        
        logger.debug(
            f"Initialized DataValidator: table={table_name}, "
            f"records={len(records)}, rules={len(self.rules)}"
        )
    
    def _load_rules(self) -> List[ValidationRule]:
        """根據 table_name 載入對應的 rules"""
        rules_map = {
            "stock_master": stock_master_rules.STOCK_MASTER_RULES,
            "stock_daily": stock_daily_rules.STOCK_DAILY_RULES,
            "cb_master": cb_master_rules.CB_MASTER_RULES,
            "tpex_cb_daily": tpex_cb_daily_rules.TPEX_CB_DAILY_RULES,
        }
        
        if self.table_name not in rules_map:
            logger.warning(f"No rules defined for table: {self.table_name}, skipping all rules")
            return []
        
        return rules_map[self.table_name]
    
    def run(self) -> ValidationReport:
        """執行所有 rules，回傳 report"""
        logger.debug(f"Starting validation for {self.table_name}")
        
        report = ValidationReport(
            table_name=self.table_name,
            total_checked=len(self.records),
        )
        
        for rule in self.rules:
            try:
                result = self._execute_rule(rule)
                
                if result.status == "PASS":
                    report.passed_rules.append(result)
                    logger.debug(f"  ✓ {rule.rule_id} PASSED")
                elif result.status == "FAIL":
                    report.failed_rules.append(result)
                    logger.debug(f"  ✗ {rule.rule_id} FAILED: {result.detail}")
                elif result.status == "WARNING":
                    report.warning_rules.append(result)
                    logger.debug(f"  ⚠ {rule.rule_id} WARNING: {result.detail}")
                else:  # SKIPPED
                    report.skipped_rules.append(result)
                    logger.debug(f"  ○ {rule.rule_id} SKIPPED: {result.detail}")
                    
            except Exception as e:
                logger.error(f"  ✗ {rule.rule_id} EXECUTION ERROR: {str(e)}")
                report.failed_rules.append(
                    RuleResult(
                        rule_id=rule.rule_id,
                        status="FAIL",
                        detail=f"Execution error: {str(e)}",
                        count=0,
                    )
                )
        
        logger.debug(f"Validation complete: {report}")
        return report
    
    def _execute_rule(self, rule: ValidationRule) -> RuleResult:
        """執行單一 rule"""
        # 準備 kwargs
        kwargs = {}
        if "expected_dates" in rule.checker_fn.__code__.co_varnames:
            kwargs["expected_dates"] = self.expected_dates
        if "expected_symbols" in rule.checker_fn.__code__.co_varnames:
            kwargs["expected_symbols"] = self.expected_symbols
        if "expected_cb_codes" in rule.checker_fn.__code__.co_varnames:
            kwargs["expected_cb_codes"] = self.expected_cb_codes
        
        # 合併自訂參數
        kwargs.update(self.custom_kwargs)
        
        # 執行 checker
        try:
            result = rule.checker_fn(self.records, **kwargs)
            
            # 若回傳 None（skip）
            if result[0] is None:
                return RuleResult(
                    rule_id=rule.rule_id,
                    status="SKIPPED",
                    detail=result[1],
                    count=0,
                )
            
            # 正常結果
            passed = result[0]
            detail = result[1]
            
            # 根據 severity 判斷 PASS/FAIL/WARNING
            if passed:
                status = "PASS"
            elif rule.severity == RuleSeverity.WARNING:
                status = "WARNING"
            else:
                status = "FAIL"
            
            return RuleResult(
                rule_id=rule.rule_id,
                status=status,
                detail=detail,
                count=len(self.records) if passed else 0,
            )
            
        except TypeError as e:
            # 參數不符
            if "unexpected keyword argument" in str(e):
                return RuleResult(
                    rule_id=rule.rule_id,
                    status="SKIPPED",
                    detail=f"Parameter not available: {str(e)}",
                    count=0,
                )
            raise
