# Phase 3.0 - EOD 爬蟲擴展 & 資料庫基礎設施架構設計

## 概述
Phase 3.0 為 EOD Analytics System 的基礎建設層。在既有 4 個爬蟲 + PostgreSQL 之上，
新增「券商分點買賣超爬蟲」以及 4 張分析專用資料表，為 Phase 3.1~3.3 鋪路。

## 既有架構
```
src/
├── framework/       BaseSpider, BaseItem, Pipeline, AlertManager ✅
├── spiders/         StockMaster, StockDaily, CbMaster, TpexCbDaily ✅
├── validators/      DataValidator + 8 個規則模組 ✅
├── etl/             Cleaner, Importer ✅
├── run_daily.py     爬蟲→驗證→清洗 主管道 ✅
└── settings/        配置 ✅
```

## ✳️ 設計原則

### 遵循 (Do)
- Spider `__init__` 接受 `pipeline=None` 參數
- 使用 `self.items` + `self.add_item(item)` + `get_items()` 模式
- 使用 `collect_only = True` (與既有 run_daily 一致)
- 在 `run_daily.py` 的 `step_spiders()` 中註冊新爬蟲
- Item 類別註冊至 `ITEM_REGISTRY`

### 不遵循 (Don't)
- **不建立** `ConversionPriceSpider` (CbMasterSpider 已有 conversion_price)
- **不建立** `security_profile` 表 (stock_master + cb_master 已涵蓋)
- **不建立** `SecurityProfileItem` (無對應表)
- **不使用** `self._items` 命名 (與既有 `self.items` 不一致)
- **不繞過** `self.add_item(item)` (否則 flush_items 失效)

## 新增項目

### BrokerBreakdownSpider
- **數據源**: TWSE MI_20S API
- **輸出**: BrokerBreakdownItem → broker_breakdown 表
- **模式**: 遵循既有 BaseSpider 模式

### 4 張新 PostgreSQL 表
```sql
broker_breakdown       PK(date, symbol, broker_id)   -- 券商買賣超
daily_analysis_results PK(date, symbol)               -- 分析結果
trading_signals        PK(date, symbol, signal_type)  -- 交易信號
broker_blacklist       PK(broker_id)                  -- 黑名單
```

### 3 個新 Item (不含 SecurityProfileItem)
- BrokerBreakdownItem
- DailyAnalysisResultItem
- TradingSignalItem

## 資料流
```
17:00 EOD 觸發
  │
  ├─ StockMasterSpider     (既有) 股票主檔
  ├─ StockDailySpider      (既有) 收盤價
  ├─ CbMasterSpider        (既有) CB 主檔 + 轉換價
  ├─ TpexCbDailySpider     (既有) CB 日行情
  └─ BrokerBreakdownSpider (✨新增) 分點明細
       │
       ▼
  既有 5 表 + 新增 4 表 (PostgreSQL)
```

## 目錄結構
```
src/
├── spiders/
│   └── broker_breakdown_spider.py   ✨
├── framework/base_item.py           ⚡ (擴充 3 個 Item)
├── configs/broker_blacklist.json    ✨
└── db/
    ├── init_eod_tables.sql          ✨ (4 張表)
    └── seed_broker_blacklist.sql    ✨
```
