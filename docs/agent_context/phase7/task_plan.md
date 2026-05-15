# Phase 7 — 分析鏈修復 (Enrichment + E2E 驗證)

> **觸發**: Phase 6 E2E 驗證發現 GAP-01 (underlying_stock 未填入) 與 GAP-02 (DataCleaner 欄位缺失)
> **Phase**: 7 — 分析鏈修復與 E2E 驗證
> **預計工時**: 3-5h
> **優先級**: 🔴 高

---

## 任務

### 1. 修 DataCleaner (GAP-02)

`src/etl/run_cleaner.py` 中 `validate_stock_daily()` 和 `validate_cb_daily()` 使用 `SET master_check = CASE ...`，但 `stock_daily` 和 `tpex_cb_daily` 表沒有 `master_check` 欄位。

**修複方式**: 在 `run_all()` 中先檢查並建立 `master_check` 欄位（若不存在）。

### 2. 加 `enrich_cb_master()` (GAP-01)

在 DataCleaner 中新增方法，用 `cb_code[:4]` 比對 `stock_master.symbol`，填入 `cb_master.underlying_stock`。

### 3. E2E 驗證

用 2026-05-14 歷史資料驗證完整分析鏈產出 S/A/B/C 評級。
