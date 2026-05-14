# Phase 3.0 - EOD 爬蟲擴展 & 資料庫基礎設施

**階段**: Phase 3.0 (EOD Infrastructure)
**專案**: BCAS Quant v3.0.0 → EOD Analytics 擴展

**背景**: 
既有系統已具備 4 個爬蟲 (StockMaster, StockDaily, CbMaster, TpexCbDaily) 與 PostgreSQL，
但缺少 EOD Analytics 所需的「券商分點買賣超」資料來源與 4 張分析專用資料表。

## 🎯 開發目標

1. **BrokerBreakdownSpider**: 抓取 TWSE 前五大買賣超券商分點明細
2. **資料庫擴展**: 建立 4 張新表 (broker_breakdown, daily_analysis_results, trading_signals, broker_blacklist)
3. **Item 擴展**: 新增 3 個 Item 類別並註冊至 ITEM_REGISTRY
4. **broker_blacklist.json 初始化**: 建立知名短線客券商清單
5. **requirements.txt 更新**: 加入 numpy, scikit-learn, rich, python-telegram-bot

### ✳️ 設計原則

1. **遵循既有 BaseSpider 模式**: `__init__(self, pipeline=None, ...)` + `self.items` + `self.add_item(item)` + collect_only 模式
2. **不重複既有功能**: `CbMasterSpider` 已提供 `conversion_price`，不另做 ConversionPriceSpider
3. **不新增冗餘表**: `stock_master` + `cb_master` 已涵蓋證券主檔，不另做 security_profile
4. **整合進主管道**: 新爬蟲必須加入 `run_daily.py` 的 `step_spiders()`

### 核心產出

| 產出 | 說明 |
|------|------|
| `src/spiders/broker_breakdown_spider.py` | 分點買賣超爬蟲 (遵循既有 BaseSpider 模式) |
| `src/db/init_eod_tables.sql` | 4 張新表 DDL |
| `src/db/seed_broker_blacklist.sql` | 黑名單種子資料 |
| `src/framework/base_item.py` (擴充) | 新增 3 個 Item 類 |
| `src/configs/broker_blacklist.json` | 初始券商黑名單 |

### 驗收標準

- [ ] BrokerBreakdownSpider 使用 `BaseSpider.__init__(pipeline=...)` 模式
- [ ] BrokerBreakdownSpider 使用 `self.add_item(item)` 而非自行管理 list
- [ ] BrokerBreakdownSpider 已加入 `run_daily.py` 的 `step_spiders()`
- [ ] 4 張新表 DDL 執行成功 (psql -f)
- [ ] 3 個 Item 類註冊至 ITEM_REGISTRY 且 `get_item_class()` 可正確查詢
- [ ] 黑名單 JSON 格式正確 (≥10 筆)
- [ ] 既有 4 個爬蟲不受影響
