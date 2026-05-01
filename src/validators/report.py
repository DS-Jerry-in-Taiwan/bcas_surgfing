from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from datetime import datetime
import json

@dataclass
class RuleResult:
    """單一規則的檢查結果"""
    rule_id: str
    status: str              # "PASS" | "FAIL" | "WARNING" | "SKIPPED"
    detail: str              # 詳細信息
    count: int               # 受影響的 row 數或統計量
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class ValidationReport:
    """完整的驗證報告"""
    table_name: str
    total_checked: int
    passed_rules: List[RuleResult] = field(default_factory=list)
    failed_rules: List[RuleResult] = field(default_factory=list)
    warning_rules: List[RuleResult] = field(default_factory=list)
    skipped_rules: List[RuleResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def summary(self) -> Dict[str, int]:
        """統計摘要"""
        return {
            "total_rules": (
                len(self.passed_rules) + len(self.failed_rules) + 
                len(self.warning_rules) + len(self.skipped_rules)
            ),
            "passed": len(self.passed_rules),
            "failed": len(self.failed_rules),
            "warnings": len(self.warning_rules),
            "skipped": len(self.skipped_rules),
            "total_checked": self.total_checked,
        }
    
    def has_errors(self) -> bool:
        """是否有失敗的規則"""
        return len(self.failed_rules) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（便於 JSON 序列化）"""
        return {
            "table_name": self.table_name,
            "total_checked": self.total_checked,
            "passed_rules": [r.to_dict() for r in self.passed_rules],
            "failed_rules": [r.to_dict() for r in self.failed_rules],
            "warning_rules": [r.to_dict() for r in self.warning_rules],
            "skipped_rules": [r.to_dict() for r in self.skipped_rules],
            "timestamp": self.timestamp,
            "summary": self.summary,
        }
    
    def __str__(self) -> str:
        """用於日誌打印"""
        s = f"ValidationReport({self.table_name}): "
        s += f"passed={len(self.passed_rules)} "
        s += f"failed={len(self.failed_rules)} "
        s += f"warnings={len(self.warning_rules)}"
        return s
