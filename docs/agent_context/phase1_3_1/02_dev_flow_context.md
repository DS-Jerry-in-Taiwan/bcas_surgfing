# Phase 1.3.1 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 入口架構設計 (@ARCH) -> ⏸️ Checkpoint 1
- **定義主流程**: 
    1. 解析 CLI 參數 (argparse)。
    2. 初始化 Logger (將輸出寫入 `logs/crawler.log` 與 Console)。
    3. 路由邏輯：根據 `task` 參數決定呼叫哪些子模組。
- **介面規範**: 要求子模組必須提供 `run(**kwargs)` 函式。

### Step 2: 模組重構 (@CODER)
- **目標**: 修改 `src/crawlers/master/*.py` 與 `src/crawlers/daily/*.py`。
- **動作**: 
    - 將原本直接執行的 `if __name__ == "__main__":` 邏輯移入 `def run():`。
    - 確保模組被 import 時不會自動執行。

### Step 3: 實作入口檔案 (@CODER)
- **檔案**: `src/main_crawler.py`。
- **功能**:
    - 實作 `setup_logging()`。
    - 實作 `main()` 解析參數。
    - 實作 `run_tasks()` 進行調度。

### Step 4: 整合測試 (@ANALYST) -> ⏸️ Checkpoint 2
- 測試指令：
    1. `python src/main_crawler.py --task master`
    2. `python src/main_crawler.py --task daily --date 2024-01-20`
- 驗證 Log 檔是否有正確的執行紀錄。

