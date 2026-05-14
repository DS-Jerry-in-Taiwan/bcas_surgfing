# Phase 3.0 - Agent 執行 Prompts

## ⛔ 禁止事項
- **禁止** 建立 `security_profile` 表 (stock_master + cb_master 已足夠)
- **禁止** 建立 `ConversionPriceSpider` (CbMasterSpider 已有 conversion_price)
- **禁止** 使用 `self._items` 命名，必須用 `self.items`
- **禁止** 繞過 `self.add_item(item)`，必須同步呼叫

## @ARCH Prompt
請設計 4 張 DB 表結構：
1. `broker_breakdown` PK(date, symbol, broker_id)
2. `daily_analysis_results` PK(date, symbol)
3. `trading_signals` PK(date, symbol, signal_type)
4. `broker_blacklist` PK(broker_id)
不用 security_profile (stock_master + cb_master 已涵蓋)

## @CODER Prompt - BrokerBreakdownSpider
請實作分點爬蟲，**嚴格遵循既有 BaseSpider 模式**：
```python
# ✅ 正確模式
class BrokerBreakdownSpider(BaseSpider):
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        ...
        for broker in data:
            item = BrokerBreakdownItem(...)
            self.items.append(item)
            self.add_item(item)          # ← 一定要 call！
    
    def get_items(self) -> List[BrokerBreakdownItem]:
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats
```

## @CODER Prompt - run_daily.py 整合
在 `step_spiders()` 中加入 BrokerBreakdownSpider 的 block：
```python
from spiders.broker_breakdown_spider import BrokerBreakdownSpider

# Broker Breakdown
p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
s = BrokerBreakdownSpider(pipeline=p)
s.collect_only = True
try:
    r = s.fetch_broker_breakdown(today_str, "2330")  # 示範用
    results["broker_breakdown"] = {...}
    records["broker_breakdown"] = [...]
    pipelines["broker_breakdown"] = (p, s)
except:
    s.close()
    raise
```

## @CODER Prompt - Item 擴充 (base_item.py)
在 ITEM_REGISTRY 中加入：
```python
"broker_breakdown": BrokerBreakdownItem,
"daily_analysis_results": DailyAnalysisResultItem,
"trading_signals": TradingSignalItem,
```
**不需要** SecurityProfileItem！

## @ANALYST Prompt
驗證：
1. 執行 `python -c "from framework.base_item import get_item_class; print(get_item_class('broker_breakdown'))"` 確認回傳正確
2. 執行 `python -c "from framework.base_item import get_item_class; print(get_item_class('security_profile'))"` 確認拋錯 (不該存在)
3. 檢查 `run_daily.py` 的 step_spiders() 包含 BrokerBreakdownSpider
4. 檢查 BrokerBreakdownSpider 的 source code 是否使用 `add_item()`
5. 執行 `python src/run_daily.py --validate-only` 確認既有流程不受影響
