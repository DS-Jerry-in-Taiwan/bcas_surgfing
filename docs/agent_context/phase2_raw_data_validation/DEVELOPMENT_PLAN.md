# Phase 2: Raw Data Validation 開發規劃文件

**版本**: 1.0  
**日期**: 2026-04-30  
**狀態**: Development Plan  
**負責**: Architecture & Development Team

---

## 概述

本文件規劃 **Raw Data Validation Layer** 的完整開發流程。  
目的在於「Spider/Parser 爬完原始資料、寫入 DB 前」，自動驗證資料是否符合預期的**結構、完整性與合理性**。

此 layer 屬於 **Phase 2（Data Quality Assurance）**，是在 Phase 1（爬蟲→DB 存儲）之後的關鍵品質控制點。

---

## 整體設計哲學

### 三層驗證架構（新舊對照）

| 現況（Phase 1）| 新增（Phase 2）| 功能 |
|-------------|--------------|------|
| Spider → Parser | ⬆️ **Validator** ← | 格式轉換、型態清理 |
| Pipeline → DB | ⬆️ **Checkpoint** ← | 結構、完整性、值域檢查 |
| Cleaner → Update | ⬆️ **Report** ← | 記錄驗證結果 |

### 檢查不做什麼
- ❌ 不檢查資料內容是否與真實世界一致（需 ground truth）
- ❌ 不做跨期趨勢分析或歷史偏差偵測（anomaly detection 階段的事）
- ❌ 不修改原始資料（read-only）
- ❌ 不依賴外部 API（except 通過環境變數注入）
- ❌ 不操作 DB（validator 解耦於 persist）

### 檢查要做什麼
- ✅ 回傳的欄位數、名稱、必要欄位是否齊全
- ✅ 各欄位型態是否可解析（price 必須 > 0、volume >= 0 等）
- ✅ 爬取日期範圍是否符合預期（相較於交易日曆）
- ✅ Symbol/CB Code 等關鍵欄位是否有缺漏
- ✅ 與 master 表的一致性（daily 中的 symbol 是否都在 stock_master 中有對應）

---

## 核心檢查維度（5D）

### 1. **完整性 (Completeness)**
- **daily 類資料**：指定爬取區間（ex. 2026-01-01 ~ 2026-04-30）的交易日數應該等於回傳 row count
  - 預期筆數 = 交易日曆.get_trading_days(year, month) × symbol 數
  - 若某些 symbol 無交易（停牌、退市等），應有異常記錄而非無聲遺漏
- **master 類資料**：應涵蓋所有已上市/上櫃公司（TWSE 全市場 + TPEx 全市場）
  - symbol 不重複、不缺漏

### 2. **結構性 (Structure)**
- 欄位數量、順序、名稱符合預期
- 必要欄位（如 symbol, date, close_price）不可為 NULL
- 型態可被正確解析（date 格式、price 為浮點、volume 為整數）

### 3. **值域合理性 (Reasonability)**
- price > 0（股票不存在 0 元或負數）
- volume >= 0（成交量不能為負）
- price_change ∈ [-999, 999]（漲跌幅限制，防極端異常值）
- transaction_count >= 0

### 4. **一致性 (Consistency)**
- **Daily vs Master**: stock_daily 中的 symbol 必須都在 stock_master 中存在（外鍵約束）
- **CB Daily vs CB Master**: tpex_cb_daily 中的 cb_code 必須都在 cb_master 中存在
- **日期一致**: trade_date / date 應在要求的日期範圍內

### 5. **異常偵測 (Anomaly)**
- 單日漲跌幅 > 10% → 標記為「可疑但可接受」（需人工確認但不阻斷）
- 全 0 row（全天無交易）→ 警告但允許
- 極端值（price > 10倍 daily average）→ 記錄詳情
- **第一階段暫不強制實作，設計上應支援擴展**

---

## 四種資料類型的預期

| 資料類型 | 資料來源 | 爬取頻率 | 行數預期 | 關鍵欄位 |
|---------|---------|---------|---------|---------|
| **stock_master** | TWSE HTML | 每月一次（或每年 9 月）| ~2,000 rows | symbol, name, market_type |
| **stock_daily** | TWSE JSON API | 每日下午 3 時後 | N_symbol × N_trading_days | symbol, date, close_price, volume |
| **cb_master** | TPEx CSV | 每月或每週 | ~200 rows | cb_code, cb_name, conversion_price |
| **tpex_cb_daily** | TPEx CSV | 每日下午 5 時後 | N_cb_code × (交易天數) | cb_code, trade_date, closing_price, volume |

---

## 使用者視角

### 正常流程（Pass 的情況）
```bash
$ python src/run_daily.py
...
[INFO] ValidationReport for stock_master: 8 rules PASSED
[INFO] ValidationReport for stock_daily: 7 rules PASSED, 1 rule WARNING
[INFO] ValidationReport for cb_master: 8 rules PASSED
[INFO] ValidationReport for tpex_cb_daily: 7 rules PASSED, 1 rule WARNING
[INFO] All validations PASSED, proceeding to DB write...
[INFO] Wrote 1,234 rows to stock_daily
[INFO] Running cleaner...
✅ Pipeline complete.
```

### 有異常的流程（Fail 的情況，預設中止）
```bash
$ python src/run_daily.py
...
[ERROR] ValidationReport for stock_daily: 1 rule FAILED
  - Rule: completeness_row_count - Expected 65 rows, got 60 rows for symbol=2330
[ERROR] Validation FAILED. Aborting pipeline.
❌ Exit code 1

# 查看詳細報告
$ cat logs/validation/2026-04-30_150230_stock_daily.json
```

### 強制繼續（override）
```bash
$ python src/run_daily.py --force-validation
...
[WARNING] ValidationReport has errors, but --force-validation is set. Proceeding...
[INFO] Wrote 1,234 rows to stock_daily (incomplete data)
⚠️ Pipeline proceeded with caveats.
```

### 驗證模式（不寫 DB）
```bash
$ python src/run_daily.py --validate-only
...
[INFO] Validation complete. No data written to DB.
$ ls logs/validation/
  2026-04-30_150230_stock_master.json
  2026-04-30_150230_stock_daily.json
  2026-04-30_150230_cb_master.json
  2026-04-30_150230_tpex_cb_daily.json
  2026-04-30_150230_summary.json
```

---

## 成功標準 & 測試通過指標

### 第一階段（Validator Core 完成）

**標準**：
- 四種 table 各自定義 5+ 條 rules
- `DataValidator` class 可吃 raw records list，回傳 `ValidationReport`
- 交易日曆模組能正確回傳交易日期清單
- Unit test 覆蓋率 >= 85%

**通過指標**：
```bash
pytest tests/test_framework/test_validator_core.py -v
# 預期：全部 PASS，無 skipped/failed
# 覆蓋項目：rules 定義、checker core、calendar module
```

### 第二階段（Pipeline 整合完成）

**標準**：
- `run_daily.py` 支援 `--validate-only` 與 `--force-validation` flags
- Validation report 正確產出 JSON 到 `logs/validation/`
- 正常流程（validate pass → write → cleaner）可完整打通

**通過指標**：
```bash
# Scenario 1: 正常資料，整條 pipeline
python src/run_daily.py
# 預期：logs/validation/ 下有 4 個 table report + 1 個 summary

# Scenario 2: validate-only 不寫 DB
python src/run_daily.py --validate-only
# 預期：DB 無新資料，但有 report 檔案

# Scenario 3: 刻意注入異常資料，force 繼續
pytest tests/test_framework/test_validation.py::test_force_validation_write_incomplete_data -v
# 預期：PASS，DB 有不完整資料但 validation report 有標記
```

### 第三階段（整合驗證完成）

**標準**：
- 所有 test case 涵蓋正常/異常/邊界情境
- 可重現 validation 對 pipeline 的「阻斷」或「放行」行為
- 交易日曆的可追蹤性與準確度被驗證

**通過指標**：
```bash
pytest tests/test_framework/test_validation.py -v
# 預期：100% PASS
# 至少包含：
#   - 3+ 個正常情境 test
#   - 3+ 個異常/邊界 test
#   - 交易日曆與預期 row count 一致的 test

pytest tests/test_framework/test_trading_calendar.py -v
# 預期：100% PASS
#   - 已知月份（ex. 2026-01）回傳正確交易日
#   - 國定假日被正確排除
```

---

## 文件與交付物清單

完成時應產出以下文件：

### 規劃文檔（你正在讀的）
- [ ] `DEVELOPMENT_PLAN.md` — 本文件
- [ ] `STAGE_BREAKDOWN.md` — 每個階段的詳細步驟與驗收標準
- [ ] `VALIDATION_RULES.md` — 四種 table 的完整 rule catalog
- [ ] `INTEGRATION_GUIDE.md` — 如何整合進 `run_daily.py`
- [ ] `BOUNDARIES_AND_CONSTRAINTS.md` — 邊界與禁止事項
- [ ] `IMPLEMENTATION_NOTES.md` — 實作細節、陷阱、建議

### 程式碼（待開發）
- [ ] `src/validators/rules.py` — `ValidationRule` dataclass
- [ ] `src/validators/checker.py` — `DataValidator` class
- [ ] `src/validators/report.py` — `ValidationReport` dataclass
- [ ] `src/validators/report_writer.py` — JSON report writer
- [ ] `src/validators/{table}_rules.py` × 4 — 各 table 的 rules 定義
- [ ] `src/utils/trading_calendar.py` — 交易日曆模組
- [ ] `tests/test_framework/test_validation.py` — 整合測試
- [ ] `tests/test_data/validation/` — Mock 測試資料（JSON）

### 文檔示例與參考
- [ ] `docs/validation/rule_catalog.md` — Rules 完整說明與示例
- [ ] `docs/validation/report_example.json` — Report JSON 範例
- [ ] `tests/test_data/validation/normal_*.json` — 正常資料範例
- [ ] `tests/test_data/validation/expected_*.json` — 預期檢查結果

---

## 實作時間規劃（建議）

| 週次 | 工作項目 | 預估時間 | 負責人 |
|------|---------|---------|-------|
| W1 | Stage 1~2: Rules 定義 + Checker core | 3 days | Dev |
| W1-2 | Stage 3: Trading calendar + Report writer | 2 days | Dev |
| W2 | Stage 4: Pipeline 整合 | 2 days | Dev |
| W2-3 | Stage 6: 整合測試 | 3 days | QA + Dev |
| W3 | 文件編寫、sample 產出 | 1 day | Doc |
| W3 | 回歸測試、上線準備 | 1 day | QA |

**總計**：~3 週

---

## 下一步

1. **確認本規劃是否有異議？**
   - 是否需要調整檢查維度或 rules？
   - 是否需要額外的 edge cases？

2. **準備進入 Stage 1？**
   - 開始定義四種 table 的 rules
   - 建立 `src/validators/` 目錄結構

3. **測試資料維護計畫**
   - 從真實爬蟲結果中提取「正常」與「異常」範例
   - 或先用 mock 資料驗證 validator 邏輯

---

**版本控制**  
- v1.0 (2026-04-30): 初版規劃
