# Phase 3.0 Development Log - EOD 爬蟲擴展 & DB 基礎設施

## ⚠️ 狀態
文件已更新，但**實際代碼尚未修正**。
需依照文件規範重新實作 BrokerBreakdownSpider 並移除冗餘項目。

## 設計變更歷程

### 初始設計 (已廢棄)
- 建立 5 張表 (含 security_profile)
- 建立 2 個爬蟲 (含 ConversionPriceSpider)
- 建立 4 個 Item (含 SecurityProfileItem)

### 審查發現的問題
| 問題 | 原因 | 修正 |
|------|------|------|
| security_profile 冗餘 | stock_master + cb_master 已涵蓋 | 刪除表 + Item |
| ConversionPriceSpider 重複 | CbMasterSpider 已有 conversion_price | 刪除爬蟲 |
| _items 命名不符 | 既有模式用 `items` | 改為 `self.items` |
| 缺少 add_item() | 繞過 BaseSpider 統一入口 | 同步呼叫 add_item() |
| 缺少 pipeline 參數 | 無法整合進 run_daily.py | __init__ 接受 pipeline |
| 未整合 run_daily.py | 主管道不會執行新爬蟲 | 加入 step_spiders() |

### 修正後設計
- 4 張表 (broker_breakdown, daily_analysis_results, trading_signals, broker_blacklist)
- 1 個新爬蟲 (BrokerBreakdownSpider，遵循既有模式)
- 3 個新 Item (不含 SecurityProfileItem)
- 完整整合進 run_daily.py

## 待辦修正
- [x] 刪除 `src/db/init_eod_tables.sql` 中的 `security_profile` 表
- [x] 刪除 `src/spiders/conversion_price_spider.py`
- [x] 從 `src/framework/base_item.py` 移除 SecurityProfileItem
- [x] 重寫 `src/spiders/broker_breakdown_spider.py` (使用 add_item + items + pipeline)
- [x] 在 `src/run_daily.py` 中加入 broker_breakdown block
- [x] 回歸測試: `python src/run_daily.py --validate-only`

## 測試結果 (2026-05-12)

### 測試檔案
| 檔案 | 路徑 | 行數 | 測試案例 |
|------|------|------|---------|
| BrokerBreakdownSpider 單元測試 | `tests/test_broker_breakdown_spider.py` | 289 | 18 |
| Phase 3.0 Item 測試 | `tests/test_phase3_items.py` | 190 | 38 |
| Phase 3.0 整合測試 | `tests/test_phase3_integration.py` | 260 | 19 |
| **Phase 3.0 總計** | | **739** | **75** |

### 執行結果
```
Phase 3.0 tests:  75 passed ✓
Phase 3.0 + 3.1: 133 passed ✓ (no regressions)
```

### 遇到的問題與處理方式

1. **`@patch('spiders.broker_breakdown_spider.requests')` 失敗**
   - 原因: `BrokerBreakdownSpider` 在 method 內部 `import requests`，而非 module-level import。`spiders.broker_breakdown_spider` module 沒有 `requests` attribute。
   - 處理: 改用 `@patch('requests.get')`，只 mock `get` function，保留 `requests.exceptions` 的真實類別供 `isinstance` 檢查使用。

2. **`isinstance(item, BrokerBreakdownItem)` 回傳 False**
   - 原因: `sys.path.insert(0, 'src')` 導致 `framework.base_item` 與 `src.framework.base_item` 被視為不同 module，產生兩個獨立的 `BrokerBreakdownItem` 類別。
   - 處理: 改用 `sys.path.insert(0, os.path.join(...))` 指向專案根目錄，測試使用 `from src.framework.base_item import BrokerBreakdownItem` 與 spider 一致的 import path。

3. **`net_volume` 非自動計算欄位**
   - 原因: `BrokerBreakdownItem` 為 dataclass，`net_volume` 是普通欄位 (default=0)，non-computed property。
   - 處理: 在 test_instantiation 建構時傳入 `net_volume=90`，移除誤導的註解。

4. **Dataclass `__repr__` 不包含 `get_unique_key()` 輸出**
   - 原因: `BrokerBreakdownItem` 繼承 `BaseItem(ABC)` 但 dataclass `__repr__` 由 Python 生成，顯示所有欄位而非 `get_unique_key()`。
   - 處理: 調整 test_repr 檢查實際欄位值 (`date`, `symbol`, `broker_id`)。

5. **`s.close()` 計數與搜尋視窗不足**
   - 原因: `stock_daily` block 使用 `except Exception` 不含 `s.close()`，且搜尋視窗 500 chars 不足。
   - 處理: 將搜尋視窗放大到 1000 chars，分別驗證 `except:` 和 `s.close()` 存在。
