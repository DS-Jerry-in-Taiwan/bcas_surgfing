from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RuleSeverity(Enum):
    """規則嚴重度等級"""
    ERROR = "error"      # 阻斷流程
    WARNING = "warning"  # 僅記錄，繼續

@dataclass
class ValidationRule:
    """檢查規則定義"""
    rule_id: str                                    # 唯一識別符
    table_name: str                                 # 適用表名
    description: str                                # 檢查邏輯敘述
    severity: RuleSeverity                         # error or warning
    checker_fn: Callable[[List[Dict], Any], Tuple[bool, str]]  # 檢查函數
    example_pass: Optional[str] = None             # 通過範例
    example_fail: Optional[str] = None             # 失敗範例
    
    def __post_init__(self):
        """驗證規則定義"""
        if not self.rule_id:
            raise ValueError("rule_id cannot be empty")
        if not self.table_name:
            raise ValueError("table_name cannot be empty")
        if self.severity not in RuleSeverity:
            raise ValueError(f"Invalid severity: {self.severity}")

# 工具函數

def create_rule(
    rule_id: str,
    table_name: str,
    description: str,
    severity: RuleSeverity,
    checker_fn: Callable,
    example_pass: str = None,
    example_fail: str = None,
) -> ValidationRule:
    """工廠函數：建立 rule"""
    return ValidationRule(
        rule_id=rule_id,
        table_name=table_name,
        description=description,
        severity=severity,
        checker_fn=checker_fn,
        example_pass=example_pass,
        example_fail=example_fail,
    )

def is_error_rule(rule: ValidationRule) -> bool:
    """判斷是否為 ERROR 等級"""
    return rule.severity == RuleSeverity.ERROR

def is_warning_rule(rule: ValidationRule) -> bool:
    """判斷是否為 WARNING 等級"""
    return rule.severity == RuleSeverity.WARNING
