# E2E 全鏈路整合測試規格

## 測試目標

驗證從 Phase 1 到 Phase 3 的完整資料流：

```
BaseSpider -> Item -> PostgresPipeline -> PostgreSQL (去重)
     ^           ^           ^
     |           |           |
  Phase 1    Phase 1     Phase 1
                     
StockMasterSpider -> StockMasterItem -> Pipeline
     ^                  ^              ^
     |                  |              |
  Phase 2            Phase 2        Phase 2
                     
StockDailySpider -> StockDailyItem -> Pipeline
     ^                  ^              ^
     |                  |              |
  Phase 3            Phase 3        Phase 3
```

## 測試情境

### 情境 1: 股票主檔 + 日行情完整流程

1. 抓取股票主檔 (StockMasterSpider)
2. 根據主檔中的 symbol 清單抓取日行情
3. 驗證去重寫入

### 情境 2: 可轉債主檔 + 日行情完整流程

1. 抓取 CB 主檔 (CbMasterSpider)
2. 根據 CB 清單抓取日行情
3. 驗證去重寫入

### 情境 3: 二次執行去重驗證

1. 執行完整流程
2. 再次執行相同流程
3. 驗證記錄數不增加，但 `updated_at` 更新

## 去重驗證

| 資料類型 | Unique Key | 去重行為 |
|---------|------------|----------|
| StockMaster | `{symbol}_{market_type}` | 更新名稱等欄位 |
| CbMaster | `{cb_code}_{underlying_stock}` | 更新到期日等欄位 |
| StockDaily | `{symbol}_{date}` | 更新收盤價等欄位 |
| TpexCbDaily | `{cb_code}_{trade_date}` | 更新收盤價等欄位 |

## 環境依賴

- PostgreSQL 運行中
- 環境變數設定 (.env)
- 測試資料庫隔離

---

*最後更新：2026-04-16*
