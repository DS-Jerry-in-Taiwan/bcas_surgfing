# Phase 3.0 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 資料庫擴展 + 依賴安裝
- **重點**:
  - 執行 `src/db/init_eod_tables.sql` 建立 4 張新表
  - 更新 `requirements.txt` (numpy, scikit-learn, rich, python-telegram-bot)
  - 建立 `src/analytics/__init__.py`

## 📐 @ARCH
- **職責**: DB Schema 設計 + Item 定義 + 確認遵循既有模式
- **重點**:
  - 只建立必要的 4 張表，不加冗餘表
  - BrokerBreakdownSpider 必須遵循既有 BaseSpider 模式
  - 確保新 Spider 可整合進 run_daily.py

## 💻 @CODER
- **職責**: 爬蟲實作 + Item 擴充 + DDL 撰寫 + 主管道整合
- **重點**:
  - **BrokerBreakdownSpider**: 
    - ✅ `__init__(self, pipeline=None, ...)` 接受 pipeline
    - ✅ `self.items` 命名與既有一致
    - ✅ `self.add_item(item)` 同步呼叫
    - ✅ `get_items()` 回傳 self.items
    - ✅ `get_statistics()` 覆蓋
    - ✅ `collect_only = True`
  - **ITEM_REGISTRY**: 擴充支援 3 個新 Item，不含 SecurityProfileItem
  - **run_daily.py**: 在 step_spiders() 中加入 BrokerBreakdownSpider

## 🧪 @ANALYST
- **職責**: 驗證爬蟲 + DB + 回歸測試
- **重點**:
  - 確認 BrokerBreakdownSpider 使用 add_item() 而非自行管理
  - 確認 ITEM_REGISTRY 只有 7 個 Item (4 既有 + 3 新增)
  - 確認 run_daily.py 有 BrokerBreakdownSpider 的 block
  - 確認既有 4 個爬蟲不受影響
