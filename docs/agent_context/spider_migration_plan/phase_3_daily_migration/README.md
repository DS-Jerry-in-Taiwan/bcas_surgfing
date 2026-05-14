# Phase 3: 日行情爬蟲遷移

## 概述

Phase 3 將現有的日行情爬蟲 (`twse_daily.py`, `tpex_cb_daily.py`) 遷移至 Feapder 框架，實現以下目標：

- 支援「指定日期區間」增量抓取
- 使用 Phase 1 的 `StockDailyItem`、`TpexCbDailyItem` 進行資料標準化
- 透過 `PostgresPipeline` 實現去重入庫
- 整合 Phase 2 的 `StockMasterSpider` 進行 symbol 清單查詢

## 任務邊界

### Phase 3 負責範圍 (日級增量與區間抓取)
- `StockDailySpider`: TWSE 個股日行情
- `TpexCbDailySpider`: TPEx 可轉債日行情
- 日期區間抓取邏輯
- JSON/CSV 解析與欄位映射
- PostgreSQL 去重入庫

### Phase 4 負責範圍 (歷史批次)
- 全市場歷史資料補檔
- 大規模並行抓取優化
- 增量同步策略

### Phase 5 負責範圍 (自動化排程)
- Cron/排程監控
- Slack 告警整合
- 失敗重試機制

## 源碼分析

| 檔案 | API端點 | 資料格式 | 關鍵解析 |
|------|---------|----------|----------|
| `twse_daily.py` | `https://www.twse.com.tw/exchangeReport/STOCK_DAY` | JSON | 民國年轉換 |
| `tpex_cb_daily.py` | `https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php` | CSV | Big5/UTF-8 |

## 技術決策

1. **繼承 BaseSpider**: 統一 Header、Proxy、Retry 策略
2. **Item 標準化**: 使用 Phase 1 定義的 dataclass
3. **去重機制**: unique_key 配合 PostgreSQL `ON CONFLICT DO UPDATE`
4. **日期處理**: 使用現有 `convert_minguo_date` 工具

## 交付物

- [ ] `src/spiders/stock_daily_spider.py`
- [ ] `src/spiders/tpex_cb_daily_spider.py`
- [ ] `tests/test_framework/test_daily_spider.py`
- [ ] 117 單元測試 → 150+ 測試

## 時間線

| 階段 | 預計時間 |
|------|----------|
| StockDailySpider 實作 | 2 小時 |
| TpexCbDailySpider 實作 | 2 小時 |
| 單元測試撰寫 | 2 小時 |
| 整合測試驗證 | 1 小時 |

---

*最後更新：2026-04-16*
