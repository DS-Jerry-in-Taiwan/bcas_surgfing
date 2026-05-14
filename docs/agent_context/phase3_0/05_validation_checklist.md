# Phase 3.0 - 驗證清單

## ✅ DB Schema (4 張表，不含 security_profile)
- [ ] `broker_breakdown` 表建立成功，PK(date, symbol, broker_id)
- [ ] `daily_analysis_results` 表建立成功，PK(date, symbol)
- [ ] `trading_signals` 表建立成功，PK(date, symbol, signal_type)
- [ ] `broker_blacklist` 表建立成功，PK(broker_id)
- [ ] 所有表皆有正確的 INDEX
- [ ] `security_profile` **不存在** (確認沒有多餘的表)

## ✅ Item 類別 (3 個新增，不含 SecurityProfileItem)
- [ ] BrokerBreakdownItem 可正確實例化
- [ ] DailyAnalysisResultItem 可正確實例化
- [ ] TradingSignalItem 可正確實例化
- [ ] `get_item_class("broker_breakdown")` 回傳正確
- [ ] `get_item_class("security_profile")` **拋出 KeyError** (不該註冊)
- [ ] ITEM_REGISTRY 長度 = 7 (4 既有 + 3 新增)

## ✅ BrokerBreakdownSpider - 模式合規檢查
- [ ] `__init__` 接受 `pipeline=None` 參數
- [ ] 使用 `self.items` 命名 (非 `self._items`)
- [ ] 使用 `self.add_item(item)` 同步呼叫
- [ ] 使用 `get_items()` 回傳 `self.items`
- [ ] 使用 `get_statistics()` 覆蓋
- [ ] 使用 `collect_only = True`
- [ ] 不使用自行管理的 `_pending_items` 或 `_items` list

## ✅ run_daily.py 整合
- [ ] `step_spiders()` 匯入 `BrokerBreakdownSpider`
- [ ] `step_spiders()` 有 broker_breakdown 的處理 block
- [ ] block 模式與其他 4 個既有爬蟲一致 (Pipeline + Spider + collect_only + try/except)

## ✅ 黑名單
- [ ] broker_blacklist.json 格式正確
- [ ] 至少有 10 個知名短線券商分點

## ✅ 回歸測試
- [ ] 既有 stock_master_spider 不受影響
- [ ] 既有 stock_daily_spider 不受影響
- [ ] 既有 cb_master_spider 不受影響
- [ ] 既有 tpex_cb_daily_spider 不受影響
- [ ] `python src/run_daily.py --validate-only` 正常執行
