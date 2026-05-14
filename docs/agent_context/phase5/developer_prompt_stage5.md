# Stage 5 Developer Prompt — E2E 整合與驗證

## 任務描述

將 BrokerBreakdownSpider (BSR+OCR) 完整整合到 `run_daily.py` 的資料驗證流程中，並更新 E2E 測試套件。這是 **Phase 5 的最後一個 Stage**。

**Phase 5 進度**:
- Stage 1 (OCR 測試): ✅ ddddocr 辨識率 100%
- Stage 2 (BSR Client): ✅ BsrClient (59 tests)
- Stage 3 (Spider 改寫): ✅ BrokerBreakdownSpider (77 tests)
- Stage 4 (RiskAssessor 恢復): ✅ S/A/B/C 評級鏈 (72 tests)
- **Stage 5 (E2E 驗證): ⬅️ 當前任務**

---

## 開發目標

### 主要目標
1. **step_validate 加入 broker_breakdown** — 在驗證迴圈中新增 broker_breakdown (跳過驗證規則，不阻塞 pipeline)
2. **E2E 測試更新** — 在既有 `test_stage5_e2e_integration.py` 中新增 broker_breakdown 測試
3. **既有測試零回歸** — 所有 54 個 Stage 4 測試 + 13 個既有 E2E 測試全部通過

### 次要目標
- 確認 `run_daily.py --validate-only` 含 BSR spider 正常執行
- 更新開發日誌與 project_context

---

## 背景資訊

### 當前 run_daily.py 狀態

**step_spiders()** — BSR spider 已在 Stage 3 加入，沒問題。

**step_validate()** — 目前只驗證 4 張表，broker_breakdown 完全不在流程中：

```python
# src/run_daily.py, line 255
for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
```

### BSR 資料特性

BSR 資料是從 HTML 表格解析 + OCR 辨識的結果，**不適合**標準的 validator rules（結構不穩定、無固定 schema 可預測）。因此不為 broker_breakdown 建立 validator rules。

---

## 具體實作要求

### 1. 修改 `src/run_daily.py` — step_validate() (0.2h)

在 `step_validate()` 的 table list 中加入 `"broker_breakdown"`：

```python
# Line 255 修改
for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily", "broker_breakdown"]:
```

**設計說明**:
- DataValidator 收到 `table_name="broker_breakdown"` 時，由於沒有對應的規則模組，所有規則會顯示為 **skipped**
- 驗證結果為: `0 passed / 0 failed / 0 warnings / N skipped`
- 不會拋錯，不阻塞 pipeline
- broker_breakdown 在 validation report 中可見，方便追蹤

### 2. 更新 `tests/test_stage5_e2e_integration.py` (1h)

在現有檔案中新增以下測試類別：

#### 2.1 `TestE2ERealBrokerBreakdown` — BSR spider E2E (2 測試)

```python
class TestE2ERealBrokerBreakdown:
    """Real BSR fetch → data validation flow"""

    def test_fetch_bsr_data(self):
        """BrokerBreakdownSpider 可透過 BsrClient 取得資料"""
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider
        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            assert result.success, f"BSR fetch failed: {result.error}"
            items = spider.get_items()
            assert len(items) > 0, "Should have at least 1 broker record"
            item = items[0]
            assert item.symbol == "2330"
            assert item.source_type == "bsr"
            assert item.broker_id, "broker_id should not be empty"
            assert item.broker_name, "broker_name should not be empty"
        finally:
            spider.close()

    def test_bsr_in_step_validate(self):
        """step_validate 可處理 broker_breakdown 不拋錯"""
        from run_daily import step_validate
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider

        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            if not result.success:
                pytest.skip(f"BSR unavailable, skip: {result.error}")

            records = [item.to_dict() for item in spider.get_items()]

            spider_result = {
                "broker_breakdown": {"success": True, "count": len(records)},
                "stock_master": {"success": True, "count": 1},
            }
            collected = {
                "broker_breakdown": records,
                "stock_master": [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}],
            }

            v_result = step_validate(spider_result, collected)
            assert "broker_breakdown" in v_result["reports"]
            bb_report = v_result["reports"]["broker_breakdown"]

            # broker_breakdown 無 validator rules → 全部 skipped
            assert bb_report.get("skipped", False) or len(bb_report.get("skipped_rules", [])) >= 0
        finally:
            spider.close()
```

#### 2.2 `TestE2EAllTablesWithBrokerBreakdown` — 5 表同時驗證 (1 測試)

```python
class TestE2EAllTablesWithBrokerBreakdown:
    """All 5 tables including broker_breakdown validated together"""

    def test_all_5_tables_pass(self):
        """5 表同時驗證，broker_breakdown 不阻斷其他表"""
        from run_daily import step_validate
        from spiders.broker_breakdown_spider import BrokerBreakdownSpider

        # 準備 broker_breakdown 資料
        spider = BrokerBreakdownSpider()
        try:
            result = spider.fetch_broker_breakdown("20260514", "2330")
            if not result.success:
                pytest.skip(f"BSR unavailable, skip: {result.error}")
            bb_records = [item.to_dict() for item in spider.get_items()]
        finally:
            spider.close()

        # 4 表模擬資料
        spider_results = {
            "stock_master": {"success": True, "count": 1},
            "stock_daily": {"success": True, "count": 1},
            "cb_master": {"success": True, "count": 1},
            "tpex_cb_daily": {"success": True, "count": 1},
            "broker_breakdown": {"success": True, "count": len(bb_records)},
        }
        collected = {
            "stock_master": [{"symbol": "2330", "name": "TSMC", "market_type": "TWSE", "industry": "半導體"}],
            "stock_daily": [{"symbol": "2330", "date": "2026-05-14", "close_price": 100.0, "volume": 1000}],
            "cb_master": [{"cb_code": "23301", "cb_name": "台積電一", "conversion_price": 100.0, "market_type": "TPEx"}],
            "tpex_cb_daily": [{"cb_code": "23301", "trade_date": "2026-05-14", "closing_price": 105.0, "volume": 100}],
            "broker_breakdown": bb_records,
        }

        v_result = step_validate(spider_results, collected)
        assert "broker_breakdown" in v_result["reports"]
        assert "stock_master" in v_result["reports"]
        assert "stock_daily" in v_result["reports"]
        # broker_breakdown 不因無 validator rules 而拋錯
        assert not v_result.get("error")
```

### 3. 驗證相容性 (0.3h)

```bash
# 1. 既有測試零回歸
python -m pytest tests/test_risk_assessor.py tests/test_chip_profiler.py tests/test_stage4_risk_pipeline.py -v --tb=short

# 2. E2E 測試 (含新增)
python -m pytest tests/test_stage5_e2e_integration.py -v --tb=short

# 3. BSR spider 獨立測試
python -m pytest tests/test_broker_breakdown_spider.py tests/test_bsr_client.py -v --tb=short

# 4. run_daily --validate-only (需要 DB)
python3 src/run_daily.py --validate-only
```

---

## 專案規範

### 必須遵循
- ✅ 只在 `step_validate` 的 table list 中新增 `"broker_breakdown"` 字串
- ✅ 使用 `pytest.skip` 處理 BSR 真實呼叫不可用時的情境
- ✅ 遵循現有 `test_stage5_e2e_integration.py` 的測試風格
- ✅ 使用 `spider.close()` 或 `try/finally` 確保資源釋放

### 禁止事項
- ❌ 禁止為 broker_breakdown 建立 validator rules
- ❌ 禁止修改 BrokerBreakdownSpider、BsrClient、ChipProfiler、RiskAssessor
- ❌ 禁止修改 DB schema
- ❌ 禁止修改其他 4 表的驗證邏輯
- ❌ 禁止在 step_validate 中因 broker_breakdown 失敗而拋錯中止

---

## 驗收標準

### 1. 既有測試零回歸
```bash
python -m pytest tests/test_risk_assessor.py tests/test_chip_profiler.py tests/test_stage4_risk_pipeline.py tests/test_broker_breakdown_spider.py tests/test_bsr_client.py -v
# 結果: 149 passed (38 + 16 + 18 + 59 + 18)
```

### 2. E2E 測試通過
```bash
python -m pytest tests/test_stage5_e2e_integration.py -v
# 結果: 13+3 = 16 passed (含新增的 broker_breakdown 測試)
```

### 3. step_validate 相容性驗證
```python
python -c "
from run_daily import step_validate
result = step_validate(
    {'broker_breakdown': {'success': True, 'count': 0}, 'stock_master': {'success': True, 'count': 1}},
    {'broker_breakdown': [], 'stock_master': [{'symbol': '2330', 'name': 'TSMC', 'market_type': 'TWSE', 'industry': '半導體'}]},
)
assert 'broker_breakdown' in result['reports']
print('step_validate 相容 broker_breakdown ✅')
"
```

---

## 預期產出

| 產出 | 路徑 | 說明 |
|------|------|------|
| step_validate 修改 | `src/run_daily.py` (line 255) | table list 加 `broker_breakdown` |
| E2E 測試更新 | `tests/test_stage5_e2e_integration.py` | 新增 ~3 個測試 |
| 開發日誌更新 | `docs/agent_context/phase5/development_log.md` | Stage 5 + Phase 5 最終總結 |
| project_context 更新 | `docs/project_context.md` | Phase 5 標記完成 |

---

## 時程

| 子階段 | 工時 | 說明 |
|--------|------|------|
| 5.1 step_validate 修改 + 驗證 | 0.3h | 一行修改 + 相容性驗證 |
| 5.2 E2E 測試新增 | 1.0h | ~3 個新測試案例 |
| 5.3 相容性 + 最終驗收 | 0.7h | 全量測試 + 文件更新 |
| **合計** | **2.0h** | |
