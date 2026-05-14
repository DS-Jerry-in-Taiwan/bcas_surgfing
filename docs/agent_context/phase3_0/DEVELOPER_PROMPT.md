# Phase 3.0 Developer Prompt - EOD 爬蟲擴展 & DB 基礎設施

## 🎯 任務概述
在 BCAS Quant v3.0.0 既有系統上，新增券商分點買賣超爬蟲與 4 張分析專用資料表。

## ✳️ 開發原則 (必須遵守)

### ✅ 遵循既有模式 (Do)
- Spider `__init__` 接受 `pipeline=None` 參數
- Item 儲存在 `self.items` list 中
- 同步呼叫 `self.add_item(item)` (讓 BaseSpider 也存一份)
- 實作 `get_items()` 回傳 `self.items`
- 實作 `get_statistics()` 覆蓋
- 使用 `collect_only = True`
- 在 `run_daily.py` 的 `step_spiders()` 中註冊

### ❌ 禁止做的事 (Don't)
- **禁止** 建立 `ConversionPriceSpider` (CbMasterSpider 已有 conversion_price)
- **禁止** 建立 `security_profile` 表 (用 stock_master + cb_master 即可)
- **禁止** 建立 `SecurityProfileItem` (無對應表)
- **禁止** 使用 `self._items` 命名 (必須用 `self.items`)
- **禁止** 繞過 `self.add_item(item)` (否則 flush_items 失效)

## 📁 既有系統架構

### 目錄結構
```
src/
├── framework/
│   ├── base_spider.py       BaseSpider (collect_only 支援)
│   ├── base_item.py         BaseItem + 7 個 Item + ITEM_REGISTRY
│   ├── pipelines.py         PostgresPipeline, CsvPipeline, MemoryPipeline
│   └── alerts.py            AlertManager + SlackAlertBackend
├── spiders/
│   ├── stock_master_spider.py   ✅ 既有 (接受 pipeline)
│   ├── stock_daily_spider.py    ✅ 既有
│   ├── cb_master_spider.py      ✅ 既有 (已有 conversion_price)
│   └── tpex_cb_daily_spider.py  ✅ 既有 (已有 premium_rate)
├── validators/              DataValidator + 8 規則模組
├── etl/                     Cleaner, Importer
├── run_daily.py             主管道 (spider→validate→clean)
└── configs/                 設定檔
```

### BaseSpider 正確使用模式
```python
# ✅ 既有爬蟲的正確模式
class StockMasterSpider(BaseSpider):
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline                         # 保存 pipeline
        self.items: List[StockMasterItem] = []            # ✅ self.items
        self.collect_only = True

    def fetch_something(self):
        ...
        for data in result:
            item = StockMasterItem(...)
            self.items.append(item)                       # ✅ 存一份
            self.add_item(item)                           # ✅ 同步 call add_item()

    def get_items(self):
        return self.items                                 # ✅ get_items()

    def get_statistics(self):
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats
```

## 📋 實作項目

### 1. src/db/init_eod_tables.sql — 4 張新表 DDL

```sql
-- 1. 券商買賣超明細
CREATE TABLE IF NOT EXISTS broker_breakdown (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    broker_id VARCHAR(16) NOT NULL,
    broker_name VARCHAR(64),
    buy_volume BIGINT DEFAULT 0,
    sell_volume BIGINT DEFAULT 0,
    net_volume BIGINT DEFAULT 0,
    rank INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, broker_id)
);

-- 2. 盤後分析結果
CREATE TABLE IF NOT EXISTS daily_analysis_results (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    close_price NUMERIC(10,2),
    conversion_value NUMERIC(10,2),
    premium_ratio NUMERIC(6,4),
    technical_signal VARCHAR(32),
    risk_score NUMERIC(3,1),
    risk_level VARCHAR(16),
    broker_risk_pct NUMERIC(5,2),
    final_rating VARCHAR(16),
    is_junk BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol)
);

-- 3. 交易信號
CREATE TABLE IF NOT EXISTS trading_signals (
    date DATE NOT NULL,
    symbol VARCHAR(16) NOT NULL,
    signal_type VARCHAR(32) NOT NULL,
    confidence NUMERIC(3,2),
    entry_range TEXT,
    stop_loss NUMERIC(10,2),
    target_price NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, signal_type)
);

-- 4. 券商黑名單
CREATE TABLE IF NOT EXISTS broker_blacklist (
    broker_id VARCHAR(16) PRIMARY KEY,
    broker_name VARCHAR(64) NOT NULL,
    category VARCHAR(32),
    risk_level VARCHAR(16) DEFAULT 'HIGH',
    notes TEXT,
    added_date DATE DEFAULT CURRENT_DATE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_broker_breakdown_date ON broker_breakdown(date);
CREATE INDEX IF NOT EXISTS idx_broker_breakdown_symbol ON broker_breakdown(symbol);
CREATE INDEX IF NOT EXISTS idx_daily_analysis_date ON daily_analysis_results(date);
CREATE INDEX IF NOT EXISTS idx_trading_signals_date ON trading_signals(date);
```

### 2. src/framework/base_item.py 擴充 — 新增 3 個 Item 類

```python
@dataclass
class BrokerBreakdownItem(BaseItem):
    __table_name__: str = "broker_breakdown"
    date: str = ""
    symbol: str = ""
    broker_id: str = ""
    broker_name: str = ""
    buy_volume: int = 0
    sell_volume: int = 0
    net_volume: int = 0
    rank: int = 0
    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}_{self.broker_id}"

@dataclass
class DailyAnalysisResultItem(BaseItem):
    __table_name__: str = "daily_analysis_results"
    date: str = ""
    symbol: str = ""
    close_price: float = 0.0
    conversion_value: float = 0.0
    premium_ratio: float = 0.0
    technical_signal: str = ""
    risk_score: float = 0.0
    risk_level: str = ""
    broker_risk_pct: float = 0.0
    final_rating: str = ""
    is_junk: bool = False
    notes: str = ""
    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}"

@dataclass
class TradingSignalItem(BaseItem):
    __table_name__: str = "trading_signals"
    date: str = ""
    symbol: str = ""
    signal_type: str = ""
    confidence: float = 0.0
    entry_range: str = ""
    stop_loss: float = 0.0
    target_price: float = 0.0
    notes: str = ""
    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}_{self.signal_type}"
```

ITEM_REGISTRY 更新：
```python
ITEM_REGISTRY: Dict[str, Type[BaseItem]] = {
    "stock_daily": StockDailyItem,
    "tpex_cb_daily": TpexCbDailyItem,
    "stock_master": StockMasterItem,
    "cb_master": CbMasterItem,
    "broker_breakdown": BrokerBreakdownItem,
    "daily_analysis_results": DailyAnalysisResultItem,
    "trading_signals": TradingSignalItem,
}
# 注意: 共 7 個 Item，不包含 SecurityProfileItem
```

### 3. src/spiders/broker_breakdown_spider.py — 分點爬蟲

**必須遵循 BaseSpider 既有模式！**

```python
"""
TWSE 券商分點買賣超爬蟲
"""
from typing import List, Dict, Any, Optional
from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import BrokerBreakdownItem


class BrokerBreakdownSpider(BaseSpider):
    """
    券商分點買賣超爬蟲
    
    Attributes:
        API_BASE: TWSE API URL
        pipeline: 資料寫入管道
        items: BrokerBreakdownItem 列表
    """
    
    API_BASE = "https://www.twse.com.tw/rwd/zh/trading/mi_sel_pls/MI_20S"
    
    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
    
    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """抓取指定日期/股票的分點買賣超"""
        import requests
        
        url = f"{self.API_BASE}?date={date}&stockNo={symbol}&response=json"
        
        try:
            resp = requests.get(url, headers=self.make_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            self.items.clear()
            
            if data.get("stat") != "OK":
                return SpiderResponse(success=False, error=data.get("errmsg"), url=url)
            
            # 解析 buyTop5
            for rank, broker in enumerate(data.get("buyTop5", []), 1):
                item = BrokerBreakdownItem(
                    date=date, symbol=symbol,
                    broker_id=str(broker.get("broker_id", "")),
                    broker_name=broker.get("broker_name", ""),
                    buy_volume=int(broker.get("buy_volume", 0) or 0),
                    sell_volume=int(broker.get("sell_volume", 0) or 0),
                    net_volume=int(broker.get("net_volume", 0) or 0),
                    rank=rank,
                    source_type="twse", source_url=url,
                )
                self.items.append(item)       # ✅ 存一份
                self.add_item(item)           # ✅ 同步 call add_item()
            
            # 解析 sellTop5
            for rank, broker in enumerate(data.get("sellTop5", []), 6):
                item = BrokerBreakdownItem(
                    date=date, symbol=symbol,
                    broker_id=str(broker.get("broker_id", "")),
                    broker_name=broker.get("broker_name", ""),
                    buy_volume=int(broker.get("buy_volume", 0) or 0),
                    sell_volume=int(broker.get("sell_volume", 0) or 0),
                    net_volume=int(broker.get("net_volume", 0) or 0),
                    rank=rank,
                    source_type="twse", source_url=url,
                )
                self.items.append(item)
                self.add_item(item)
            
            return SpiderResponse(success=True, data={"count": len(self.items)}, url=url)
            
        except Exception as e:
            return SpiderResponse(success=False, error=str(e), url=url)
    
    def get_items(self) -> List[BrokerBreakdownItem]:
        return self.items
    
    def get_statistics(self) -> Dict[str, Any]:
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats


# CLI
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    
    spider = BrokerBreakdownSpider()
    result = spider.fetch_broker_breakdown(args.date, args.symbol)
    print(f"Success: {result.success}, Items: {len(spider.get_items())}")
```

### 4. run_daily.py 整合 (step_spiders 新增 block)

```python
# 在 step_spiders() 中加入:
from spiders.broker_breakdown_spider import BrokerBreakdownSpider

# Broker Breakdown
p = PostgresPipeline(table_name="broker_breakdown", batch_size=500, **DB_CONFIG)
s = BrokerBreakdownSpider(pipeline=p)
s.collect_only = True
try:
    r = s.fetch_broker_breakdown(today_str, "2330")
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

### 5. src/configs/broker_blacklist.json

```json
[
  {"broker_id": "9200", "broker_name": "凱基-台北", "risk_level": "HIGH", "category": "DAY_TRADER"},
  {"broker_id": "9800", "broker_name": "元大-台北", "risk_level": "HIGH", "category": "DAY_TRADER"},
  ...
]
```

### 6. requirements.txt 更新
```
numpy>=1.24.0
scikit-learn>=1.3.0
rich>=13.0.0
python-telegram-bot>=20.0
```

## ✅ 驗收清單

### 模式合規檢查
- [ ] BrokerBreakdownSpider.__init__ 接受 `pipeline=None`
- [ ] BrokerBreakdownSpider 使用 `self.items` (不是 `self._items`)
- [ ] BrokerBreakdownSpider 使用 `self.add_item(item)`
- [ ] BrokerBreakdownSpider 有 `get_items()` 和 `get_statistics()`
- [ ] BrokerBreakdownSpider 使用 `collect_only = True`

### 無冗餘
- [ ] 沒有 `ConversionPriceSpider`
- [ ] 沒有 `security_profile` 表
- [ ] 沒有 `SecurityProfileItem`
- [ ] ITEM_REGISTRY 長度 = 7

### 整合
- [ ] `step_spiders()` 有 broker_breakdown block
- [ ] `python src/run_daily.py --validate-only` 正常

## 📋 檔案變更清單
```
CREATE:
  src/db/init_eod_tables.sql           (4 張表，非 5 張)
  src/db/seed_broker_blacklist.sql
  src/spiders/broker_breakdown_spider.py
  src/configs/broker_blacklist.json

MODIFY:
  src/framework/base_item.py           (+3 Item，非 4 個)
  src/run_daily.py                     (step_spiders 加 broker_breakdown)
  requirements.txt
```
