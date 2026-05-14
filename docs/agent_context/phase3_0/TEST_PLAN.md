# Phase 3.0 Test Plan

## 需要測試的項目

### 1. BrokerBreakdownSpider 單元測試
- [ ] `__init__` 接受 `pipeline=None` 參數
- [ ] `self.items` 初始化為空 list
- [ ] `collect_only` 預設為 True
- [ ] `fetch_broker_breakdown()` 成功解析 buyTop5/sellTop5
- [ ] 成功時 `add_item()` 被正確呼叫 (每筆資料)
- [ ] `get_items()` 回傳正確數量的 items
- [ ] `get_statistics()` 包含 total_items
- [ ] API 回傳 stat != "OK" 時回傳 success=False
- [ ] 網路錯誤時回傳 success=False (不拋錯)
- [ ] JSON 解析錯誤時回傳 success=False (不拋錯)

### 2. base_item.py 新 Item 單元測試
- [ ] BrokerBreakdownItem 實例化 + get_unique_key()
- [ ] DailyAnalysisResultItem 實例化 + get_unique_key()
- [ ] TradingSignalItem 實例化 + get_unique_key()
- [ ] ITEM_REGISTRY 正確註冊 3 個新 Item
- [ ] `get_item_class("broker_breakdown")` 回傳正確
- [ ] `get_item_class("security_profile")` 拋 KeyError (不該存在)
- [ ] ITEM_REGISTRY 總長度為 7

### 3. BrokerBreakdownSpider 整合測試 (run_daily.py)
- [ ] `step_spiders()` 中有 broker_breakdown 的處理 block
- [ ] block 中使用 PostgresPipeline + BrokerBreakdownSpider
- [ ] 使用 collect_only = True
- [ ] try/except 模式與其他 4 個蜘蛛一致

### 4. DB init_eod_tables.sql 語法驗證
- [ ] SQL 語法正確 (可被 psql 解析)
- [ ] 4 張表 (不含 security_profile)
- [ ] 每個表都有 PRIMARY KEY
- [ ] 有正確的 INDEX
