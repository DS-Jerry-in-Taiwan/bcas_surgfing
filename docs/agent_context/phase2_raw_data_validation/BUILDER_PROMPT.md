# Phase 2 Raw Data Validation — Builder Prompt

**版本**: 1.0  
**日期**: 2026-04-30  
**對象**: Development Team (Builder/Implementer)  
**模式**: Stage-by-Stage Implementation Guide

---

## 📋 前置條件

### 環境檢查
```bash
# 確認 Python 版本
python --version  # >= 3.8

# 確認 PostgreSQL 運行
docker ps | grep postgres

# 確認專案根目錄
cd /home/ubuntu/projects/bcas_quant

# 查看現有結構
ls -la src/
ls -la tests/
ls -la logs/
```

### 依賴檢查
```bash
# 所需的庫（應已安裝）
python -c "import psycopg2, pandas, requests" && echo "✓ All dependencies ready"
```

---

## 🎯 Stage 1: Validation Rule Definition

### 1.1 建立目錄結構

```bash
# 建立 validators 目錄
mkdir -p src/validators
touch src/validators/__init__.py

# 驗證
ls -la src/validators/
```

### 1.2 實作 `src/validators/rules.py`

**任務**: 定義 `ValidationRule` dataclass 與基礎工具函數

**檔案**: `src/validators/rules.py`

```python
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
```

**測試**:
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "from src.validators.rules import ValidationRule, RuleSeverity; print('✓ rules.py imported successfully')"
```

### 1.3 實作各 Table 的 Rules

**檔案**: `src/validators/stock_master_rules.py`

```python
from typing import List, Dict, Tuple
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
        return False, f"Missing fields: {', '.join(sorted(missing_fields))}"
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
]
```

**類似地建立**:
- `src/validators/stock_daily_rules.py` (7 條 rules)
- `src/validators/cb_master_rules.py` (5 條 rules)
- `src/validators/tpex_cb_daily_rules.py` (6 條 rules)

**參考** `VALIDATION_RULES.md` 中各 table 的 rule 定義。

### 1.4 Stage 1 測試

**檔案**: `tests/test_framework/test_validator_rules.py`

```python
import pytest
from src.validators.rules import ValidationRule, RuleSeverity
from src.validators.stock_master_rules import (
    check_structure_required_fields,
    check_uniqueness_symbol,
    check_value_market_type,
)

class TestStockMasterRules:
    def test_structure_required_fields_pass(self):
        """正常資料應 PASS"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}
        ]
        passed, msg = check_structure_required_fields(records)
        assert passed, msg

    def test_structure_required_fields_fail_missing_industry(self):
        """缺 industry 應 FAIL"""
        records = [
            {"symbol": "2330", "name": "TSMC", "market_type": "TWSE"}
        ]
        passed, msg = check_structure_required_fields(records)
        assert not passed
        assert "industry" in msg

    def test_uniqueness_symbol_pass(self):
        """symbol 不重複應 PASS"""
        records = [
            {"symbol": "2330"},
            {"symbol": "2454"},
        ]
        passed, msg = check_uniqueness_symbol(records)
        assert passed, msg

    def test_uniqueness_symbol_fail(self):
        """symbol 重複應 FAIL"""
        records = [
            {"symbol": "2330"},
            {"symbol": "2330"},
        ]
        passed, msg = check_uniqueness_symbol(records)
        assert not passed
        assert "2330" in msg

    def test_value_market_type_pass(self):
        """有效的 market_type 應 PASS"""
        records = [
            {"symbol": "2330", "market_type": "TWSE"},
            {"symbol": "0050", "market_type": "TPEx"},
        ]
        passed, msg = check_value_market_type(records)
        assert passed, msg

    def test_value_market_type_fail(self):
        """無效的 market_type 應 FAIL"""
        records = [
            {"symbol": "2330", "market_type": "NYSE"}
        ]
        passed, msg = check_value_market_type(records)
        assert not passed
        assert "NYSE" in msg

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**執行測試**:
```bash
cd /home/ubuntu/projects/bcas_quant
pytest tests/test_framework/test_validator_rules.py -v
# 預期：全部 PASS
```

### ✅ Stage 1 驗收

- [ ] `src/validators/rules.py` 實作完成
- [ ] `src/validators/stock_master_rules.py` 實作完成（5 條 rules）
- [ ] `src/validators/stock_daily_rules.py` 實作完成（7 條 rules）
- [ ] `src/validators/cb_master_rules.py` 實作完成（5 條 rules）
- [ ] `src/validators/tpex_cb_daily_rules.py` 實作完成（6 條 rules）
- [ ] `tests/test_framework/test_validator_rules.py` 全部 PASS
- [ ] 每條 rule 都有通過 & 失敗的測試範例

---

## 🎯 Stage 2: Checker 實作

### 2.1 實作 `src/validators/report.py`

**檔案**: `src/validators/report.py`

```python
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
```

### 2.2 實作 `src/validators/checker.py`

**檔案**: `src/validators/checker.py`

```python
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
        **kwargs
    ):
        """
        Args:
            table_name: 四種之一 (stock_master, stock_daily, cb_master, tpex_cb_daily)
            records: raw records list (list of dict)
            expected_dates: 交易日期清單（用於 completeness 檢查）
            expected_symbols: 預期 symbol 清單（用於 consistency 檢查）
            **kwargs: 其他自訂參數
        """
        self.table_name = table_name
        self.records = records
        self.expected_dates = expected_dates
        self.expected_symbols = expected_symbols
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
            raise ValueError(f"Unknown table: {self.table_name}")
        
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
            
            return RuleResult(
                rule_id=rule.rule_id,
                status="PASS" if passed else "FAIL",
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
```

### 2.3 Stage 2 測試

**檔案**: `tests/test_framework/test_validator_checker.py`

```python
import pytest
from src.validators.checker import DataValidator

class TestDataValidator:
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

    def test_stock_daily_zero_price_fail(self):
        """0 元資料應 FAIL"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 0, "volume": 1000},
        ]
        validator = DataValidator("stock_daily", records)
        report = validator.run()
        
        assert len(report.failed_rules) > 0
        assert any(r.rule_id == "stock_daily_value_price_positive" for r in report.failed_rules)

    def test_stock_daily_with_expected_dates(self):
        """提供 expected_dates，檢查 completeness"""
        records = [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 100, "volume": 1000},
        ]
        expected_dates = ["2026-04-01", "2026-04-02"]  # 缺少一天
        validator = DataValidator("stock_daily", records, expected_dates=expected_dates)
        report = validator.run()
        
        # 應該有 completeness rule 失敗
        completeness_rules = [r for r in report.failed_rules if "completeness" in r.rule_id]
        assert len(completeness_rules) > 0

    def test_report_summary(self):
        """Report 摘要應正確"""
        records = [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        summary = report.summary
        assert summary["total_rules"] > 0
        assert summary["passed"] + summary["failed"] + summary["warnings"] == summary["total_rules"]

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
```

**執行測試**:
```bash
cd /home/ubuntu/projects/bcas_quant
pytest tests/test_framework/test_validator_checker.py -v
```

### ✅ Stage 2 驗收

- [ ] `src/validators/report.py` 實作完成
- [ ] `src/validators/checker.py` 實作完成
- [ ] `tests/test_framework/test_validator_checker.py` 全部 PASS
- [ ] Report 可正確序列化為 JSON

---

## 🎯 Stage 3: Trading Calendar 模組

### 3.1 實作 `src/utils/trading_calendar.py`

**檔案**: `src/utils/trading_calendar.py`

```python
from datetime import date, timedelta
import calendar
from typing import List
import logging

logger = logging.getLogger(__name__)

class TradingCalendar:
    """交易日曆（基於簡單規則）"""
    
    # 國定假日映射（年份 → [月-日]）
    NATIONAL_HOLIDAYS = {
        2026: [
            "01-01",  # 元旦
            "02-28",  # 和平紀念日
            "04-04",  # 兒童節
            "04-05",  # 清明節
            "06-10",  # 端午節
            "09-28",  # 教師節
            "10-10",  # 雙十節
        ]
    }
    
    # 補班日（年份 → [月-日]）
    MAKEUP_DAYS = {
        2026: []
    }
    
    @staticmethod
    def get_trading_days(year: int, month: int) -> List[str]:
        """
        回傳該月份的交易日清單（YYYY-MM-DD 格式）
        不包含：週六、週日、國定假日
        """
        trading_days = []
        
        # 生成該月所有日期
        days_in_month = calendar.monthrange(year, month)[1]
        
        for day in range(1, days_in_month + 1):
            current_date = date(year, month, day)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 排除週末（0=Monday, 5=Saturday, 6=Sunday）
            if current_date.weekday() >= 5:
                continue
            
            # 排除國定假日
            holiday_key = f"{month:02d}-{day:02d}"
            if year in TradingCalendar.NATIONAL_HOLIDAYS:
                if holiday_key in TradingCalendar.NATIONAL_HOLIDAYS[year]:
                    continue
            
            # 加入交易日
            trading_days.append(date_str)
        
        return sorted(trading_days)
    
    @staticmethod
    def count_trading_days(year: int, month: int) -> int:
        """回傳該月份的交易日數"""
        return len(TradingCalendar.get_trading_days(year, month))
    
    @staticmethod
    def get_trading_days_range(start_date: str, end_date: str) -> List[str]:
        """
        回傳日期範圍內的所有交易日（YYYY-MM-DD）
        start_date, end_date: 格式 "YYYY-MM-DD"
        """
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        all_trading_days = []
        current = start
        
        while current.year < end.year or (current.year == end.year and current.month <= end.month):
            trading_days = TradingCalendar.get_trading_days(current.year, current.month)
            # 只保留在日期範圍內的
            for day in trading_days:
                if start_date <= day <= end_date:
                    all_trading_days.append(day)
            
            # 移到下一個月
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        return sorted(list(set(all_trading_days)))
    
    @staticmethod
    def is_trading_day(date_str: str) -> bool:
        """檢查某日是否為交易日"""
        d = date.fromisoformat(date_str)
        trading_days = TradingCalendar.get_trading_days(d.year, d.month)
        return date_str in trading_days
```

### 3.2 Stage 3 測試

**檔案**: `tests/test_framework/test_trading_calendar.py`

```python
import pytest
from src.utils.trading_calendar import TradingCalendar

class TestTradingCalendar:
    def test_get_trading_days_2026_01(self):
        """2026-01 應排除週末與元旦"""
        trading_days = TradingCalendar.get_trading_days(2026, 1)
        assert len(trading_days) > 0
        assert "2026-01-01" not in trading_days  # 元旦
        
        # 檢查沒有週末
        from datetime import date
        for day_str in trading_days:
            d = date.fromisoformat(day_str)
            assert d.weekday() < 5, f"{day_str} 是週末"

    def test_get_trading_days_contains_weekdays_only(self):
        """交易日應只包含週一至週五"""
        trading_days = TradingCalendar.get_trading_days(2026, 4)
        from datetime import date
        for day_str in trading_days:
            d = date.fromisoformat(day_str)
            assert d.weekday() < 5

    def test_count_trading_days(self):
        """計數應與清單長度相符"""
        count = TradingCalendar.count_trading_days(2026, 4)
        days = TradingCalendar.get_trading_days(2026, 4)
        assert count == len(days)

    def test_get_trading_days_range(self):
        """日期範圍查詢應跨月份正確"""
        trading_days = TradingCalendar.get_trading_days_range("2026-01-01", "2026-02-28")
        assert len(trading_days) >= 30  # 兩個月至少 30 天

    def test_is_trading_day(self):
        """檢查特定日是否為交易日"""
        # 2026-01-01 是元旦，不是交易日
        assert not TradingCalendar.is_trading_day("2026-01-01")
        
        # 2026-01-02 是週五，是交易日
        assert TradingCalendar.is_trading_day("2026-01-02")
```

**執行測試**:
```bash
cd /home/ubuntu/projects/bcas_quant
pytest tests/test_framework/test_trading_calendar.py -v
```

### ✅ Stage 3 驗收

- [ ] `src/utils/trading_calendar.py` 實作完成
- [ ] `tests/test_framework/test_trading_calendar.py` 全部 PASS
- [ ] 已知月份的交易日數驗證正確

---

## 🎯 Stage 4: Pipeline 整合

### 4.1 修改 `src/run_daily.py`

**檔案**: `src/run_daily.py` (修改)

```python
import argparse
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def create_parser():
    """建立命令列參數解析器"""
    parser = argparse.ArgumentParser(
        description="Daily automated pipeline: Spider -> Validate -> Write -> Clean"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate data without writing to DB"
    )
    parser.add_argument(
        "--force-validation",
        action="store_true",
        help="Ignore validation errors and proceed with DB write"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation entirely (legacy mode)"
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleaner step"
    )
    return parser

def step_validate(raw_records_by_table: dict) -> dict:
    """
    驗證原始資料
    
    Args:
        raw_records_by_table: {table_name: [raw_dict]}
    
    Returns:
        {table_name: ValidationReport}
    """
    from src.validators.checker import DataValidator
    from src.validators.report_writer import ReportWriter
    from src.utils.trading_calendar import TradingCalendar
    
    logger.info("=" * 60)
    logger.info("STEP 2: Validate raw records")
    logger.info("=" * 60)
    
    reports = {}
    trading_calendar = TradingCalendar()
    
    # 假設驗證 2026-04（實際應從參數傳入）
    target_year = 2026
    target_month = 4
    expected_dates = trading_calendar.get_trading_days(target_year, target_month)
    
    for table_name, records in raw_records_by_table.items():
        logger.info(f"\nValidating {table_name}... ({len(records)} records)")
        
        # 準備 validator 參數
        kwargs = {}
        if table_name in ["stock_daily"]:
            kwargs["expected_dates"] = expected_dates
        
        # 執行驗證
        validator = DataValidator(table_name, records, **kwargs)
        report = validator.run()
        reports[table_name] = report
        
        # 記錄結果
        logger.info(f"  Total rules: {report.summary['total_rules']}")
        logger.info(f"  Passed: {report.summary['passed']}")
        logger.info(f"  Failed: {report.summary['failed']}")
        logger.info(f"  Warnings: {report.summary['warnings']}")
        
        for failed in report.failed_rules:
            logger.error(f"    ✗ {failed.rule_id}: {failed.detail}")
        
        for warning in report.warning_rules:
            logger.warning(f"    ⚠ {warning.rule_id}: {warning.detail}")
    
    # 保存報告
    for table_name, report in reports.items():
        filepath = ReportWriter.save_report(report, "logs/validation/")
        logger.info(f"  Report saved: {filepath}")
    
    summary_path = ReportWriter.save_summary(reports, "logs/validation/")
    logger.info(f"\nSummary saved: {summary_path}")
    
    return reports

def main():
    """主函數"""
    args = create_parser().parse_args()
    
    logger.info(f"Start: {datetime.now().isoformat()}")
    logger.info(f"Mode: {'validate-only' if args.validate_only else 'normal'}")
    
    # Phase 1: 爬蟲（需修改以支援 capture_raw）
    logger.info("\n[PHASE 1] Spider execution")
    # TODO: 呼叫 step_spiders(capture_raw=True)
    raw_records = {}  # 暫時 placeholder
    
    if args.skip_validation:
        logger.info("[INFO] Skipping validation, going directly to write...")
        # TODO: step_spiders(capture_raw=False, write_to_db=True)
        # TODO: step_clean()
        return
    
    # Phase 2: 驗證
    logger.info("\n[PHASE 2] Validation")
    reports = step_validate(raw_records)
    
    # 檢查結果
    has_errors = any(r.failed_rules for r in reports.values())
    
    if args.validate_only:
        logger.info("\n[RESULT] Validation complete. --validate-only mode, skipping write.")
        return
    
    if has_errors and not args.force_validation:
        logger.error("\n[RESULT] Validation FAILED. Aborting pipeline.")
        logger.error("  Use --force-validation to override.")
        sys.exit(1)
    
    if has_errors and args.force_validation:
        logger.warning("\n[WARNING] Validation has errors, but --force-validation is set. Proceeding...")
    
    # Phase 3: 寫入 DB
    logger.info("\n[PHASE 3] Write to database")
    # TODO: step_spiders(capture_raw=False, write_to_db=True)
    
    # Phase 4: Cleaner
    if not args.skip_clean:
        logger.info("\n[PHASE 4] Cleaner")
        # TODO: step_clean()
    
    logger.info(f"\n[RESULT] Pipeline complete. End: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
```

### 4.2 實作 `src/validators/report_writer.py`

**檔案**: `src/validators/report_writer.py`

```python
import json
import os
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ReportWriter:
    """報告寫入器"""
    
    @staticmethod
    def save_report(report, output_dir: str = "logs/validation/") -> str:
        """
        儲存單份報告到 JSON 檔案
        
        Returns:
            檔案路徑
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}_{report.table_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    @staticmethod
    def save_summary(reports: Dict, output_dir: str = "logs/validation/") -> str:
        """
        儲存彙整報告
        
        Args:
            reports: {table_name: ValidationReport}
        
        Returns:
            檔案路徑
        """
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        
        summary = {
            "timestamp": timestamp,
            "tables": {
                table: {
                    "total_rules": report.summary["total_rules"],
                    "passed": report.summary["passed"],
                    "failed": report.summary["failed"],
                    "warnings": report.summary["warnings"],
                    "total_checked": report.summary["total_checked"],
                }
                for table, report in reports.items()
            },
            "overall_pass": all(not r.failed_rules for r in reports.values()),
        }
        
        filepath = os.path.join(output_dir, f"{timestamp}_summary.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return filepath
```

### ✅ Stage 4 驗收

- [ ] `src/run_daily.py` 新增 CLI 參數支援
- [ ] `step_validate()` 函數完成
- [ ] `src/validators/report_writer.py` 實作完成
- [ ] 手動測試（--validate-only, --force-validation 等）

---

## 🎯 Stage 5 & 6: 整合測試

### 5.1 建立整合測試檔案

**檔案**: `tests/test_framework/test_validation_integration.py`

```python
import pytest
import os
import json
from src.validators.checker import DataValidator
from src.validators.report_writer import ReportWriter

class TestValidationIntegration:
    def test_full_pipeline_normal_data(self):
        """完整 pipeline：正常資料"""
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"},
                {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"},
            ],
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000},
                {"symbol": "2330", "date": "2026-04-02", "close_price": 101.0, "volume": 1100},
            ],
        }
        
        for table_name, recs in records.items():
            validator = DataValidator(table_name, recs)
            report = validator.run()
            assert not report.has_errors(), f"{table_name} should pass"

    def test_report_writer_save(self, tmp_path):
        """Report 寫入測試"""
        records = [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}]
        validator = DataValidator("stock_master", records)
        report = validator.run()
        
        # 寫入
        filepath = ReportWriter.save_report(report, str(tmp_path))
        assert os.path.exists(filepath)
        
        # 驗證 JSON 格式
        with open(filepath, 'r') as f:
            data = json.load(f)
        assert data["table_name"] == "stock_master"
        assert "summary" in data

    def test_report_writer_summary(self, tmp_path):
        """Summary 報告寫入測試"""
        records = {
            "stock_master": [
                {"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}
            ],
            "stock_daily": [
                {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000}
            ],
        }
        
        reports = {}
        for table_name, recs in records.items():
            validator = DataValidator(table_name, recs)
            reports[table_name] = validator.run()
        
        # 寫入 summary
        filepath = ReportWriter.save_summary(reports, str(tmp_path))
        assert os.path.exists(filepath)
        
        # 驗證 JSON 格式
        with open(filepath, 'r') as f:
            data = json.load(f)
        assert "tables" in data
        assert "overall_pass" in data
```

**執行測試**:
```bash
cd /home/ubuntu/projects/bcas_quant
pytest tests/test_framework/test_validation_integration.py -v
```

### ✅ Stage 5 & 6 驗收

- [ ] 整合測試全部 PASS
- [ ] Report JSON 可正確產出到 logs/validation/
- [ ] Summary 報告格式正確
- [ ] E2E 流程（spider → validate → report）可完整執行

---

## 📊 最終檢查清單

### 程式碼完成度

- [ ] Stage 1: Rules 定義（4 個檔案 × 5-7 條 rules）
- [ ] Stage 2: DataValidator & ValidationReport 實作
- [ ] Stage 3: TradingCalendar 模組
- [ ] Stage 4: run_daily.py 整合 + ReportWriter
- [ ] Stage 5 & 6: 整合測試

### 測試覆蓋度

- [ ] Unit tests: rules, checker, calendar
- [ ] Integration tests: E2E validation flow
- [ ] Coverage >= 85%

### 文件完成度

- [ ] README.md（入口點）
- [ ] DEVELOPMENT_PLAN.md
- [ ] STAGE_BREAKDOWN.md
- [ ] VALIDATION_RULES.md
- [ ] INTEGRATION_GUIDE.md
- [ ] BOUNDARIES_AND_CONSTRAINTS.md
- [ ] IMPLEMENTATION_NOTES.md

### 驗收交付物

- [ ] logs/validation/ 目錄建立
- [ ] JSON report 可正確產出
- [ ] CLI 參數 (--validate-only, --force-validation, --skip-validation) 可用
- [ ] 所有測試 PASS

---

## 🚀 部署後操作

### 正常運行

```bash
cd /home/ubuntu/projects/bcas_quant
python src/run_daily.py
# 預期：logs/validation/ 下有 4 個 table report + 1 個 summary
```

### 驗證模式

```bash
python src/run_daily.py --validate-only
# 預期：只驗證，不寫入 DB
```

### 查看報告

```bash
# 查看彙整報告
cat logs/validation/*_summary.json | jq

# 查看單表報告
cat logs/validation/*_stock_daily.json | jq
```

---

## 📞 常見問題

### Q: 若 Spider 層有異常怎樣？
**A**: Validator 不應捕捉 spider 異常。Spider 異常應在 spider 層被處理。

### Q: 若交易日曆有誤怎樣？
**A**: 更新 `src/utils/trading_calendar.py` 中的假日清單，重新執行。

### Q: JSON 報告格式可以改嗎？
**A**: 可以，但需更新 `ValidationReport.to_dict()` 與對應的讀取邏輯。

---

**本 Builder Prompt 為開發者的實作指南。逐個 Stage 完成，持續測試，最後交付。祝順利！** 🎯

**下一步**: 開始 Stage 1 - Rules 定義
