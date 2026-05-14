# Stage 5 任務規劃 — E2E 整合與驗證

> **Phase**: Phase 5 (BSR + ddddocr 整合)
> **Stage**: 5/5 — E2E 整合與驗證
> **更新日期**: 2026-05-14
> **負責角色**: AI Architect Team

---

## 1. 需求確認

### 1.1 任務目標

將 BrokerBreakdownSpider (BSR+OCR) 完整整合到 `run_daily.py` 與 EOD Pipeline 中，確保：
1. `step_spiders()` 中 BSR spider 正常執行 (collect_only → validate → flush)
2. E2E 流程完整通過 (爬蟲 → 驗證 → 寫入 → 清洗 → 分析 → 評級)
3. 所有測試無回歸

### 1.2 成功標準

| 驗收項目 | 驗證方式 | 預期結果 |
|---------|---------|---------|
| `step_spiders()` 包含 BrokerBreakdownSpider | 執行 `python3 src/run_daily.py --validate-only` | broker_breakdown 資料正確暫存 |
| `flush_pipelines()` 可寫入 broker_breakdown | 查看 DB broker_breakdown 表 | 有 BSR 資料 |
| step_validate 不因 broker_breakdown 崩潰 | 執行 step_validate | broker_breakdown 跳過驗證，其他表正常 |
| E2E 完整流程 | 執行完整 pipeline | 5 spiders → validate → flush → clean → EOD 分析順暢 |
| 既有測試零回歸 | `pytest tests/` | 全部通過 |
| E2E 測試新增 | `pytest tests/test_stage5_e2e_integration.py -v` | 13+ 測試通過 (含新增) |

### 1.3 依賴關係

```
上游完成狀態:
  Stage 1 (OCR)     ✅ BsrClient + OcrSolver
  Stage 2 (BSR Client) ✅ 59 tests
  Stage 3 (Spider)     ✅ BrokerBreakdownSpider + step_spiders 整合
  Stage 4 (Risk)       ✅ ChipProfiler + RiskAssessor 恢復

下游:
  └─ EOD Pipeline → Stage 1 (_run_spiders) 已整合
  └─ EOD Pipeline → Stage 3 (_run_risk) 已整合 (Stage 4)
```

---

## 2. 代碼與架構掃描

### 2.1 現有整合狀態

#### step_spiders() — `src/run_daily.py`

```python
def step_spiders():
    # ...
    # Broker Breakdown (已存在)
    p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
    s = BrokerBreakdownSpider(pipeline=p)
    s.collect_only = True
    try:
        today_str = datetime.now().strftime("%Y%m%d")
        r = s.fetch_broker_breakdown(today_str, "2330")   # 硬編碼 2330
        # ...
    except:
        s.close()
        raise
```

**問題**: `fetch_broker_breakdown()` 硬編碼 `"2330"`，未來需支援多檔股票遍歷。

#### step_validate() — `src/run_daily.py`

```python
for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
    # ...
```

**問題**: `broker_breakdown` 不在驗證清單中。BSR 為 OCR 資料，結構不可預測，不宜加入標準驗證規則。

#### EOD Pipeline — `src/pipeline/eod_pipeline.py`

```python
def _run_spiders(self, date: str):
    from run_daily import step_spiders, flush_pipelines
    results, records, pipelines = step_spiders()
    flush_pipelines(pipelines)
```

**狀態**: `_run_spiders()` 呼叫 `step_spiders()`，BSR spider 自動包含。

### 2.2 測試現狀

#### 既有 E2E 測試: `tests/test_stage5_e2e_integration.py`

| 測試類別 | 案例 | 說明 |
|---------|------|------|
| TestE2ERealStockMaster | 2 | 真實 TWSE fetch + validate |
| TestE2ERealStockDaily | 3 | 真實 daily + validate |
| TestE2ERealCbMaster | 1 | 真實 CB master + validate |
| TestE2ERealTpexCbDaily | 1 | 真實 TPEx daily + validate |
| TestE2ERealCrossTable | 2 | 跨表一致性檢查 |
| TestE2ERealAllTables | 1 | 4 表同時驗證 |
| TestE2ERealReportOutput | 3 | 報表輸出格式 |
| TestE2ERealValidateOnly | 1 | --validate-only 流程 |
| **合計** | **13** | ❌ **不含 broker_breakdown** |

### 2.3 變更影響範圍

| 檔案 | 操作 | 原因 |
|------|------|------|
| `src/run_daily.py` | 🔍 驗證 step_spiders() | BSR spider 已存在，需確認相容性 |
| `src/run_daily.py` | 📝 修改 step_validate() | 加入 broker_breakdown 跳過邏輯 |
| `tests/test_stage5_e2e_integration.py` | 📝 新增測試 | 加入 broker_breakdown E2E 測試 |
| `docs/agent_context/phase5/development_log.md` | 📝 更新 | Phase 5 最終總結 |
| `docs/project_context.md` | 📝 更新 | Phase 5 標記完成 |

---

## 3. 階段實作與測試步驟

### 3.1 Stage 5.1 — run_daily.py 相容性測試 (1h)

**動作**:

1. **驗證 step_spiders() 中 BrokerBreakdownSpider**
   ```bash
   # 確認 import 正常，spider 可被實例化
   python -c "
   from spiders.broker_breakdown_spider import BrokerBreakdownSpider
   s = BrokerBreakdownSpider()
   print(f'BrokerBreakdownSpider 可實例化 ✅')
   s.close()
   "
   ```

2. **驗證 step_spiders() 可包含 BSR**
   ```bash
   # 模擬 step_spiders 中 BSR 部分
   python -c "
   from spiders.broker_breakdown_spider import BrokerBreakdownSpider
   with BrokerBreakdownSpider() as s:
       s.collect_only = True
       r = s.fetch_broker_breakdown('20260514', '2330')
       print(f'fetch_broker_breakdown: success={r.success}, items={len(s.get_items())}')
   "
   ```

3. **驗證 step_validate 不因 broker_breakdown 崩潰**
   - 在 step_validate 的 table list 中加入 `"broker_breakdown"`
   - 由於無對應 validator rules，預期跳過 (skipped)
   ```bash
   python -c "
   from unittest.mock import patch, MagicMock
   from run_daily import step_validate

   result = step_validate(
       {'broker_breakdown': {'success': True, 'count': 5}, 'stock_master': {'success': True, 'count': 1}},
       {'broker_breakdown': [{'symbol': '2330', 'broker_id': '9200'}], 'stock_master': [{'symbol': '2330', 'name': 'TSMC'}]},
   )
   assert 'broker_breakdown' in result['reports']
   print(f'broker_breakdown in reports ✅')
   "
   ```

4. **執行 --validate-only 確認流程**
   ```bash
   python3 src/run_daily.py --validate-only
   ```

### 3.2 Stage 5.2 — E2E 流程測試 (1h)

**動作**:

1. **更新 step_validate 加入 broker_breakdown 支援**

   修改 `src/run_daily.py`，在 `step_validate()` 的 table list 中加入 `"broker_breakdown"`：

   ```python
   # Before:
   for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
   
   # After:
   for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily", "broker_breakdown"]:
   ```

   **設計說明**:
   - `broker_breakdown` 無對應 validator rules
   - 當 DataValidator 接到的 table_name 無註冊規則時，**所有規則跳過 (skipped)**
   - 驗證結果為 0 passed / 0 failed / 0 warnings / N skipped
   - 不會阻斷 pipeline 流程

2. **新增 broker_breakdown E2E 測試**

   在 `tests/test_stage5_e2e_integration.py` 中新增:

   **TestE2ERealBrokerBreakdown**:
   - `test_fetch_bsr_data`: 呼叫 BrokerBreakdownSpider 真實 fetch，確認回傳成功
   - `test_bsr_in_step_validate`: 模擬 step_validate 包含 broker_breakdown

   **TestE2EAllTablesWithBrokerBreakdown**:
   - `test_all_5_tables_pass`: 5 表同時驗證 (含 broker_breakdown)

3. **驗證完整 E2E 流程**
   ```bash
   # 完整 pipeline (需要 DB)
   python3 src/run_daily.py --skip-clean
   ```

### 3.3 Stage 5.3 — 開發日誌與最終驗收 (0.5h)

**動作**:
1. 更新 `docs/agent_context/phase5/development_log.md` — Phase 5 最終總結
2. 更新 `docs/project_context.md` — Phase 5 標記完成
3. 執行最終全量測試確認零回歸

---

## 4. 完成標準與測試指標

### 4.1 打通標準

| 檢查項 | 通過條件 | 驗證方式 |
|--------|---------|---------|
| step_validate 含 broker_breakdown | 不拋錯，正常回傳 report | `pytest -k "broker"` |
| BSR spider 在 step_spiders 中正常 | `--validate-only` 不崩潰 | `python3 src/run_daily.py --validate-only` |
| E2E 測試新增 | 2 個新測試案例通過 | `pytest tests/test_stage5_e2e_integration.py -v` |
| 既有 54 測試零回歸 | 全部通過 | `python -m pytest tests/test_risk_assessor.py tests/test_chip_profiler.py tests/test_stage4_risk_pipeline.py -v` |
| Phase 5 全部測試 | 各 stage 測試總和通過 | 各 stage 逐一確認 |

### 4.2 量化指標

| 指標 | Stage 5 前 | Stage 5 目標 |
|------|-----------|-------------|
| E2E 測試案例 | 13 (不含 BSR) | 15+ (含 BSR) |
| step_validate 涵蓋表數 | 4 | 5 |
| Phase 5 總測試 | 208+ | 208+ (零回歸) |
| run_daily.py BSR 相容性 | 未驗證 | ✅ 已驗證 |

---

## 5. 開發過程與結果紀錄

### 5.1 開發日誌記錄要求

Stage 5 完成後更新 `docs/agent_context/phase5/development_log.md`：
- 最終測試總表 (各 stage 測試統計)
- E2E 驗證結果
- Phase 5 最終總結

### 5.2 Stage 5 完成後更新 project_context.md

- 將 Phase 5 狀態從「進行中」改為「✅ 已完成」
- 更新 broker_breakdown spider 狀態為「✅ 已恢復 (BSR+OCR)」
- 更新 chip_profiler / risk_assessor 狀態為「✅ 已恢復」

---

## 6. 任務邊界與禁止事項

### 6.1 邊界定義

| 項目 | 歸屬 |
|------|------|
| ✅ step_validate 加入 broker_breakdown | **屬於** Stage 5 |
| ✅ E2E 測試新增 broker_breakdown | **屬於** Stage 5 |
| ✅ run_daily.py --validate-only 相容性 | **屬於** Stage 5 |
| ✅ 最終開發日誌撰寫 | **屬於** Stage 5 |
| ❌ 修改 BsrClient 邏輯 | **不屬於** (Stage 2) |
| ❌ 修改 BrokerBreakdownSpider 邏輯 | **不屬於** (Stage 3) |
| ❌ 修改 ChipProfiler / RiskAssessor | **不屬於** (Stage 4) |
| ❌ 新增 broker_breakdown validator rules | **不屬於** (OCR 資料不適合標準驗證) |
| ❌ 並行化爬蟲 / 監控系統 / 故障恢復 | **不屬於** (Phase 5 後優化項目) |
| ❌ 修改 DB schema | **不屬於** |

### 6.2 禁止事項

- ❌ 禁止修改 BrokerBreakdownSpider 的簽名或 collect_only 模式
- ❌ 禁止新增 DB 表或修改 broker_breakdown schema
- ❌ 禁止為 broker_breakdown 建立 validator rules（BSR 資料為 OCR 結果，結構不穩定）
- ❌ 禁止移除其他 4 表的既有驗證邏輯
- ❌ 禁止在 step_validate 中因 broker_breakdown 失敗而阻塞 pipeline

---

## 7. 其他影響因素

### 7.1 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| BSR 網站改版或 captcha 變更 | 低 | 高 | BsrClient 有 circuit breaker + retry；降級處理 risk_ratio=0 |
| BSR 在非交易時段無資料 | 高 (非交易日) | 低 | step_spiders 已有 except 處理，BSR 失敗視為 success=False |
| ddddocr 辨識率下降 | 低 | 中 | 已有 retry 機制 (max 3)，降級不中斷 pipeline |
| run_daily.py step_spiders 逾時 | 低 | 中 | BSR 有 timeout 設定 (BsrClient._session.timeout) |
| step_validate 因 broker_breakdown 拋錯 | 低 | 中 | 加入 try/except 確保不阻塞其他表 |

### 7.2 測試金字塔

```
Stage 5 測試:
         ╱╲
        ╱  ╲      2 E2E (真實 BSR 呼叫)
       ╱    ╲
      ╱      ╲    3 相容性測試 (模擬 step_spiders/step_validate)
     ╱────────╲
    ╱          ╲  54 既有測試 (RiskAssessor 38 + ChipProfiler 16)
   ╱────────────╲
  ╱              ╲  77 Stage 2+3 測試 (BSR Client 59 + Spider 18)
 ╱────────────────╲
```

### 7.3 回滾策略

- step_validate 修改極小 (僅新增一個 table name)，可一秒還原
- 測試檔案可安全移除
- DB 資料可 TRUNCATE broker_breakdown 表重新執行

---

## 8. 時程預估

| 子階段 | 工時 | 說明 |
|--------|------|------|
| 5.1 run_daily 相容性 | 1.0h | step_validate 修改 + --validate-only 驗證 |
| 5.2 E2E 流程測試 | 1.0h | E2E 測試新增 + 完整 pipeline 驗證 |
| 5.3 開發日誌 | 0.5h | Phase 5 最終總結 + project_context 更新 |
| **總計** | **2.5h** | |

---

## 9. Phase 5 最終驗收總表

### 各 Stage 測試統計

| Stage | 測試檔案 | 測試數 | 狀態 |
|-------|---------|--------|------|
| Stage 1 | `tests/test_bsr_captcha.py` | OCR 獨立測試 | ✅ |
| Stage 2 | `tests/test_bsr_client.py` | 59 | ✅ |
| Stage 3 | `tests/test_broker_breakdown_spider.py` | 18 | ✅ |
| Stage 4 | `tests/test_risk_assessor.py` | 38 | ✅ |
| Stage 4 | `tests/test_chip_profiler.py` | 16 | ✅ |
| Stage 4 | `tests/test_stage4_risk_pipeline.py` | 18 | ✅ |
| Stage 5 | `tests/test_stage5_e2e_integration.py` | 13+2 | ⏳ |
| **Phase 5 總計** | | **164+** | **⏳** |

### 最終資料流確認

```
BSR 網站
  ↓ OCR (ddddocr)
BsrClient (session/captcha/submit/parse)
  ↓
BrokerBreakdownSpider (collect_only → add_item → flush)
  ↓
broker_breakdown 表 (PostgreSQL)
  ↓
ChipProfiler.analyze() → risk_ratio per symbol
  ↓
RiskAssessor.run_analysis() → S/A/B/C rating
  ↓
daily_analysis_results (final_rating, broker_risk_pct)
trading_signals (BUY/HOLD/AVOID)
```

---

## 10. 參考資料

- `docs/agent_context/phase5/02_work_breakdown.md` — 原始 WBS
- `docs/agent_context/phase5/development_log.md` — 開發日誌
- `docs/agent_context/phase5/task_plan_stage4.md` — Stage 4 規劃
- `src/run_daily.py` — 主管道
- `tests/test_stage5_e2e_integration.py` — 既有 E2E 測試
- `src/pipeline/eod_pipeline.py` — EOD 管道
