# Phase 3.0 - 檢查點協議

## ⏸️ Checkpoint 1: Item 擴充 + DB 表建立
**條件**: 
  - 4 張表 DDL 執行成功 (不含 security_profile)
  - 3 個 Item 類已加入 ITEM_REGISTRY (不含 SecurityProfileItem)
**驗證指令**:
```bash
# Item 查詢
python -c "
from framework.base_item import get_item_class
print(get_item_class('broker_breakdown'))     # 應顯示 BrokerBreakdownItem
print(get_item_class('security_profile'))     # 應拋 KeyError
print(len(get_item_class.__globals__['ITEM_REGISTRY']))  # 應為 7
"
# DB 確認
psql -d cbas -c "\dt broker_breakdown daily_analysis_results trading_signals broker_blacklist"
psql -d cbas -c "\dt security_profile"  # 應顯示 "Did not find any relation"
```
**通過與否**: [ ] 通過 / [ ] 未通過
**簽署人**: 

## ⏸️ Checkpoint 2: Spider 模式合規 + 主管道整合
**條件**: 
  - BrokerBreakdownSpider 使用 `add_item()` + `self.items`
  - BrokerBreakdownSpider 已加入 run_daily.py step_spiders()
**驗證指令**:
```bash
# 檢查 add_item 使用
grep -n "add_item\|self.items" src/spiders/broker_breakdown_spider.py
# 檢查 run_daily 整合
grep -n "BrokerBreakdown\|broker_breakdown" src/run_daily.py
# 回歸測試
python src/run_daily.py --validate-only
```
**通過與否**: [ ] 通過 / [ ] 未通過
**簽署人**: 

## ✅ Phase 3.0 完成條件
- [ ] DB 4 張表全部建立 (無 security_profile)
- [ ] 3 個 Item 註冊至 ITEM_REGISTRY (無 SecurityProfileItem)
- [ ] BrokerBreakdownSpider 模式合規 (add_item + items + pipeline)
- [ ] BrokerBreakdownSpider 已整合進 run_daily.py
- [ ] 黑名單已初始化 (≥10 筆)
- [ ] requirements.txt 已更新
- [ ] 既有爬蟲回歸測試通過
→ **可進入 Phase 3.1**

**Phase Lead 簽署**: 
**日期**: 
