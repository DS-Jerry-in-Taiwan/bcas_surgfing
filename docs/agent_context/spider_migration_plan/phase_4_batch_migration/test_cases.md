# Phase 4 測試案例

## 測試檔案結構

```
tests/test_framework/
├── test_batch_spider.py           # 新增: 批次爬蟲測試
│   ├── TestBatchSpider
│   ├── TestCheckpointManager
│   └── TestConcurrency
```

## 測試清單

### TestBatchSpider

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| BATCH-01 | test_initialization | 正確初始化 |
| BATCH-02 | test_backfill_single_symbol | 單一股票補檔 |
| BATCH-03 | test_backfill_multiple_symbols | 多股票批次 |
| BATCH-04 | test_progress_tracking | 進度追蹤 |

### TestCheckpointManager

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| CHECK-01 | test_load_empty_checkpoint | 空斷點載入 |
| CHECK-02 | test_mark_completed | 標記完成 |
| CHECK-03 | test_is_completed | 檢查完成狀態 |
| CHECK-04 | test_get_pending | 取得待處理清單 |
| CHECK-05 | test_save_and_load | 保存與載入 |
| CHECK-06 | test_reset | 重置斷點 |

### TestConcurrency

| 測試ID | 測試名稱 | 預期行為 |
|--------|----------|----------|
| CONC-01 | test_thread_pool | 執行緒池控制 |
| CONC-02 | test_rate_limiting | 速率限制 |
| CONC-03 | test_error_handling | 並發錯誤處理 |

---

*最後更新：2026-04-16*
