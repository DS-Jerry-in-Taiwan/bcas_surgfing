# Stage 5: Real E2E Integration Tests — 完成報告

**日期**: 2026-04-30  
**階段**: Stage 5（真實 E2E 整合測試）  
**測試**: 13/13 PASS  

---

## 📊 測試概覽

**13 個真實 E2E 測試**，不打 mock、不造假資料：

| 測試類別 | 測試數 | 驗證內容 |
|----------|--------|----------|
| **stock_master** | 3 | 真 TWSE API 請求 → 6 條規則 → 有 symbols |
| **stock_daily** | 2 | 真 2330 日行情 → 7 條規則 → 價格正性 |
| **cb_master** | 1 | 真 TPEx CB 主檔 → 5 條規則 |
| **tpex_cb_daily** | 1 | 真 CB 日行情 → 6 條規則 |
| **Cross-table 一致性** | 2 | stock↔master consistency, cb_daily↔master consistency |
| **4 表同時驗證** | 1 | 全部 fetch → 全部 validate → 全部 pass |
| **報告產出** | 3 | 目錄、欄位完整、JSON 可序列化 |
| **--validate-only** | 1 | Mock main() + 真 records → exit(0) |

---

## 真實 bug 修復

E2E 測試立刻抓到 3 個真實問題：

| Bug | 發現方式 | 修復 |
|-----|----------|------|
| `tpex_cb_daily` closing_price=0 是 ERROR | 真資料 157 筆 CB 未交易日收盤價 0 | severity WARNING（0 是正常值） |
| `cb_master` conversion_price 字串 `"35.2000"` | rule 用 `<=` 比對字串拋 TypeError | 加 `float()` 轉換 |
| `stock_daily` close_price check 重複條件 | 代碼審查 | 清理邏輯 |

---

## 關鍵架構驗證

collect_only 模式的正確性通過測試驗證：
- Spider fetch 時不寫 DB（Mock pipeline 沒被呼叫 save_items）
- `add_item()` 正確暫存 _pending_items
- `flush_items()` 正確寫入指定 pipeline
- `_pending_items.clear()` 在驗證失敗時正確清空

---

## 版本記錄

- v1.0 (2026-04-30): Mock 接口 E2E（26 tests）
- v2.0 (2026-04-30): 真 API 請求 + 真 DataValidator（13 tests）
