# 實作注意事項

本文件記錄開發過程中可能遇到的陷阱、設計決定、與優化建議。

---

## 1. Spider 捕捉 Raw Records 的技術細節

### 問題：何時捕捉？

Spider 的流程通常是：
```
API call → parse to Items → validate Item → save to pipeline
```

**選項 A**: 在 Item 產生時捕捉（推薦）
```python
for row in api_response:
    item = StockDailyItem(...)
    if self.capture_raw:
        self.raw_records.append(item.to_dict())
    self.pipeline.save_items(item)
```

**優點**：
- 簡單直接
- Raw record 已是 dict format（易於序列化）

**缺點**：
- Item 產生時可能已經進行了某些轉換（如日期格式化）
- 若想要「最原始的格式」可能不符合

**選項 B**: 在 API 回應層捕捉
```python
raw_response = api_call()
if self.capture_raw:
    self.raw_records.append(raw_response)  # JSON/CSV 原文
items = self.parse(raw_response)
for item in items:
    self.pipeline.save_items(item)
```

**優點**：
- 最接近原始形式
- 便於 debug API 問題

**缺點**：
- 可能佔用大量內存（原始 JSON/CSV 有冗餘信息）
- 與 Validator 的期望不符（Validator 期望 Item dict format）

**建議**：採用 **選項 A**（Item 層捕捉），因為 Validator 預期的就是 Item dict。

---

## 2. 交易日曆的精度與維護

### 問題：如何精確定義「交易日」？

假期規則包括：
- 固定假日（元旦、和平紀念日等）
- 浮動假日（端午節、中秋節 lunar calendar 計算）
- 補班日（政府臨時公告）
- 大盤故障（罕見，如 2021 年交易所故障）

### 第一版實作（簡化版）

```python
NATIONAL_HOLIDAYS = {
    2026: ["01-01", "02-28", "04-04", "04-05", "06-10", "09-28", "10-10"]
}
```

**限制**：
- 端午節、中秋節等 lunar calendar 計算的節日需硬寫
- 補班日需人工輸入
- 無法預測未來兩年以上

### 改進建議（非 Phase 2）

1. **簡單 config 檔**：
   ```yaml
   # holidays.yaml
   2026:
     - date: 2026-06-10  # 端午節
       name: Dragon Boat Festival
   ```

2. **外部來源**：
   - 勞動部行事曆 API
   - 第三方假日庫（pyholidays）
   - 但需謹慎添加外部依賴

### 當前建議

- 年初時由人工更新 `trading_calendar.py` 中的假日清單
- 可在 GitHub issue 中追蹤補班日等臨時異動
- 若有遺漏，可用 `--skip-validation` 跳過當天驗證

---

## 3. Validator Rule 的參數化與複用

### 問題：如何讓 rule 支援參數注入？

不同執行場景可能需要不同的檢查標準：
- 月度爬蟲：檢查該月的交易日
- 年度爬蟲：檢查該年的交易日
- 補爬某天：檢查該天是否交易日

### 實作方案

在 `DataValidator.__init__()` 中支援可選參數：

```python
class DataValidator:
    def __init__(
        self,
        table_name: str,
        records: List[Dict],
        expected_dates: Optional[List[str]] = None,
        expected_symbols: Optional[List[str]] = None,
        min_row_count: Optional[int] = None,
        **kwargs
    ):
        """
        Args:
            expected_dates: 預期交易日清單（用於 completeness check）
            expected_symbols: 預期 symbol 清單（用於 consistency check）
            min_row_count: 最少要求行數（用於 master completeness check）
            **kwargs: 其他自訂參數
        """
        self.expected_dates = expected_dates
        self.expected_symbols = expected_symbols
        self.min_row_count = min_row_count
        self.custom_params = kwargs
```

然後在 rule checker 中檢查參數是否存在：

```python
def check_completeness_row_count(records: List[Dict], expected_dates=None, **kwargs):
    if expected_dates is None:
        # 參數未提供，skip 此 rule
        return None, "Skipped (expected_dates not provided)"
    
    # 正常檢查
    expected_count = len(expected_dates) * len(set(r.get("symbol") for r in records))
    actual_count = len(records)
    if actual_count == expected_count:
        return True, f"Row count correct: {actual_count}"
    else:
        return False, f"Expected {expected_count} rows, got {actual_count}"
```

### 處理 Skip 的 Rule

若某些 rule 因參數缺失而 skip，應在 report 中明確標記：

```python
def _execute_rule(self, rule: ValidationRule) -> RuleResult:
    try:
        passed, detail = rule.checker_fn(self.records, **self.kwargs)
        if passed is None:  # Skip
            return RuleResult(
                rule_id=rule.rule_id,
                status="SKIPPED",
                detail=detail,
                count=0
            )
        return RuleResult(...)
    except Exception as e:
        return RuleResult(...)
```

---

## 4. 大數據集下的效能優化

### 問題：若爬取全市場資料呢？

假設爬蟲參數：
- symbols: 2000+
- trading_days: 250 / year
- rows: 2000 × 250 = 500k+

### 瓶頸分析

1. **Rule 執行順序**：
   - 快速 rule（structure, format）應先執行，快速 fail
   - 耗 CPU rule（uniqueness, consistency）應後執行

2. **記憶體**：
   - 500k rows 的 dict list 可能佔 100+ MB
   - 應考慮使用生成器或流式處理

3. **I/O**：
   - 寫 500k 行 JSON report 可能較慢
   - 應考慮壓縮或分片存儲

### 優化建議（非 Phase 2 強制實作）

1. **分批驗證**：
   ```python
   for batch in chunked(records, batch_size=10000):
       report_batch = validator.run_batch(batch)
       reports.append(report_batch)
   ```

2. **抽樣驗證**：
   ```python
   sample_records = random.sample(records, min(10000, len(records)))
   report = validator.run(sample_records)
   ```

3. **並行驗證**（若有多個 rule checker）：
   ```python
   from concurrent.futures import ThreadPoolExecutor
   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(rule_checker, records) for rule_checker in rules]
       results = [f.result() for f in futures]
   ```

**當前建議**：
- Phase 2 先不優化，使用簡單 O(n) 或 O(n log n) 實作
- 若實際運行時遇到性能問題，再考慮上述優化

---

## 5. JSON Report 的版本化與向後相容性

### 問題：若 rule 定義改變，舊 report 如何解析？

Report JSON 結構可能隨著 rule 演進而變化。

### 建議方案

在 report 中添加 version 欄：

```json
{
  "version": "1.0",
  "schema_version": 1,
  "table_name": "stock_daily",
  "...": "..."
}
```

在 report reader 中檢查版本：

```python
def load_report(filepath: str) -> ValidationReport:
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    if data.get("schema_version") != CURRENT_SCHEMA_VERSION:
        logger.warning(f"Report schema v{data['schema_version']} may not be fully compatible")
    
    return ValidationReport.from_dict(data)
```

### 預計的版本演進

- v1.0: 初版（20 個 rules，無異常偵測）
- v1.1: 加入 anomaly detection rules（可回向相容）
- v2.0: 添加歷史數據與時間序列相關 rules（可能破壞相容性）

---

## 6. Error Handling 與日誌策略

### 問題：如何平衡詳細日誌與簡潔輸出？

#### 日誌等級使用建議

| 等級 | 用途 | 範例 |
|------|------|------|
| DEBUG | 最詳細的執行過程 | `Rule stock_daily_value_price_positive checking record[42]...` |
| INFO | 高層次進度 | `Validating stock_daily... (63 records)` |
| WARNING | 潛在問題但不阻斷 | `5 records have price change > 10%` |
| ERROR | 驗證失敗 | `Rule failed: completeness_row_count - expected 65, got 60` |
| CRITICAL | 系統異常 | `Validator crashed: out of memory` |

#### 實作建議

```python
logger = logging.getLogger(__name__)

# 在 DataValidator 中
def run(self):
    logger.debug(f"Starting validation for {self.table_name} with {len(self.records)} records")
    
    for rule in self.rules:
        logger.debug(f"  Executing rule {rule.rule_id}...")
        try:
            result = self._execute_rule(rule)
            if result.status == "PASS":
                logger.debug(f"    ✓ {rule.rule_id} PASSED")
            elif result.status == "FAIL":
                logger.error(f"    ✗ {rule.rule_id} FAILED: {result.detail}")
            else:  # WARNING
                logger.warning(f"    ⚠ {rule.rule_id} WARNING: {result.detail}")
        except Exception as e:
            logger.error(f"    ✗ {rule.rule_id} ERROR: {str(e)}")
```

---

## 7. 關於 Validator 與 Cleaner 的協作

### 問題：Validator 標記「NOT_FOUND」vs Cleaner 實際執行

當 stock_daily 中的某個 symbol 不在 stock_master 中時：

- **Validator** 會檢查並產生 `consistency_symbol_in_master` FAILED rule
- **Cleaner** 會執行 SQL 查詢並產生 `master_check = 'NOT_FOUND'` 標記

### 設計原則

**Validator 與 Cleaner 的職責不重疊**：
- **Validator**：檢查數據是否符合預期（可以在 memory 中完成，不涉及 DB）
- **Cleaner**：在 DB 中進行實際的 enrichment 與標記（原地 UPDATE）

### 如果都失敗會怎樣？

假設 validator 檢查失敗（symbol 不在 expected_symbols 中），但用戶用 `--force` 強制繼續：

1. Validator report 中 `consistency_symbol_in_master` = FAILED
2. 數據仍寫入 DB
3. Cleaner 執行，也會在 master_check = NOT_FOUND
4. 最終結果相同，但多了一份驗證記錄

### 建議

**不需特殊處理兩者重複檢查的情況**：
- 這是設計的一部分（layered validation）
- Validator 作為「第一層防線」，Cleaner 作為「最終確認」
- 若 Validator 通過但 Cleaner 發現問題，說明有邏輯漏洞（應改進 rule）

---

## 8. 測試資料的生命週期管理

### 問題：Mock 資料如何維護？

測試資料存放在 `tests/test_data/validation/`，如：
- normal_stock_daily.json
- missing_dates_stock_daily.json
- expected_report_normal.json

### 維護策略

1. **與 Item Schema 同步**：
   - 若 `StockDailyItem` 添加新欄位，test data 也要更新
   - 建議在 CI 中加入「schema validation」檢查

2. **定期從真實數據更新**：
   - 每個月抽取一次真實爬蟲結果（after cleaner）
   - 提取 5-10 筆「正常」與「異常」範例
   - 更新到 test_data 中

3. **版本化 test data**：
   ```
   tests/test_data/validation/
   ├── v1.0/
   │   ├── normal_stock_daily.json
   │   └── ...
   ├── v2.0/
   │   ├── normal_stock_daily.json
   │   └── ...
   └── latest -> v2.0
   ```

### 建議

- 第一版先手工編寫簡單 mock data（5-10 筆 records）
- 待系統穩定後，可考慮自動化更新機制

---

## 9. Validator 與 Spider 的解耦

### 問題：Validator 依賴 Spider 產生 raw records？

目前設計中，validator 必須在 spider 完成後才能運行：

```
Spider.fetch() → capture raw → Validator.run() → Report
```

### 思考：能否獨立運行 Validator？

**是的，可以**。Validator 只要傳入 `records` list 與可選參數，就能獨立執行：

```python
# 可以直接從檔案或 DB 讀取 records，繞過 spider
with open("data/stock_daily_2026-04.json") as f:
    records = json.load(f)

validator = DataValidator("stock_daily", records)
report = validator.run()
```

### 應用場景

1. **事後驗證**：若發現某天的爬蟲結果有問題，可重新執行 validator
2. **批量驗證**：驗證整個月/年的數據
3. **持續監控**：定期驗證 DB 中的現有數據

### 建議

- 設計時已支援這種解耦
- 將 validator 視為一個「獨立工具」，可被 spider、cleaner、或外部流程使用

---

## 10. 關於 Trading Calendar 的擴展

### 問題：未來如何支援更複雜的假日規則？

當前實作：簡單的 dict 映射（年份 → 假日清單）

### 未來擴展方向

1. **Config 檔案化**：
   ```yaml
   # configs/holidays.yaml
   2026:
     fixed_holidays:
       - date: "01-01"
         name: "New Year"
       - date: "02-28"
         name: "Peace Memorial Day"
     lunar_holidays:
       - lunar_month: 5
         lunar_day: 5
         name: "Dragon Boat Festival"
       - lunar_month: 8
         lunar_day: 15
         name: "Mid-Autumn Festival"
     makeup_days:
       - date: "2026-04-25"
         reason: "makeup for 04-04"
   ```

2. **與外部 API 同步**：
   ```python
   def sync_from_government_api():
       # 每年初從勞動部 API 獲取最新假日
       pass
   ```

3. **支援多國市場**：
   ```python
   calendar_tw = TradingCalendar(market="TW")
   calendar_us = TradingCalendar(market="US")
   ```

### 當前建議

- Phase 2 先保持簡單（dict 方式）
- 在代碼中預留擴展點（如 load_holidays() 方法）
- 若未來需要，可在 Phase 3 升級

---

## 11. 報表可視化（未來考慮）

### 概念：生成 HTML 報告而非只有 JSON

```html
<!-- validation_report_2026-04-30.html -->
<html>
  <head>
    <title>Validation Report - 2026-04-30</title>
  </head>
  <body>
    <h1>Validation Summary</h1>
    <table>
      <tr><th>Table</th><th>Rules</th><th>Passed</th><th>Failed</th><th>Warnings</th></tr>
      <tr><td>stock_daily</td><td>7</td><td>7</td><td>0</td><td>0</td></tr>
      ...
    </table>
    
    <h2>Detailed Rules</h2>
    <section id="stock_daily">
      <h3>stock_daily</h3>
      <ul>
        <li><span class="pass">✓</span> structure_required_fields: All required fields present</li>
        ...
      </ul>
    </section>
  </body>
</html>
```

### 建議

- Phase 2 不實作（focus on core validator）
- 若需要，可在 Phase 3 或後續作為「可視化增強」

---

## 12. 版本控制與 Changelog

### 建議文檔維護

**在本目錄下保留 CHANGELOG.md**：

```markdown
# Validation Layer Changelog

## [1.0] - 2026-04-30
### Added
- Core validator with 20 rules
- Support for 4 data types (stock_master, stock_daily, cb_master, tpex_cb_daily)
- CLI flags: --validate-only, --force-validation, --skip-validation
- JSON report generation
- Trading calendar module

### Known Limitations
- Trading calendar hard-coded (no API)
- No performance optimization for large datasets (>500k rows)
- No database persistence of validation logs

## [1.1] - TBD
### Planned
- Anomaly detection rules (deviation from historical average)
- Database logging of validation results
- HTML report generation
- Performance optimization for large datasets
```

---

## 快速參考

### 常見錯誤與解決方案

| 錯誤 | 原因 | 解決方案 |
|------|------|--------|
| `expected_dates is None` | 未傳入交易日曆 | 在 DataValidator 初始化時提供 expected_dates |
| `symbol not found in master` | 日行情中的 symbol 在主檔找不到 | 檢查主檔爬蟲是否成功，或使用 --force-validation |
| `row count mismatch` | 爬取的日期不完整 | 檢查交易日曆規則，或提供 expected_dates 參數 |
| `JSON report not generated` | report_writer 異常 | 檢查 logs/validation/ 目錄權限 |
| `OOM (out of memory)` | 資料集太大 | 考慮分批驗證或抽樣檢查 |

---

**版本控制**
- v1.0 (2026-04-30): 初版實作注意事項
