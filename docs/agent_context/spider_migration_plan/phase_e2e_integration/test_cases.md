# E2E 整合測試案例

## 測試類別清單

| 測試ID | 測試類別 | 測試方法數 | 優先級 |
|--------|----------|-----------|--------|
| E2E-01 | TestFullPipelineFlow | 5 | P0 |
| E2E-02 | TestDeduplicationLogic | 4 | P0 |
| E2E-03 | TestErrorRecovery | 3 | P1 |
| E2E-04 | TestMultiTableIntegration | 3 | P1 |

---

## TestFullPipelineFlow

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| E2E-01-01 | test_master_then_daily_flow | Mock 主檔 + Mock 日行情 | 成功抓取並寫入 |
| E2E-01-02 | test_cb_master_then_daily_flow | Mock CB主檔 + Mock CB日行情 | 成功抓取並寫入 |
| E2E-01-03 | test_empty_symbol_list | 空 symbol 清單 | 0 items |
| E2E-01-04 | test_statistics_aggregation | 多個 Spider 統計 | 統計正確彙總 |
| E2E-01-05 | test_pipeline_close_integrity | 未關閉的 Pipeline | flush 後資料完整 |

---

## TestDeduplicationLogic

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| E2E-02-01 | test_duplicate_stock_daily | 相同 symbol_date 兩次 | count 不增加 |
| E2E-02-02 | test_duplicate_cb_daily | 相同 cb_code_trade_date 兩次 | count 不增加 |
| E2E-02-03 | test_updated_at_changes | 二次寫入 | updated_at 更新 |
| E2E-02-04 | test_different_dates_no_dedup | 不同日期 | 兩筆記錄 |

---

## TestErrorRecovery

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| E2E-03-01 | test_partial_failure_recovery | 部分失敗 | 成功的繼續寫入 |
| E2E-03-02 | test_network_timeout_retry | 網路超時 | 重試後成功 |
| E2E-03-03 | test_invalid_data_skip | 無效資料 | 跳過並記錄錯誤 |

---

## TestMultiTableIntegration

| 測試ID | 測試名稱 | 輸入 | 預期輸出 |
|--------|----------|------|----------|
| E2E-04-01 | test_stock_and_cb_same_pipeline | 股票 + CB 同 Pipeline | 各自寫入正確表 |
| E2E-04-02 | test_unique_keys_isolated | 不同表的 unique_key | 不會衝突 |
| E2E-04-03 | test_transaction_rollback | 交易失敗 | 無殘留資料 |

---

## 執行指令

```bash
# 執行所有 E2E 測試
pytest tests/test_framework/test_full_system_integration.py -v

# 執行特定測試類別
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow -v

# 產生覆蓋率報告
pytest tests/test_framework/test_full_system_integration.py --cov=src --cov-report=html
```

---

*最後更新：2026-04-16*
