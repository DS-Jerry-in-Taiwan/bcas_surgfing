# Phase 2: Master 資料爬蟲遷移

## 概述

Phase 2 專注於將現有的股票主檔與可轉債主檔爬蟲遷移至 Feapder 框架，確保主檔資料的穩定抓取與入庫。

---

## 目錄結構

```
phase_2_master_migration/
├── README.md                    # 本文件
├── implementation_plan.md      # 實作計畫
├── test_cases.md                # 測試案例
└── DEVELOPER_PROMPT.md          # Developer 工作指引
```

---

## 任務地圖

```
Phase 1 完成                    Phase 2 已完成                  Phase 3
┌──────────────┐    ┌──────────────────────────────────────┐    ┌──────────────┐
│ 框架建設     │───▶│ StockMasterSpider                     │───▶│ 日行情爬蟲   │
│ (已完成)     │    │ CbMasterSpider                        │    │ (待執行)     │
└──────────────┘    │ • TWSE 股票主檔                      │    └──────────────┘
                     │ • TPEx 股票主檔                      │
                     │ • TPEx CB 主檔                      │
                     │ • PostgresPipeline 整合              │
                     └──────────────────────────────────────┘
```

---

## Phase 2 交付物

### Spider 實作

| 檔案 | 說明 | 優先級 |
|------|------|--------|
| `stock_master_spider.py` | 股票主檔爬蟲 (TWSE + TPEx) | 高 |
| `cb_master_spider.py` | 可轉債主檔爬蟲 (TPEx CSV) | 高 |

### 測試檔案

| 檔案 | 測試數 |
|------|--------|
| `test_master_spider.py` | 10+ |

### 文件

| 檔案 | 說明 |
|------|------|
| `implementation_plan.md` | 實作步驟與技術細節 |
| `test_cases.md` | 測試案例定義 |

---

## 實作進度追蹤

### Step 1: StockMasterSpider

- [x] 實作 `fetch_twse()` 方法
- [x] 實作 `fetch_tpex()` 方法
- [x] 實作 `parse_twse_html()` 方法
- [x] 實作 `parse_tpex_html()` 方法
- [x] 整合 Pipeline
- [x] 單元測試

### Step 2: CbMasterSpider

- [x] 實作 `fetch_cb_master()` 方法
- [x] 實作 `parse_cb_csv()` 方法
- [x] Big5 編碼處理
- [x] 整合 Pipeline
- [x] 單元測試

### Step 3: 整合測試

- [x] CSV Pipeline 整合測試
- [x] PostgreSQL 整合測試
- [x] 去重邏輯驗證

---

## 技術參考

### 現有程式碼

- `src/crawlers/master/cb_master.py` - CB Master CSV 下載
- `src/crawlers/master/stock_crawler.py` - 股票主檔抓取

### Phase 1 框架

- `src/framework/base_spider.py` - BaseSpider
- `src/framework/base_item.py` - StockMasterItem, CbMasterItem
- `src/framework/pipelines.py` - PostgresPipeline, CsvPipeline

### 目標資料表

```sql
-- 股票主檔
CREATE TABLE stock_master (
    symbol VARCHAR(10) NOT NULL,
    market_type VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    industry VARCHAR(100),
    listing_date DATE,
    cfi_code VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, market_type)
);

-- 可轉債主檔
CREATE TABLE cb_master (
    cb_code VARCHAR(10) NOT NULL,
    underlying_stock VARCHAR(10) NOT NULL,
    cb_name VARCHAR(100),
    market_type VARCHAR(10),
    issue_date DATE,
    maturity_date DATE,
    conversion_price DECIMAL(10,2),
    coupon_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (cb_code, underlying_stock)
);
```

---

## Phase 邊界定義

### Phase 2 完成項目
- ✅ StockMasterSpider (TWSE + TPEx)
- ✅ CbMasterSpider (TPEx CSV)
- ✅ PostgresPipeline 整合
- ✅ 去重邏輯

### Phase 3 涵蓋
- ⬜ StockDailySpider
- ⬜ TpexCbDailySpider
- ⬜ 批次排程
- ⬜ 增量更新

---

## 下一步

完成 Phase 2 後，進入 [Phase 3: 日行情爬蟲遷移](../phase_3_daily_migration/)

---

*文件版本：1.0.0*
*最後更新：2026-04-16 (100% 完成)*
