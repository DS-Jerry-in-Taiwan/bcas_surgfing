# Stage 分解與驗收標準

**本文件**深入各開發階段的具體步驟、測試方法、驗收指標。

---

## Stage 1：Validation Rule Definition

### 目標
針對四種資料類型，明確定義各自的檢查規則。

### 產出
`src/validators/rules.py` 及 `src/validators/{table}_rules.py` × 4

### 開發步驟

#### Step 1.1：定義 Rule 基類（`src/validators/rules.py`）

```python
# 結構參考
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
from enum import Enum

class RuleSeverity(Enum):
    ERROR = "error"      # 阻斷流程
    WARNING = "warning"  # 僅記錄，繼續

@dataclass
class ValidationRule:
    rule_id: str                    # 唯一識別，ex: "completeness_row_count"
    table_name: str                 # 適用 table
    description: str                # 檢查邏輯敘述
    severity: RuleSeverity         # error or warning
    checker_fn: Callable            # (records: List[Dict], **kwargs) -> (bool, str)
    example_pass: Optional[str] = None   # 通過範例描述
    example_fail: Optional[str] = None   # 失敗範例描述
```

#### Step 1.2：定義 stock_master rules（`src/validators/stock_master_rules.py`）

**預期規則清單**（至少 5 條）：

| Rule ID | 說明 | 嚴重度 |
|---------|------|-------|
| `structure_required_fields` | 欄位齊全（symbol, name, market_type, industry） | ERROR |
| `uniqueness_symbol` | symbol 不重複 | ERROR |
| `value_market_type` | market_type ∈ {TWSE, TPEx} | ERROR |
| `completeness_twse_coverage` | TWSE 回傳 > 1500 rows | WARNING |
| `completeness_tpex_coverage` | TPEx 回傳 > 500 rows | WARNING |

**實作範例**：
```python
def check_structure_required_fields(records: List[Dict]) -> Tuple[bool, str]:
    required = ['symbol', 'name', 'market_type', 'industry']
    missing_fields = set()
    for field in required:
        if not records or all(field not in r for r in records):
            missing_fields.add(field)
    if missing_fields:
        return False, f"Missing fields: {missing_fields}"
    return True, "All required fields present"

# 在 stock_master_rules.py 中定義
STOCK_MASTER_RULES = [
    ValidationRule(
        rule_id="structure_required_fields",
        table_name="stock_master",
        description="Check all required fields are present",
        severity=RuleSeverity.ERROR,
        checker_fn=check_structure_required_fields,
        example_pass="Records contain: symbol, name, market_type, industry",
        example_fail="Records missing: industry"
    ),
    # ... more rules
]
```

#### Step 1.3：定義 stock_daily rules（`src/validators/stock_daily_rules.py`）

**預期規則清單**（至少 5 條）：

| Rule ID | 說明 | 嚴重度 |
|---------|------|-------|
| `structure_required_fields` | 欄位齊全（symbol, date, close_price, volume） | ERROR |
| `value_price_positive` | close_price > 0 | ERROR |
| `value_volume_non_negative` | volume >= 0 | ERROR |
| `completeness_row_count` | 行數 = 預期交易日數 × symbol 數 | ERROR |
| `consistency_symbol_in_master` | 所有 symbol 都在 stock_master 中 | ERROR |

#### Step 1.4：定義 cb_master rules（`src/validators/cb_master_rules.py`）

**預期規則清單**：

| Rule ID | 說明 | 嚴重度 |
|---------|------|-------|
| `structure_required_fields` | 欄位齊全（cb_code, cb_name, conversion_price） | ERROR |
| `uniqueness_cb_code` | cb_code 不重複 | ERROR |
| `value_conversion_price_positive` | conversion_price > 0 | ERROR |
| `completeness_min_rows` | 至少回傳 10 rows | WARNING |

#### Step 1.5：定義 tpex_cb_daily rules（`src/validators/tpex_cb_daily_rules.py`）

**預期規則清單**：

| Rule ID | 說明 | 嚴重度 |
|---------|------|-------|
| `structure_required_fields` | 欄位齊全（cb_code, trade_date, closing_price） | ERROR |
| `value_price_positive` | closing_price > 0 | ERROR |
| `value_volume_non_negative` | volume >= 0 | ERROR |
| `consistency_cb_code_in_master` | 所有 cb_code 都在 cb_master 中 | ERROR |
| `consistency_date_format` | trade_date 格式為 YYYY-MM-DD | ERROR |

### 測試方法（Unit Tests）

**檔案**：`tests/test_framework/test_validator_rules.py`

```python
def test_stock_master_rule_structure_required_fields():
    """Should FAIL when required fields missing"""
    records = [{"symbol": "2330", "name": "TSMC"}]  # missing market_type, industry
    passed, msg = check_structure_required_fields(records)
    assert not passed
    assert "industry" in msg

def test_stock_daily_rule_value_price_positive():
    """Should FAIL when price <= 0"""
    records = [{"close_price": 0}]
    passed, msg = check_value_price_positive(records)
    assert not passed

def test_stock_daily_rule_value_price_positive_pass():
    """Should PASS when all prices > 0"""
    records = [{"close_price": 100.5}, {"close_price": 200.0}]
    passed, msg = check_value_price_positive(records)
    assert passed
```

### 驗收指標

```bash
pytest tests/test_framework/test_validator_rules.py -v
# 預期：
# - ✅ 每條 rule 的 checker_fn 可被 import 且可執行
# - ✅ 正常資料通過 checker_fn → PASS
# - ✅ 異常資料通過 checker_fn → FAIL
# - ✅ 每條 rule 有 example_pass 與 example_fail 敘述
```

---

## Stage 2：Checker 實作

### 目標
實作可執行檢查的 `DataValidator` class。

### 產出
`src/validators/checker.py` 與 `src/validators/report.py`

### 開發步驟

#### Step 2.1：定義 ValidationReport 結構（`src/validators/report.py`）

```python
@dataclass
class RuleResult:
    rule_id: str
    status: str              # "PASS" | "FAIL" | "WARNING"
    detail: str              # 詳細信息
    count: int               # 受影響的 row 數或統計量

@dataclass
class ValidationReport:
    table_name: str
    total_checked: int       # 總共檢查多少 rows
    passed_rules: List[RuleResult]
    failed_rules: List[RuleResult]
    warning_rules: List[RuleResult]
    timestamp: str           # ISO format
    
    @property
    def summary(self) -> Dict[str, int]:
        return {
            "total_rules": len(self.passed_rules) + len(self.failed_rules) + len(self.warning_rules),
            "passed": len(self.passed_rules),
            "failed": len(self.failed_rules),
            "warnings": len(self.warning_rules),
            "total_checked": self.total_checked,
        }
    
    def to_dict(self) -> Dict:
        # 便於 JSON 序列化
        pass
    
    def __str__(self) -> str:
        # 便於 log 打印
        pass
```

#### Step 2.2：實作 DataValidator（`src/validators/checker.py`）

```python
class DataValidator:
    def __init__(
        self, 
        table_name: str, 
        records: List[Dict],
        expected_dates: Optional[List[str]] = None,
        expected_symbols: Optional[List[str]] = None,
    ):
        """
        Args:
            table_name: 四種之一 (stock_master, stock_daily, cb_master, tpex_cb_daily)
            records: raw records list (list of dict)
            expected_dates: 交易日期清單（用於 completeness 檢查）
            expected_symbols: 預期 symbol 清單（用於 consistency 檢查）
        """
        self.table_name = table_name
        self.records = records
        self.expected_dates = expected_dates
        self.expected_symbols = expected_symbols
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[ValidationRule]:
        """根據 table_name 載入對應的 rules"""
        if self.table_name == "stock_master":
            from . import stock_master_rules
            return stock_master_rules.STOCK_MASTER_RULES
        # ... 其他 table
    
    def run(self) -> ValidationReport:
        """執行所有 rules，回傳 report"""
        passed = []
        failed = []
        warning = []
        
        for rule in self.rules:
            try:
                result = self._execute_rule(rule)
                if result.status == "PASS":
                    passed.append(result)
                elif result.status == "FAIL":
                    failed.append(result)
                else:  # WARNING
                    warning.append(result)
            except Exception as e:
                # 規則執行異常時也要記錄
                failed.append(RuleResult(
                    rule_id=rule.rule_id,
                    status="FAIL",
                    detail=f"Rule execution error: {str(e)}",
                    count=0
                ))
        
        return ValidationReport(
            table_name=self.table_name,
            total_checked=len(self.records),
            passed_rules=passed,
            failed_rules=failed,
            warning_rules=warning,
            timestamp=datetime.now().isoformat(),
        )
    
    def _execute_rule(self, rule: ValidationRule) -> RuleResult:
        """執行單一 rule"""
        try:
            # 根據 rule 所需的參數準備 kwargs
            kwargs = {}
            if "expected_dates" in rule.checker_fn.__code__.co_varnames:
                kwargs["expected_dates"] = self.expected_dates
            if "expected_symbols" in rule.checker_fn.__code__.co_varnames:
                kwargs["expected_symbols"] = self.expected_symbols
            
            passed, detail = rule.checker_fn(self.records, **kwargs)
            
            return RuleResult(
                rule_id=rule.rule_id,
                status="PASS" if passed else "FAIL",
                detail=detail,
                count=len(self.records) if passed else 0,
            )
        except Exception as e:
            return RuleResult(
                rule_id=rule.rule_id,
                status="FAIL",
                detail=f"Error: {str(e)}",
                count=0,
            )
```

#### Step 2.3：測試 DataValidator

**檔案**：`tests/test_framework/test_validator_checker.py`

```python
def test_validator_stock_daily_pass():
    """正常資料應全部 PASS"""
    records = [
        {"symbol": "2330", "date": "2026-01-01", "close_price": 100.0, "volume": 1000},
        {"symbol": "2330", "date": "2026-01-02", "close_price": 101.0, "volume": 1100},
    ]
    validator = DataValidator("stock_daily", records)
    report = validator.run()
    assert len(report.failed_rules) == 0, f"Should pass but failed: {report.failed_rules}"

def test_validator_stock_daily_fail_zero_price():
    """包含 0 元資料應 FAIL"""
    records = [
        {"symbol": "2330", "date": "2026-01-01", "close_price": 0, "volume": 1000},
    ]
    validator = DataValidator("stock_daily", records)
    report = validator.run()
    assert any(r.rule_id == "value_price_positive" for r in report.failed_rules)

def test_validator_with_expected_dates():
    """指定交易日期，檢查 completeness"""
    records = [
        {"symbol": "2330", "date": "2026-01-01", "close_price": 100.0, "volume": 1000},
        # 缺少 2026-01-02
    ]
    expected_dates = ["2026-01-01", "2026-01-02"]
    validator = DataValidator("stock_daily", records, expected_dates=expected_dates)
    report = validator.run()
    # 應有 completeness_row_count FAIL
    assert any(r.rule_id == "completeness_row_count" and r.status == "FAIL" 
               for r in report.failed_rules)
```

### 驗收指標

```bash
pytest tests/test_framework/test_validator_checker.py -v
# 預期：
# - ✅ 正常資料 → report.failed_rules 為空
# - ✅ 缺失資料 → 對應的 rule FAIL
# - ✅ 異常值資料 → 對應的 rule FAIL
# - ✅ report.summary 計算正確
# - ✅ report.to_dict() 可被 JSON dump
```

---

## Stage 3：交易日曆模組

### 目標
提供預期日期區間與預期 row count，供 completeness 檢查使用。

### 產出
`src/utils/trading_calendar.py`

### 開發步驟

#### Step 3.1：定義交易日曆規則

```python
# src/utils/trading_calendar.py

class TradingCalendar:
    """
    基於簡單規則（排除週末 + 內建假日清單）產生交易日。
    第一版不依賴外部 API。
    """
    
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
    
    # 補班日（年份 → [月-日]）- 第一版先空著
    MAKEUP_DAYS = {
        2026: []
    }
    
    @staticmethod
    def get_trading_days(year: int, month: int) -> List[str]:
        """
        回傳該月份的交易日清單（YYYY-MM-DD 格式）
        不包含：週六、週日、國定假日
        包含：補班日（若有）
        """
        import calendar
        from datetime import date, timedelta
        
        trading_days = []
        # 生成該月所有日期
        month_calendar = calendar.monthcalendar(year, month)
        for day in range(1, calendar.monthrange(year, month)[1] + 1):
            current_date = date(year, month, day)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # 排除週末（0=Monday, 5=Saturday, 6=Sunday）
            if current_date.weekday() >= 5:
                continue
            
            # 排除國定假日
            holiday_key = f"{month:02d}-{day:02d}"
            if TradingCalendar.NATIONAL_HOLIDAYS.get(year, []) and holiday_key in TradingCalendar.NATIONAL_HOLIDAYS[year]:
                continue
            
            # 加入補班日
            if TradingCalendar.MAKEUP_DAYS.get(year, []) and holiday_key in TradingCalendar.MAKEUP_DAYS[year]:
                trading_days.append(date_str)
                continue
            
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
        """
        from datetime import date, timedelta
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        all_trading_days = []
        current = start
        while current <= end:
            trading_days = TradingCalendar.get_trading_days(current.year, current.month)
            all_trading_days.extend([d for d in trading_days if start_date <= d <= end_date])
            # 移到下一個月
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        return sorted(list(set(all_trading_days)))
```

#### Step 3.2：測試交易日曆

**檔案**：`tests/test_framework/test_trading_calendar.py`

```python
def test_trading_calendar_2026_01():
    """2026-01 應排除週末與元旦"""
    trading_days = TradingCalendar.get_trading_days(2026, 1)
    assert len(trading_days) == 20  # 假設 2026-01 有 20 個交易日
    assert "2026-01-01" not in trading_days  # 元旦
    # 檢查沒有週末
    for day_str in trading_days:
        date_obj = date.fromisoformat(day_str)
        assert date_obj.weekday() < 5  # 0=Mon, 4=Fri

def test_trading_calendar_range():
    """跨月份查詢應包含所有交易日"""
    trading_days = TradingCalendar.get_trading_days_range("2026-01-01", "2026-02-28")
    # 應該 >= 30 天（兩個月）
    assert len(trading_days) >= 30

def test_count_trading_days():
    """計數與清單長度應一致"""
    count = TradingCalendar.count_trading_days(2026, 1)
    days = TradingCalendar.get_trading_days(2026, 1)
    assert count == len(days)
```

### 驗收指標

```bash
pytest tests/test_framework/test_trading_calendar.py -v
# 預期：
# - ✅ 已知月份回傳正確交易日清單
# - ✅ 週末不在清單中
# - ✅ 國定假日被排除
# - ✅ 跨月份計算正確
```

---

## Stage 4：Pipeline 整合

### 目標
將 validation 插入 spider 完成後、pipeline flush 前，或在 flush 後立即檢查。

### 產出
修改 `src/run_daily.py` 與相關 spider，新增 validation 步驟

### 開發步驟

#### Step 4.1：修改 run_daily.py

```python
# 新增 CLI 參數
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--validate-only", action="store_true", help="Only validate, don't write to DB")
parser.add_argument("--force-validation", action="store_true", help="Ignore validation errors and proceed")
parser.add_argument("--skip-validation", action="store_true", help="Skip validation entirely")
args = parser.parse_args()

# 新增 step_validate() 方法
def step_validate(spiders_output: Dict[str, List[Dict]]) -> Dict[str, ValidationReport]:
    """
    Validate raw records from all spiders
    Args:
        spiders_output: {table_name: [raw_records]}
    Returns:
        {table_name: ValidationReport}
    """
    from src.validators.checker import DataValidator
    from src.validators.report_writer import ReportWriter
    from src.utils.trading_calendar import TradingCalendar
    
    reports = {}
    for table_name, records in spiders_output.items():
        # 準備 expected_dates 與 expected_symbols
        kwargs = {}
        if table_name in ["stock_daily", "tpex_cb_daily"]:
            # 假設要驗證 2026-04 的資料
            kwargs["expected_dates"] = TradingCalendar.get_trading_days(2026, 4)
        
        validator = DataValidator(table_name, records, **kwargs)
        report = validator.run()
        reports[table_name] = report
        
        # 打印到 console
        logger.info(f"ValidationReport for {table_name}: {report}")
        
        # 儲存到 JSON
        ReportWriter.save_report(report, f"logs/validation/")
    
    return reports

# 新增整合邏輯到 main
def main():
    if args.skip_validation:
        # 舊流程：直接爬取與寫入
        step_spiders()
        step_clean()
    else:
        # 新流程：驗證 + 寫入 + 清洗
        raw_records = step_spiders(capture_raw=True)  # 修改 spider 回傳 raw records
        
        # 驗證
        reports = step_validate(raw_records)
        
        # 檢查驗證結果
        has_errors = any(r.failed_rules for r in reports.values())
        
        if args.validate_only:
            # 只驗證，不寫入
            logger.info("Validation complete. No data written to DB.")
            return
        
        if has_errors and not args.force_validation:
            logger.error("Validation FAILED. Aborting pipeline.")
            sys.exit(1)
        
        if has_errors and args.force_validation:
            logger.warning("Validation has errors, but --force-validation is set. Proceeding...")
        
        # 寫入
        step_spiders(write=True)  # 實際寫入
        step_clean()
        
        logger.info("Pipeline complete.")
```

#### Step 4.2：修改 Spider 以支援 capture_raw

```python
# src/spiders/base_spider.py (或各個 spider 的 fetch_all 方法)

class BaseSpider:
    def __init__(self, ..., capture_raw=False, ...):
        self.capture_raw = capture_raw
        self.raw_records = []  # 儲存原始 records
    
    def fetch_all(self):
        # 爬取邏輯
        items = self.parse_data()  # 獲得 Item objects
        
        # 如果 capture_raw，儲存 dict format
        if self.capture_raw:
            self.raw_records = [item.to_dict() for item in items]
        
        # 正常流程
        for item in items:
            self.pipeline.save_items(item)
    
    def get_raw_records(self):
        """回傳原始 records list"""
        return self.raw_records
```

### 驗收指標

```bash
# Scenario 1: 正常流程
python src/run_daily.py
# 預期：logs/validation/ 下有 4 個 table report

# Scenario 2: validate-only
python src/run_daily.py --validate-only
# 預期：DB 無新資料，但有 report

# Scenario 3: force 繼續
python src/run_daily.py --force-validation
# 預期：即使驗證 failed 仍寫入 DB
```

---

## Stage 5：Report 產出

### 目標
將 validation 結果寫入 JSON 檔案與可選的 DB log table。

### 產出
`src/validators/report_writer.py`

### 開發步驟

```python
# src/validators/report_writer.py

class ReportWriter:
    @staticmethod
    def save_report(report: ValidationReport, output_dir: str = "logs/validation/") -> str:
        """
        儲存 report 到 JSON 檔案
        Filename: YYYY-MM-DD_HHMMSS_{table_name}.json
        """
        import json
        from datetime import datetime
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{timestamp}_{report.table_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return filepath
    
    @staticmethod
    def save_summary(reports: Dict[str, ValidationReport], output_dir: str = "logs/validation/") -> str:
        """儲存彙整報告"""
        import json
        from datetime import datetime
        
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

---

## Stage 6：整合測試

### 目標
驗證整個 validation pipeline 可正常跑完。

### 測試項目

**檔案**：`tests/test_framework/test_validation_integration.py`

```python
def test_full_pipeline_normal_data():
    """完整 pipeline：正常資料"""
    # Mock spider output
    raw_records = {
        "stock_master": [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE"}],
        "stock_daily": [
            {"symbol": "2330", "date": "2026-04-01", "close_price": 100.0, "volume": 1000}
        ],
    }
    
    # Validate
    reports = step_validate(raw_records)
    
    # Check pass
    assert not any(r.failed_rules for r in reports.values())

def test_validate_only_mode():
    """--validate-only 不寫入 DB"""
    # 執行 run_daily.py --validate-only
    # 確認 DB 無新資料
    # 確認 logs/validation/ 有 report 檔案

def test_force_validation_mode():
    """--force-validation 即使 failed 仍寫入"""
    # Mock 異常資料
    # 執行 with --force-validation
    # 確認 DB 有資料（雖然驗證失敗）
```

---

## 總結表

| 階段 | 主要產出 | 單位測試通過 | 整合測試 | 預估工時 |
|------|---------|-----------|---------|---------|
| 1 | Rules 定義 × 4 | ✅ test_validator_rules.py | N/A | 1-2 days |
| 2 | DataValidator + Report | ✅ test_validator_checker.py | N/A | 1-2 days |
| 3 | TradingCalendar | ✅ test_trading_calendar.py | N/A | 0.5 days |
| 4 | run_daily.py 整合 | ✅ 各 spider 單測 | ⚠️ 手動測試 | 1-2 days |
| 5 | ReportWriter | ✅ unit test | ⚠️ 檢查檔案輸出 | 0.5 days |
| 6 | E2E 整合測試 | ✅ test_validation_integration.py | ✅ Full pipeline | 1-2 days |

**版本控制**  
- v1.0 (2026-04-30): 初版
