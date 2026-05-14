# Validation Rules 詳細規範

本文件列出四種資料類型各自的完整 rule catalog，包括檢查邏輯、通過/失敗標準、與實作建議。

---

## Pipeline 整合說明

### 規則在 pipeline 中的執行位置

```
Step 1: 爬蟲 (step_spiders)
  spider.fetch_*()
    → pipeline.save_items(item)      ← 寫入 DB
    → spider.get_items() → to_dict() ← 收集 records
  ↓
Step 2: 驗證 (step_validate)
  DataValidator(table_name, records, ...).run()
    → 自動載入對應的 rules（依 table_name）
    → 自動注入 cross-table 參數（symbols, cb_codes）
    → 逐條執行所有 rules
    → 回傳 ValidationReport
  ↓
  report.has_errors() ?
    → Yes: exit(1)（預設）/ --force-validation 繼續
    → No:  繼續到 Step 3 清洗
```

### 規則對應關係

| table_name | 規則數 | 載入來源 |
|------------|--------|----------|
| `stock_master` | 6 | `stock_master_rules.STOCK_MASTER_RULES` |
| `stock_daily` | 7 | `stock_daily_rules.STOCK_DAILY_RULES` |
| `cb_master` | 5 | `cb_master_rules.CB_MASTER_RULES` |
| `tpex_cb_daily` | 6 | `tpex_cb_daily_rules.TPEX_CB_DAILY_RULES` |

### Cross-table 參數注入

DataValidator 執行時，`step_validate()` 會自動從 `collected_records` 提取：

```python
# stock_daily 驗證時注入 master symbols
master_symbols = [r["symbol"] for r in collected_records["stock_master"]]
DataValidator("stock_daily", records, expected_symbols=master_symbols)

# tpex_cb_daily 驗證時注入 master cb_codes
master_cb_codes = [r["cb_code"] for r in collected_records["cb_master"]]
DataValidator("tpex_cb_daily", records, expected_cb_codes=master_cb_codes)
```

這使得 `consistency_symbol_in_master` 和 `consistency_cb_code_in_master` 兩條規則能實際比對跨表資料。

---

## Rule 設計原則

1. **唯一性**：rule_id 全局唯一（ex: `table_name_rule_purpose`）
2. **正交性**：各 rule 檢查不同的維度，盡量避免重複
3. **獨立性**：一條 rule 失敗不影響其他 rule 的執行
4. **可測試性**：每條 rule 都應有明確的通過/失敗範例
5. **可調優**：rule 參數化，允許注入 expected_dates、expected_symbols 等

---

## 1. stock_master Rules

### Rule 1.1：structure_required_fields
- **ID**: `stock_master_structure_required_fields`
- **Severity**: ERROR
- **描述**: 檢查是否包含所有必要欄位
- **必要欄位**: symbol, name, market_type, industry
- **邏輯**:
  - 若任何必要欄位在所有 records 中都缺失 → FAIL
  - 若某筆 record 缺少必要欄位 → FAIL（記錄哪些 record）
  - 否則 → PASS
- **通過範例**:
  ```json
  [
    {"symbol": "2330", "name": "台積電", "market_type": "TWSE", "industry": "半導體"},
    {"symbol": "2454", "name": "聯發科", "market_type": "TWSE", "industry": "半導體"}
  ]
  ```
- **失敗範例**:
  ```json
  [
    {"symbol": "2330", "name": "台積電"}  // 缺 market_type, industry
  ]
  ```

### Rule 1.2：uniqueness_symbol
- **ID**: `stock_master_uniqueness_symbol`
- **Severity**: ERROR
- **描述**: symbol 不重複
- **邏輯**:
  - 計算 unique symbol 數 vs 總 records 數
  - 若不相等 → FAIL，記錄重複的 symbol
  - 否則 → PASS
- **通過範例**: 1000 unique symbols, 1000 records
- **失敗範例**: 1000 unique symbols, 1001 records (某個 symbol 重複)

### Rule 1.3：value_market_type
- **ID**: `stock_master_value_market_type`
- **Severity**: ERROR
- **描述**: market_type 只能是 "TWSE" 或 "TPEx"
- **邏輯**:
  - 遍歷所有 records，檢查 market_type ∈ {TWSE, TPEx}
  - 若有不符 → FAIL，列出異常值
  - 否則 → PASS
- **通過範例**: 所有 market_type 都是 "TWSE" 或 "TPEx"
- **失敗範例**: 某筆 record market_type = "NYSE"

### Rule 1.4：completeness_twse_coverage
- **ID**: `stock_master_completeness_twse_coverage`
- **Severity**: WARNING
- **描述**: TWSE 回傳應有最少 1500 rows
- **邏輯**:
  - 計算 market_type == "TWSE" 的 records 數
  - 若 < 1500 → WARNING
  - 否則 → PASS
- **備註**: 警告但不阻斷，因為 TWSE 上市公司數可能波動
- **通過範例**: 1800 rows (TWSE)
- **失敗（警告）範例**: 500 rows (TWSE)

### Rule 1.5：completeness_tpex_coverage
- **ID**: `stock_master_completeness_tpex_coverage`
- **Severity**: WARNING
- **描述**: TPEx 回傳應有最少 800 rows
- **邏輯**:
  - 計算 market_type == "TPEx" 的 records 數
  - 若 < 800 → WARNING
  - 否則 → PASS
- **備註**: 同樣為警告
- **通過範例**: 1000 rows (TPEx)
- **失敗（警告）範例**: 200 rows (TPEx)

### Rule 1.6：value_industry_not_empty
- **ID**: `stock_master_value_industry_not_empty`
- **Severity**: WARNING
- **描述**: industry 欄位應非空
- **邏輯**:
  - 計算有多少 records 的 industry 為空/NULL/""/None
  - 若超過 5% → WARNING
  - 否則 → PASS
- **通過範例**: < 5% 的 industry 為空
- **失敗（警告）範例**: 10% 的 industry 為空

---

## 2. stock_daily Rules

### Rule 2.1：structure_required_fields
- **ID**: `stock_daily_structure_required_fields`
- **Severity**: ERROR
- **描述**: 檢查必要欄位
- **必要欄位**: symbol, date, close_price, volume
- **邏輯**: 同 stock_master_structure_required_fields
- **通過範例**:
  ```json
  [
    {"symbol": "2330", "date": "2026-04-01", "close_price": 850.5, "volume": 10000}
  ]
  ```
- **失敗範例**: 缺少任何必要欄位

### Rule 2.2：value_price_positive
- **ID**: `stock_daily_value_price_positive`
- **Severity**: ERROR
- **描述**: close_price 必須 > 0
- **邏輯**:
  - 遍歷所有 records，檢查 close_price > 0
  - 若有 <= 0 → FAIL，列出異常 rows
  - 否則 → PASS
- **通過範例**: 所有 close_price > 0
- **失敗範例**: close_price = 0 或 -10.5

### Rule 2.3：value_volume_non_negative
- **ID**: `stock_daily_value_volume_non_negative`
- **Severity**: ERROR
- **描述**: volume 必須 >= 0
- **邏輯**:
  - 遍歷所有 records，檢查 volume >= 0
  - 若有 < 0 → FAIL
  - 否則 → PASS
- **備註**: volume = 0 是允許的（停牌日或無交易日）
- **通過範例**: 所有 volume >= 0
- **失敗範例**: volume = -100

### Rule 2.4：completeness_row_count
- **ID**: `stock_daily_completeness_row_count`
- **Severity**: ERROR
- **描述**: 行數應等於 expected_dates × unique_symbols
- **邏輯**:
  - 參數: expected_dates (交易日曆清單)
  - 計算 unique symbols 數
  - 預期行數 = len(expected_dates) × len(unique_symbols)
  - 若 actual_rows != expected_rows → FAIL
  - 否則 → PASS
- **備註**: 若 expected_dates 未提供，則 skip 此 rule
- **通過範例**:
  - expected_dates = ["2026-04-01", "2026-04-02", ..., "2026-04-30"] (21 trading days)
  - symbols = ["2330", "2454", "3008"] (3 symbols)
  - actual rows = 63 → PASS
- **失敗範例**: actual rows = 60 (缺少 3 rows)

### Rule 2.5：consistency_symbol_in_master
- **ID**: `stock_daily_consistency_symbol_in_master`
- **Severity**: ERROR
- **描述**: 所有 symbol 都應在 stock_master 中存在
- **邏輯**:
  - 參數: expected_symbols (或從上一步 master 驗證得到)
  - 收集 stock_daily 中所有 unique symbols
  - 檢查是否都在 master 中
  - 若有 symbol 不在 → FAIL，列出缺失的 symbol
  - 否則 → PASS
- **備註**: 若 expected_symbols 未提供，則 skip 此 rule（或回傳 WARNING）
- **通過範例**: stock_daily 的所有 symbol 都在 stock_master 中
- **失敗範例**: stock_daily 包含 symbol = "9999"（不在 master 中）

### Rule 2.6：format_date
- **ID**: `stock_daily_format_date`
- **Severity**: ERROR
- **描述**: date 格式應為 YYYY-MM-DD
- **邏輯**:
  - 遍歷所有 records，檢查 date 是否符合 YYYY-MM-DD 格式
  - 若有不符 → FAIL
  - 否則 → PASS
- **通過範例**: "2026-04-01"
- **失敗範例**: "2026/04/01"、"04-01-2026"、"2026-4-1"

### Rule 2.7：value_price_range_warning
- **ID**: `stock_daily_value_price_range_warning`
- **Severity**: WARNING
- **描述**: 單日漲跌幅 > 10% 的記錄應被標記
- **邏輯**:
  - 計算 price_change（若有該欄位）或 (close_price - open_price) / open_price
  - 若 |change| > 0.10 → WARNING（但不 FAIL）
  - 計算並報告有多少 records 超過此閾值
- **通過範例**: 無超過 10% 漲跌幅的 records
- **失敗（警告）範例**: 5 records 超過 10% 漲跌幅

---

## 3. cb_master Rules

### Rule 3.1：structure_required_fields
- **ID**: `cb_master_structure_required_fields`
- **Severity**: ERROR
- **描述**: 檢查必要欄位
- **必要欄位**: cb_code, cb_name, conversion_price
- **邏輯**: 同前述
- **通過範例**:
  ```json
  [
    {"cb_code": "2330A", "cb_name": "台積電轉債", "conversion_price": 50.0}
  ]
  ```

### Rule 3.2：uniqueness_cb_code
- **ID**: `cb_master_uniqueness_cb_code`
- **Severity**: ERROR
- **描述**: cb_code 不重複
- **邏輯**: 同 symbol 不重複檢查
- **通過範例**: 100 unique cb_codes, 100 records
- **失敗範例**: 100 unique cb_codes, 101 records

### Rule 3.3：value_conversion_price_positive
- **ID**: `cb_master_value_conversion_price_positive`
- **Severity**: ERROR
- **描述**: conversion_price 必須 > 0
- **邏輯**:
  - 遍歷所有 records，檢查 conversion_price > 0
  - 若有 <= 0 → FAIL
  - 否則 → PASS
- **通過範例**: 所有 conversion_price > 0
- **失敗範例**: conversion_price = 0

### Rule 3.4：completeness_min_rows
- **ID**: `cb_master_completeness_min_rows`
- **Severity**: WARNING
- **描述**: 至少應有 10 rows
- **邏輯**:
  - 若 row count < 10 → WARNING
  - 否則 → PASS
- **備註**: master 資料量相對小，只做最小檢查
- **通過範例**: 150 rows
- **失敗（警告）範例**: 5 rows

### Rule 3.5：value_cb_name_not_empty
- **ID**: `cb_master_value_cb_name_not_empty`
- **Severity**: WARNING
- **描述**: cb_name 應非空
- **邏輯**:
  - 計算多少 records 的 cb_name 為空
  - 若 > 0 → WARNING
  - 否則 → PASS
- **通過範例**: 所有 cb_name 非空
- **失敗（警告）範例**: 某筆 cb_name 為空

---

## 4. tpex_cb_daily Rules

### Rule 4.1：structure_required_fields
- **ID**: `tpex_cb_daily_structure_required_fields`
- **Severity**: ERROR
- **描述**: 檢查必要欄位
- **必要欄位**: cb_code, trade_date, closing_price
- **邏輯**: 同前述
- **通過範例**:
  ```json
  [
    {"cb_code": "2330A", "trade_date": "2026-04-01", "closing_price": 50.5}
  ]
  ```

### Rule 4.2：value_price_positive
- **ID**: `tpex_cb_daily_value_price_positive`
- **Severity**: WARNING (was ERROR — changed 2026-04-30: 0 是未交易日正常值)
- **描述**: closing_price 應 > 0，但 0 是未交易日正常值
- **邏輯**: 同 stock_daily 的 price check，但僅 WARNING 不阻斷
- **通過範例**: 所有 closing_price > 0
- **失敗（警告）範例**: closing_price = 0（非交易日）

### Rule 4.3：value_volume_non_negative
- **ID**: `tpex_cb_daily_value_volume_non_negative`
- **Severity**: ERROR
- **描述**: volume 必須 >= 0
- **邏輯**: 同前述
- **通過範例**: 所有 volume >= 0
- **失敗範例**: volume < 0

### Rule 4.4：consistency_cb_code_in_master
- **ID**: `tpex_cb_daily_consistency_cb_code_in_master`
- **Severity**: ERROR
- **描述**: 所有 cb_code 都應在 cb_master 中存在
- **邏輯**:
  - 參數: expected_cb_codes (從 cb_master 驗證得到)
  - 檢查 tpex_cb_daily 中的所有 cb_code 是否都在 master 中
  - 若有不在 → FAIL，列出缺失的 cb_code
  - 否則 → PASS
- **通過範例**: tpex_cb_daily 的所有 cb_code 都在 cb_master 中
- **失敗範例**: tpex_cb_daily 包含 cb_code = "INVALID" (不在 master 中)

### Rule 4.5：format_date
- **ID**: `tpex_cb_daily_format_date`
- **Severity**: ERROR
- **描述**: trade_date 格式應為 YYYY-MM-DD
- **邏輯**: 同 stock_daily 的 date format check
- **通過範例**: "2026-04-01"
- **失敗範例**: "2026/04/01"

### Rule 4.6：completeness_at_least_one_record
- **ID**: `tpex_cb_daily_completeness_at_least_one_record`
- **Severity**: WARNING
- **描述**: 至少應有 1 筆交易紀錄
- **邏輯**:
  - 若 row count = 0 → WARNING
  - 若 row count > 0 → PASS
- **備註**: 某些日期（如假日）可能沒有 CB 交易，所以只 WARNING
- **通過範例**: > 0 rows
- **失敗（警告）範例**: 0 rows

---

## Rule 執行順序建議

為了提高效率，建議以下執行順序（對於每個 table）：

1. **Structure checks first** (快速失敗)
   - structure_required_fields
   - format_* checks
2. **Value checks** (檢查數據正確性)
   - value_* checks
3. **Uniqueness checks** (較耗 CPU)
   - uniqueness_* checks
4. **Completeness checks** (可能涉及參數注入)
   - completeness_* checks
5. **Consistency checks** (涉及跨 table 比較)
   - consistency_* checks
6. **Anomaly / Warning checks** (最後階段)
   - 各 warning level rules

---

## 測試資料範例

### 正常的 stock_daily 資料
```json
[
  {
    "symbol": "2330",
    "date": "2026-04-01",
    "open_price": 840.0,
    "high_price": 860.0,
    "low_price": 835.0,
    "close_price": 850.0,
    "volume": 12345,
    "turnover_rate": 5.5,
    "price_change": 10.0,
    "transaction_count": 500
  },
  {
    "symbol": "2330",
    "date": "2026-04-02",
    "open_price": 850.0,
    "high_price": 865.0,
    "low_price": 848.0,
    "close_price": 860.0,
    "volume": 11000,
    "turnover_rate": 5.2,
    "price_change": 10.0,
    "transaction_count": 480
  }
]
```

### 異常的 stock_daily 資料（缺日期）
```json
[
  {
    "symbol": "2330",
    "date": "2026-04-01",
    "close_price": 850.0,
    "volume": 12345
  }
  // 缺少 2026-04-02
]
```

### 異常的 stock_daily 資料（0 元）
```json
[
  {
    "symbol": "2330",
    "date": "2026-04-01",
    "close_price": 0,  // ← 異常
    "volume": 12345
  }
]
```

---

## 版本控制 & 更新

- v1.0 (2026-04-30): 初版 20 條 rules
- 未來可追加 anomaly detection rules（如 deviation > 3σ 等）
