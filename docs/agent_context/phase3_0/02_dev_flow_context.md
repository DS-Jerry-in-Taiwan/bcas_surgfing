# Phase 3.0 - 開發流程

## 📅 執行步驟

### Step 1: DB Schema 設計與建立 (@ARCH → @INFRA)
**動作**: 
  - 建立 `src/db/init_eod_tables.sql` (4 張表 DDL)
  - 建立 `src/db/seed_broker_blacklist.sql` (黑名單 seed)
  - 執行 `psql -d cbas -f src/db/init_eod_tables.sql`
**注意**: 不建立 security_profile (stock_master + cb_master 已涵蓋)
**驗證**: `\dt broker_breakdown daily_analysis_results trading_signals broker_blacklist`

### Step 2: Item 類別擴充 (@CODER) → ⏸️ Checkpoint 1
**動作**: 在 `src/framework/base_item.py` 新增 3 個 Item 類
  - `BrokerBreakdownItem` → `__table_name__ = "broker_breakdown"`
  - `DailyAnalysisResultItem` → `__table_name__ = "daily_analysis_results"`
  - `TradingSignalItem` → `__table_name__ = "trading_signals"`
**注意**: 不建立 SecurityProfileItem (CbMasterItem + StockMasterItem 已涵蓋)
**重點**: 需註冊至 ITEM_REGISTRY，確保 `get_item_class()` 可正確查詢

### Step 3: BrokerBreakdownSpider 實作 (@CODER)
**動作**: 建立 `src/spiders/broker_breakdown_spider.py`
**API**: TWSE MI_20S (需確認可用端點)
**必須遵循既有模式**:
```python
# ✅ 遵循既有模式
class BrokerBreakdownSpider(BaseSpider):
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
    
    def fetch_broker_breakdown(self, date, symbol):
        ...
        for broker in data:
            item = BrokerBreakdownItem(...)
            self.items.append(item)     # ✅ 存在 self.items
            self.add_item(item)         # ✅ 同步 call add_item()
    
    def get_items(self):
        return self.items              # ✅ 與既有模式一致
    
    def get_statistics(self):
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats                   # ✅ 與既有模式一致
```

### Step 4: 黑名單初始化 (@CODER/@INFRA)
**動作**:
  - `src/configs/broker_blacklist.json` (≥10 筆知名短線券商)
  - 更新 `requirements.txt`
  - 建立 `src/analytics/__init__.py`

### Step 5: 整合進 run_daily.py (@CODER) → ⏸️ Checkpoint 2
**動作**: 在 `run_daily.py` 的 `step_spiders()` 中加入 BrokerBreakdownSpider
```python
def step_spiders():
    from spiders.broker_breakdown_spider import BrokerBreakdownSpider
    ...
    # Broker Breakdown
    p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
    s = BrokerBreakdownSpider(pipeline=p)
    s.collect_only = True
    try:
        r = s.fetch_broker_breakdown(today_str, symbol)
        results["broker_breakdown"] = {
            "success": r.success,
            "count": r.data.get("count", 0) if r.data else 0,
            "error": r.error,
        }
        records["broker_breakdown"] = [item.to_dict() for item in s.get_items()]
        pipelines["broker_breakdown"] = (p, s)
    except:
        s.close()
        raise
```

### Step 6: 整合驗證 (@ANALYST)
**測試**:
  1. 確認 4 張表全部建立成功
  2. 確認 BrokerBreakdownSpider 使用 `add_item()` + `self.items`
  3. 確認 BrokerBreakdownSpider 已加入 `step_spiders()`
  4. 確認 3 個 Item 類可正確寫入 DB
  5. 確認既有 4 個爬蟲不受影響 (回歸測試)
  6. 確認黑名單 JSON 可載入

## ⏰ 預估工時: 12-18 小時
