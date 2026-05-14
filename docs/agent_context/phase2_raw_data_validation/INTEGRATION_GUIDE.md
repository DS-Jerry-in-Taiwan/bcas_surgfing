# Pipeline 整合指南（實際實作）

本文件說明 validation layer 如何與 `run_daily.py` 和 spider 架構實際整合。

---

## 整合架構

```
Step 1: 爬蟲 (step_spiders) — collect_only 模式
  spider.fetch_*()
    ├─ self.add_item(item)          ← 暫存到 _pending_items（不寫 DB）
    └─ spider.get_items() → to_dict ← 收集 raw records
  ↓
  回傳 (metadata_results, collected_records, pipelines)
    - metadata: {table: {success, count, error}}
    - records:  {table: [item.to_dict(), ...]}
    - pipelines: {table: (PostgresPipeline, spider)}
  ↓
Step 2: 驗證 (step_validate)
  DataValidator(table_name, records, ...)
    ├─ 自動載入對應的 24 條規則
    ├─ 自動注入 cross-table 參數
    │   ├─ stock_daily     → expected_symbols from stock_master records
    │   └─ tpex_cb_daily   → expected_cb_codes from cb_master records
    └─ validator.run() → ValidationReport
  ↓
  report.has_errors() ?
    ├─ Yes + 無 --force  → clear _pending_items + exit(1)  ← 髒資料被阻擋
    ├─ Yes + --force     → 繼續到 flush
    └─ No                → 繼續到 flush
  ↓
  Step 2.5: 寫入 DB (flush_pipelines)
    spider.flush_items(pipeline)    ← 驗證通過後才真的寫入
    pipeline.close()
  ↓
Step 3: 清洗 (step_clean)
  DataCleaner.run_all()  ← 不變
```

---

## 實際實作細節

### 1. `BaseSpider` 的抽象層

每個 spider 的 item 存入統一由 `add_item()` 處理：

```python
class BaseSpider:
    def __init__(self, ...):
        self._pending_items: List = []
        self.collect_only: bool = False

    def add_item(self, item) -> None:
        """統一的 item 儲存入口
        
        在 collect_only 模式下暫存不寫入；
        否則立即寫入 pipeline（向後相容）。
        """
        self._pending_items.append(item)
        pipeline = getattr(self, 'pipeline', None)
        if pipeline and not self.collect_only:
            pipeline.save_items(item)

    def flush_items(self, pipeline=None) -> None:
        """將暫存的 items 寫入指定的 pipeline"""
        p = pipeline or getattr(self, 'pipeline', None)
        if not p:
            return
        for item in self._pending_items:
            p.save_items(item)
        self._pending_items.clear()
```

### 2. `run_daily.py` 的關鍵修改

#### 2.1 `step_spiders()` — collect_only 模式

```python
def step_spiders() -> tuple:
    """
    Returns:
        (metadata_results, collected_records, pipelines)
        - metadata_results: dict {table: {success, count, error}}
        - collected_records: dict {table: [{...}, ...]}
        - pipelines: dict {table: (PostgresPipeline, spider)}
    """
    results = {}
    records = {}
    pipelines = {}

    # Stock Master
    p = PostgresPipeline(table_name="stock_master", batch_size=500, **DB_CONFIG)
    s = StockMasterSpider(pipeline=p)
    s.collect_only = True          # ← 關鍵：設定 collect_only
    try:
        r = s.fetch_twse()
        results["stock_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["stock_master"] = [
            item.to_dict() for item in s.get_items()
        ]
        pipelines["stock_master"] = (p, s)  # ← 保留 pipeline 供後續 flush
    except:
        s.close()
        raise

    # ... 其他 3 張表同樣模式

    return results, records, pipelines
```

#### 2.2 `flush_pipelines()` — 驗證通過後寫入

```python
def flush_pipelines(pipelines: dict) -> None:
    """將暫存的 items 寫入 DB（驗證通過後呼叫）"""
    for table_name, (pipeline, spider) in pipelines.items():
        try:
            count = spider.get_pending_count()
            if count > 0:
                logger.info(f"Flushing {count} items to {table_name}...")
                spider.flush_items(pipeline)
            pipeline.close()
            logger.info(f"  ✅ {table_name}: {count} records written")
        except Exception as e:
            logger.error(f"  ❌ {table_name} flush failed: {e}")
```

#### 2.3 `main()` — 閘門邏輯

```python
def main():
    args = parse_args()

    if not args.clean_only:
        # Step 1: 爬蟲（collect_only）
        spider_result, spider_records, spider_pipelines = step_spiders()

        # Step 2: 驗證
        validation_result = step_validate(spider_result, spider_records)

        if validation_result["has_errors"] and not args.force_validation:
            # 驗證失敗：清除暫存，exit(1)
            for _, (p, s) in spider_pipelines.items():
                s._pending_items.clear()
                p.close()
            sys.exit(1)

        # Step 2.5: 寫入 DB（驗證通過後）
        if not args.validate_only:
            flush_pipelines(spider_pipelines)
        else:
            # --validate-only: 清除暫存不寫入
            for _, (p, s) in spider_pipelines.items():
                s._pending_items.clear()
                p.close()
            sys.exit(0 if not has_errors else 1)

    if not args.skip_clean and not args.validate_only:
        # Step 3: 清洗
        step_clean()
```

### 3. CLI 參數

| 參數 | 流程 | DB 寫入 |
|------|------|---------|
| (無) | fetch → validate → flush → clean | ✅ 驗證後 |
| `--validate-only` | fetch → validate → exit | ❌ 不寫入 |
| `--force-validation` | fetch → validate → flush → clean | ✅ 強制 |
| `--skip-clean` | fetch → validate → flush | ✅ 驗證後 |
| `--clean-only` | clean only | ❌ 不執行 |

---

## 4 種 CLI 模式的流程

### 正常模式
```
fetch(collect_only=True)
  ↓
validate(records)
  ↓
report.has_errors()? → No
  ↓
flush_pipelines() → 寫入 DB
  ↓
clean()
```

### --validate-only
```
fetch(collect_only=True)
  ↓
validate(records)
  ↓
report.has_errors()? → No / Yes
  ↓
_pending_items.clear()
  ↓
exit(0) / exit(1)
```

### --force-validation
```
fetch(collect_only=True)
  ↓
validate(records)
  ↓
report.has_errors()? → Yes + --force
  ↓
flush_pipelines() → 寫入 DB（強制）
  ↓
clean()
```

### --clean-only
```
fetch / validate / flush 全部跳過
  ↓
clean()
```
        results["stock_master"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["stock_master"] = [
            item.to_dict() for item in s.get_items()
        ]  # ← 收集 raw records
    finally:
        s.close()

    # ... 其他 3 張表同樣模式

    return results, records
```

**關鍵設計**：
- Spider 的 `self.items` 已經在 `fetch_*()` 過程中累積了所有 `BaseItem`
- `spider.get_items()` 回傳所有 items
- `item.to_dict()` 轉換為 dict 供 DataValidator 使用
- Pipeline 寫入 DB 和 records 收集互不影響

#### 1.2 `step_validate()` — 實際執行 24 條規則

```python
def step_validate(spider_results: dict, collected_records: dict = None) -> dict:
    """
    Args:
        spider_results: {table: {success, count, error}}
        collected_records: {table: [{...}, ...]}

    Returns:
        {"validation_dir": str, "reports": dict, "has_errors": bool}
    """
    validation_reports = {}
    validated_objects = {}
    global_has_errors = False

    for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
        spider_result = spider_results.get(table_name, {})

        # Skip conditions
        if not spider_result.get("success"):
            validation_reports[table_name] = {"skipped": True, "reason": "spider failed"}
            continue

        records = (collected_records or {}).get(table_name, [])
        if not records:
            validation_reports[table_name] = {"skipped": True, "reason": "no records"}
            continue

        # Cross-table parameter injection
        master_symbols = [
            r["symbol"] for r in collected_records.get("stock_master", [])
            if r.get("symbol")
        ] if collected_records else None

        master_cb_codes = [
            r["cb_code"] for r in collected_records.get("cb_master", [])
            if r.get("cb_code")
        ] if collected_records else None

        # Execute DataValidator with real records
        validator = DataValidator(
            table_name=table_name,
            records=records,
            expected_symbols=master_symbols if table_name == "stock_daily" else None,
            expected_cb_codes=master_cb_codes if table_name == "tpex_cb_daily" else None,
        )
        report = validator.run()

        table_has_errors = report.has_errors()
        if table_has_errors:
            global_has_errors = True

        validated_objects[table_name] = report
        validation_reports[table_name] = report.to_dict()

    # Save JSON reports
    if validated_objects:
        ReportWriter.save_summary(validated_objects, "logs/validation/")
        for report_obj in validated_objects.values():
            ReportWriter.save_report(report_obj, "logs/validation/")

    return {
        "validation_dir": "logs/validation",
        "reports": validation_reports,
        "has_errors": global_has_errors,
    }
```

### 2. Cross-table 參數注入機制

`step_validate()` 在執行 DataValidator 之前，會自動從 `collected_records` 提取 cross-table 參考資料：

```
collected_records = {
    "stock_master": [{symbol, name, market_type, industry}, ...],
    "stock_daily":  [{symbol, date, close_price, volume}, ...],
    "cb_master":    [{cb_code, cb_name, conversion_price}, ...],
    "tpex_cb_daily": [{cb_code, trade_date, closing_price, volume}, ...],
}

stock_daily 驗證時:
  master_symbols ← stock_master records 中的 symbol 列表
  DataValidator(records, expected_symbols=master_symbols)
  → consistency_symbol_in_master rule 可以比對

tpex_cb_daily 驗證時:
  master_cb_codes ← cb_master records 中的 cb_code 列表
  DataValidator(records, expected_cb_codes=master_cb_codes)
  → consistency_cb_code_in_master rule 可以比對
```

### 3. CLI 參數

| 參數 | 行為 |
|------|------|
| (無) | 爬蟲 → 驗證 → 清洗，驗證失敗 exit(1) |
| `--validate-only` | 爬蟲 → 驗證 → exit(0/1)，不執行清洗 |
| `--force-validation` | 驗證失敗仍繼續清洗 |
| `--skip-clean` | 爬蟲 → 驗證 → exit(0/1)，不執行清洗 |
| `--clean-only` | 僅清洗，跳過爬蟲和驗證 |

### 4. 流程控制邏輯

```python
def main():
    args = parse_args()

    if not args.clean_only:
        # Step 1: 爬蟲
        spider_result, spider_records = step_spiders()
        report["spiders"] = spider_result

        # Step 2: 驗證（除非 --clean-only）
        validation_result = step_validate(spider_result, spider_records)
        report["validation"] = validation_result

        if validation_result["has_errors"]:
            if not args.force_validation:
                sys.exit(1)  # 預設：中止
            # --force-validation: 繼續

        if args.validate_only:
            sys.exit(0 if not validation_result["has_errors"] else 1)

    if not args.skip_clean and not args.validate_only:
        # Step 3: 清洗
        step_clean()
```

---

## 報告輸出

### 位置
`logs/validation/`

### 檔案命名
```
{timestamp}_{table_name}.json     ← 單表報告（由 ReportWriter.save_report() 輸出）
{timestamp}_summary.json          ← 彙整報告（由 ReportWriter.save_summary() 輸出）
```

### 單表報告結構（DataValidator.to_dict()）

```json
{
  "table_name": "stock_master",
  "total_checked": 2,
  "passed_rules": [
    {"rule_id": "stock_master_structure_required_fields", "status": "PASS", ...},
    {"rule_id": "stock_master_uniqueness_symbol", "status": "PASS", ...}
  ],
  "failed_rules": [],
  "warning_rules": [
    {"rule_id": "stock_master_completeness_twse_coverage", "status": "WARNING", ...}
  ],
  "skipped_rules": [],
  "summary": {
    "total_rules": 6,
    "passed": 5,
    "failed": 0,
    "warnings": 1,
    "skipped": 0,
    "total_checked": 2
  },
  "timestamp": "2026-04-30T09:30:00.123456"
}
```

### 彙整報告結構

```json
{
  "timestamp": "2026-04-30_093000",
  "tables": {
    "stock_master": {
      "total_rules": 6,
      "passed": 5,
      "failed": 0,
      "warnings": 1,
      "skipped": 0,
      "total_checked": 2
    },
    "stock_daily": {...},
    "cb_master": {...},
    "tpex_cb_daily": {...}
  },
  "overall_pass": true
}
```

---

## 使用範例

### 正常流程
```bash
$ python3 src/run_daily.py
============================================================
Step 1: 爬蟲（collect only，暫不寫入 DB）
============================================================
  ✅ stock_master: 1850
  ✅ stock_daily: 63
  ✅ cb_master: 150
  ✅ tpex_cb_daily: 480
============================================================
Step 2: 驗證
============================================================
  ✅ 驗證通過
  報告位置: logs/validation
============================================================
Step 2.5: 寫入 DB
============================================================
  ✅ stock_master: 1850 records written
  ✅ stock_daily: 63 records written
  ✅ cb_master: 150 records written
  ✅ tpex_cb_daily: 480 records written
============================================================
Step 3: 清洗
============================================================
  ✅ stock_daily: 63 OK / 0 NOT_FOUND
  ✅ tpex_cb_daily: 480 OK / 0 NOT_FOUND
============================================================
完成
============================================================
```

### 僅驗證（不寫入 DB）
```bash
$ python3 src/run_daily.py --validate-only
============================================================
Step 2: 驗證
============================================================
  ✅ 驗證通過
============================================================
完成（--validate-only）
============================================================
```

### 強制繼續（驗證失敗仍執行）
```bash
$ python3 src/run_daily.py --force-validation
============================================================
Step 2: 驗證
============================================================
  ❌ 驗證失敗
  ⚠️  強制繼續（--force-validation）
Step 2.5: 寫入 DB
============================================================
  ✅ stock_master: 1850 records written
============================================================
Step 3: 清洗
============================================================
...
```

---

## 設計決策

### collect_only 模式的設計考量
- `add_item()` 是統一入口，collect_only=True 時暫存不寫入
- collect_only=False 時行為與改造前完全一致（向後相容）
- `flush_items()` 可指定不同的 pipeline（用於測試或重導向）

### ERROR vs WARNING 的影響
- **ERROR** 規則失敗 → `report.has_errors() = True` → 預設中止 pipeline
- **WARNING** 規則失敗 → 僅記錄在 report 中，不影響流程
- ERROR 規則數：19 條 / WARNING 規則數：5 條

### 驗證閘門的位置
```
fetch → collect → validate → gate → flush → clean
                               ↑
                         這裡擋住髒資料進 DB
```
驗證閘門從「擋 cleaner」改成「擋 DB write」，真正保護資料品質。

---

## 版本記錄

- v1.0 (2026-04-30): 初版規劃（規劃用）
- v2.0 (2026-04-30): 更新為實際實作，DataValidator 串接
- v3.0 (2026-04-30): 加入 collect_only 模式，驗證通過後才寫入 DB
