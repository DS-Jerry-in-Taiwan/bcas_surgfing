# Phase 6 開發日誌 — E2E 整合驗證

> 最後更新: 2026-05-15

---

## 執行摘要

首次完整執行 `run_daily.py` + `run_eod_analysis.py` 端到端 Pipeline，使用**真實資料**驗證每一階段。

### 驗證結論

```
Pipeline 核心流程: ✅ 完全正常
資料正確性:       ✅ DB 寫入驗證通過
單元測試回歸:     ✅ 295 passed (零回歸)
分析鏈空資料:     ⚠️ 因 cb_master 無資料，PremiumCalculator 產出 0 筆
Clean 階段:       ❌ master_check 欄位不存在於 DB
```

---

## Phase A — 逐個爬蟲真實資料測試 (✅)

| 爬蟲 | success | items | 狀態 |
|------|:-------:|:-----:|:----:|
| StockMasterSpider | True | 32,076 | ✅ |
| CbMasterSpider | True | 0 | ⚠️ E2E-001 |
| StockDailySpider | True | 10 | ✅ |
| TpexCbDailySpider | True | 378 | ✅ |
| BrokerBreakdownSpider | True | 437 | ✅ |

## Phase B — run_daily.py 執行 (✅ 核心流程通過)

### B.1 --validate-only
- ✅ 5 spiders 全部成功執行
- ✅ step_validate 正常運作
  - stock_master: 4 passed / 0 failed / 2 warnings
  - stock_daily: 5 passed / 0 failed / 1 warning
  - tpex_cb_daily: 4 passed / 1 failed (cb_code consistency, 因 cb_master=0)
  - broker_breakdown: 0 rules (跳過，符合設計)
- ⚠️ has_errors=true (tpex_cb_daily consistency fail)，正確中止

### B.2 --force-validation
- ✅ spiders → validate → flush 完整執行
- ✅ DB 寫入驗證通過：
  - stock_master: 32,076
  - stock_daily: 10 (+2 既有)
  - tpex_cb_daily: 378
  - broker_breakdown: 437
- ❌ Step 3 (clean) 失敗：`master_check` 欄位不存在於 DB (E2E-004)

## Phase C — run_eod_analysis.py (✅ 4 階段零崩潰)

| Stage | 結果 | 備註 |
|-------|:----:|------|
| Stage 1: spiders + flush | ✅ | 同 Phase B |
| Stage 2: analytics | ✅ 0 筆 | PremiumCalculator 因 cb_master=0 無法計算溢價率 |
| Stage 3: risk | ✅ 0 筆 | RiskAssessor 因 daily_analysis_results 為空 |
| Stage 4: report | ✅ 34 chars | 報表產出 (實質空，因無 trading signals) |

**修復**: 發現 `run_eod_analysis.py` sys.path 缺少 project root，導致 Stage 2-4 無法 import `src.xxx` 模組。已修正：

```python
# Before:
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))  # src/ only

# After:
_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _THIS_DIR)                                # src/
sys.path.insert(0, os.path.abspath(os.path.join(_THIS_DIR, "..")))  # project root
```

## Phase D — DB 資料驗證 (✅)

```sql
stock_master:       32,076 ✅
stock_daily:           12 ✅
tpex_cb_daily:        378 ✅
broker_breakdown:     871 ✅ (all source_type='bsr')
broker_blacklist:      10 ✅
cb_master:              0 ⚠️ E2E-001
daily_analysis_results: 0 ⚠️ (因 cb_master=0)
trading_signals:        0 ⚠️ (因 daily_analysis_results=0)
```

---

## 更新檔案

| 檔案 | 操作 | 說明 |
|------|------|------|
| `src/db/init_eod_tables.sql` | ✅ commit | 加入 source_url, source_type 欄位 |
| `src/run_eod_analysis.py` | ✅ fix | sys.path 加入 project root |
| `docs/agent_context/phase6/task_plan.md` | ✅ update | Issue Log 狀態更新 |
| `docs/agent_context/phase6/development_log.md` | ✅ create | 本文件 |
| `docs/project_context.md` | ✅ update | Phase 5/6 完成狀態 |
