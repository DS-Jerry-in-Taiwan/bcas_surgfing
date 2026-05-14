# Phase 2 Raw Data Validation — 開發完成報告

**日期**：2026-04-30  
**狀態**: ✅ Stage 1-5 全部完成  
**測試**: 119/119 PASS（另有 1 個 pre-existing 外部測試失敗）  
**總規則數**: 24 條（ERROR 19 / WARNING 5）

---

## 已交付成果

| 階段 | 狀態 | 測試 | 核心產出 |
|------|------|------|----------|
| **Stage 1: 驗證規則** | ✅ | 45/45 | 24 條規則（4 張表的 rule 定義） |
| **Stage 2: Core Validator** | ✅ | 19/19 | DataValidator, ValidationReport, ReportWriter |
| **Stage 3: 交易日曆** | ✅ | 21/21 | TradingCalendar（2026 年假日內建） |
| **Stage 4: Pipeline 整合** | ✅ | 21/21 | CLI flags, DataValidator 串接, 流程控制 |
| **Stage 5: 真實 E2E 測試** | ✅ | 13/13 | 真 API 請求 + collect-only 模式驗證 |

**原始碼位置**: `src/run_daily.py`, `src/validators/`, `src/utils/trading_calendar.py`, `src/framework/base_spider.py`  
**測試位置**: `tests/test_framework/test_validator_rules.py`, `test_validator_checker.py`, `test_trading_calendar.py`, `test_stage4_pipeline_integration.py`, `tests/test_stage5_e2e_integration.py`  
**報告位置**: `logs/validation/`

---

## 核心架構

```
Step 1: 爬蟲 (collect_only)
  spider.add_item(item) → _pending_items (暫存，不寫 DB)
  ↓
Step 2: 驗證
  DataValidator.run() → 24 條規則
  ↓
  report.has_errors() ?
  ├─ True + 無 --force → exit(1)  (髒資料被阻擋)
  ├─ True + --force    → 繼續
  └─ False             → 繼續
  ↓
Step 2.5: 寫入 DB
  spider.flush_items(pipeline) → DB
  ↓
Step 3: 清洗（不變）
```

## 已修正的真實 bug
- tpex_cb_daily: closing_price=0 改為 WARNING（未交易日正常值）
- cb_master: conversion_price 字串型態加 float() 轉換
- stock_daily: close_price 重複條件清理

---

## 核心文件清單

### 規劃階段文件（v1.0）

### 1. **DEVELOPMENT_PLAN.md** — 整體設計哲學與檢查維度
   - 四種資料類型的預期與成功標準
   - 使用者視角（正常、異常、強制繼續、驗證模式）

### 2. **STAGE_BREAKDOWN.md** — 6 階段開發指南
   - 每個 Stage 的開發步驟、程式碼範例、測試方法
   - 實際略有調整（Stage 4 提前合併部分功能）

### 3. **BOUNDARIES_AND_CONSTRAINTS.md** — 邊界劃分
   - IN SCOPE / OUT OF SCOPE 定義
   - Validator vs Cleaner 分工原則

### 4. **IMPLEMENTATION_NOTES.md** — 開發陷阱與優化建議
   - Trading calendar 維護策略
   - Validator vs Cleaner 協作
   - 常見錯誤與解決方案

### 實作階段文件（v2.0）

### 5. **VALIDATION_RULES.md** — 24 條規則完整目錄
   - **stock_master**: 6 條 rules
   - **stock_daily**: 7 條 rules
   - **cb_master**: 5 條 rules
   - **tpex_cb_daily**: 6 條 rules
   - 每條 rule 含 ID、severity、邏輯、通過/失敗範例
   - **新增 Pipeline 整合說明**

### 6. **INTEGRATION_GUIDE.md** (v2.0) — 實際實作手冊
   - **更新為實際實作架構**（非規劃版）
   - `step_validate()` 串接 DataValidator 的完整程式碼
   - Cross-table 參數注入機制
   - 24 條規則的 pipeline 對應關係
   - 報告輸出格式與範例

### 7. **STAGE_1_3_COMPLETION_REPORT.md** — Stage 1-3 完成報告
   - 45+19+21 = 85 個測試結果
   - 24 條規則詳情
   - Validator 與 Calendar 完整設計

### 8. **STAGE_4_PIPELINE_INTEGRATION_REPORT.md** — Stage 4 完成報告
   - DataValidator 串接的完整說明
   - 真實 records 驗證的測試結果
   - 流程控制與錯誤處理策略

### 9. **STAGE_5_E2E_REPORT.md** — Stage 5 完成報告
   - 13 個真實 E2E 測試（不 mock）
   - 真實 API 請求驗證 DataValidator
   - collect-only 模式的正確性驗證
   - 3 個真實 bug 的修復記錄

---

## 快速開始

### 給開發者

1. **先讀** `DEVELOPMENT_PLAN.md` 瞭解整體目標
2. **參考** `STAGE_BREAKDOWN.md` 逐步實作（從 Stage 1 開始）
3. **查詢** `VALIDATION_RULES.md` 了解每條 rule 的細節
4. **遵守** `BOUNDARIES_AND_CONSTRAINTS.md` 的限制
5. **參考** `IMPLEMENTATION_NOTES.md` 避免常見陷阱

### 給測試人員

1. 閱讀 `DEVELOPMENT_PLAN.md` 的「成功標準」章節
2. 查看 `STAGE_BREAKDOWN.md` 中各 Stage 的「測試通過指標」
3. 根據 `INTEGRATION_GUIDE.md` 的 4 個場景進行測試

### 給架構師/評審

1. 重點看 `BOUNDARIES_AND_CONSTRAINTS.md`（設計邊界）
2. 查看 `DEVELOPMENT_PLAN.md` 的「整體設計哲學」
3. 確認 `INTEGRATION_GUIDE.md` 中對現有流程的修改是否可接受

---

## 核心概念速覽

### 五個檢查維度

| 維度 | 說明 | 例子 |
|------|------|------|
| **完整性** | Row count 符合預期 | 2026-04 應有 21 × 3 = 63 筆 stock_daily |
| **結構性** | 欄位齊全、型態正確 | symbol, date, close_price, volume 都有 |
| **值域** | 價格 > 0、成交量 >= 0 | close_price = 0 → FAIL |
| **一致性** | 關鍵欄位可與 master 比對 | stock_daily 的 symbol 都在 stock_master 中 |
| **異常** | 單日漲跌幅 > 10% → 警告 | price_change = 15% → WARNING |

### 六個開發階段

```
Week 1
├─ Stage 1: Rules 定義 (1-2 days)
└─ Stage 2: Checker 實作 (1-2 days)

Week 1-2
└─ Stage 3: Trading Calendar (0.5 days)
   Stage 5: Report Writer (0.5 days)

Week 2
└─ Stage 4: Pipeline 整合 (1-2 days)

Week 2-3
└─ Stage 6: 整合測試 (1-2 days)

Week 3
└─ 文件編寫與最終檢查 (1 day)
```

### 三個 CLI 模式

```bash
# 模式 1: 正常流程（默認）
python src/run_daily.py
# Spider → Validate → [fail? abort : continue] → Write → Clean

# 模式 2: 僅驗證
python src/run_daily.py --validate-only
# Spider → Validate → [生成 report，不寫入]

# 模式 3: 強制繼續
python src/run_daily.py --force-validation
# Spider → Validate → [即使 fail 仍] → Write → Clean
```

---

## 預期的目錄結構

開發完成後，新增檔案將包括：

```
src/
├── validators/                      # 新增
│   ├── __init__.py
│   ├── rules.py                    # ValidationRule dataclass
│   ├── checker.py                  # DataValidator class
│   ├── report.py                   # ValidationReport dataclass
│   ├── report_writer.py            # JSON report writer
│   ├── stock_master_rules.py
│   ├── stock_daily_rules.py
│   ├── cb_master_rules.py
│   └── tpex_cb_daily_rules.py
└── utils/
    └── trading_calendar.py         # 修改/新增

tests/
├── test_framework/
│   └── test_validation.py          # 新增整合測試
└── test_data/
    └── validation/                 # 新增 mock 資料
        ├── normal_stock_daily.json
        ├── missing_dates_stock_daily.json
        ├── expected_report_normal.json
        └── ...

logs/
└── validation/                     # 運行時產生
    ├── YYYY-MM-DD_HHMMSS_stock_master.json
    ├── YYYY-MM-DD_HHMMSS_stock_daily.json
    ├── YYYY-MM-DD_HHMMSS_cb_master.json
    ├── YYYY-MM-DD_HHMMSS_tpex_cb_daily.json
    └── YYYY-MM-DD_HHMMSS_summary.json
```

---

## 成功驗收清單

開發完成時應檢查以下項目：

- [ ] 所有 6 份規劃文件已產出（本目錄）
- [ ] `src/validators/` 目錄建立，包含所有必要模組
- [ ] 四種 table 各定義 5+ 條 rules，共 20+ 條
- [ ] `DataValidator` class 可獨立測試，覆蓋率 >= 85%
- [ ] `TradingCalendar` 支援月份與日期範圍查詢
- [ ] `run_daily.py` 整合 validation，支援 3 個 CLI flag
- [ ] 單位測試全部 PASS（`pytest tests/test_framework/test_validation*.py -v`）
- [ ] E2E 測試通過（正常、validate-only、force、legacy 四個場景）
- [ ] JSON report 檔案正確產出到 `logs/validation/`
- [ ] 所有文件進版本控制（`.gitignore` 排除 logs/validation）

---

## 文件版本歷史

- **v1.0** (2026-04-30)：初版規劃完成，6 份文檔產出

---

## 後續步驟

### 立即行動（go/no-go 決定）
1. 團隊評審本規劃（尤其是 BOUNDARIES 部分）
2. 確認 timeline 與資源分配
3. 決定是否進入 Stage 1（Rules 定義）

### 如有疑問
- 架構相關：查看 `DEVELOPMENT_PLAN.md`
- 實作細節：查看 `STAGE_BREAKDOWN.md`
- 邊界爭議：查看 `BOUNDARIES_AND_CONSTRAINTS.md`
- 陷阱預防：查看 `IMPLEMENTATION_NOTES.md`

---

**本文件為 Phase 2 的入口點。建議所有參與者先讀本文檔，再根據角色查閱詳細文檔。**
