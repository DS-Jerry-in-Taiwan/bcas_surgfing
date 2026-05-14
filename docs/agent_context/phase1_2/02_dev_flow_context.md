# Phase 1.2 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 環境與目錄擴充 (@INFRA)
- 新增 `data/raw/master` 目錄用於存放清單。
- 確認 Python 環境包含 `pandas`, `requests`。

### Step 2: Master Data 架構設計 (@ARCH) -> ⏸️ Checkpoint 1
- 設計 `MasterProvider` 介面：定義 `get_all_stocks()` 與 `get_all_cbs()`。
- 設計清單資料結構：需包含 `symbol`, `name`, `market_type` (上市/上櫃)。
- 規劃標的選擇邏輯：如何從 2000+ 檔中選出測試樣本？

### Step 3: 實作清單與日爬蟲 (@CODER)
- **Task A**: 實作 `fetch_stock_master.py` (證交所/櫃買中心 API)。
- **Task B**: 實作 `fetch_cb_master.py` (櫃買中心 CB 專區)。
- **Task C**: 升級原有的日爬蟲，使其接受 Task A/B 的輸出作為輸入。
- **Task D**: 撰寫 `verify_pipeline.py` 串接上述流程。

### Step 4: 整合驗證 (@ANALYST) -> ⏸️ Checkpoint 2
- 執行 `verify_pipeline.py`。
- 檢查清單完整性：台股是否少於 1000 檔？(異常警告)。
- 檢查 CB 清單：是否有包含 52694 等已知標的？
- 檢查日資料品質：抽樣的 CSV 是否有空值或格式錯誤？

