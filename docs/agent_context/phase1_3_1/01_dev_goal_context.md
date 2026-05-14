# Phase 1.3.1 - 爬蟲流程編排與入口建置

**階段**: Phase 1.3.1 (Crawler Orchestration)
**專案**: Project Gamma Surf
**背景**: 目前爬蟲散落在不同檔案 (`stock_master.py`, `tpex_daily.py` 等)，缺乏統一調度機制。

## 🎯 開發目標
設計並實作爬蟲系統的**入口檔案 (Entry Point)**，定義清晰的**主流程 (Main Flow)**，並透過參數控制要執行哪些模組。

### 核心產出
1.  **Entry Point**: `src/main_crawler.py`。
2.  **Pipeline Logic**: 
    - `run_pipeline(task, date)`: 主控函式。
    - `Task 1`: Update Master Lists (Stock & CB).
    - `Task 2`: Update Daily Quotes (Stock & CB).
3.  **Refactored Modules**: 將原有的爬蟲腳本封裝為可調用的函式 (e.g., `run()`)。

### 驗收標準
- [ ] 能透過單一指令 `python src/main_crawler.py` 觸發爬蟲。
- [ ] 支援參數控制：`--task master` (只跑主檔) / `--task daily` (只跑行情) / `--task all`。
- [ ] 支援指定日期：`--date 2024-01-25`。
- [ ] 主流程能依序呼叫 Phase 1.3 完成的模組，且無 Import Error。

