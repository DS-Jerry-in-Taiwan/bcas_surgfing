# Phase 1.2 - Agent 執行 Prompts

## @INFRA Prompt
請擴充專案結構：
1. 建立 `data/raw/master` 目錄。
2. 更新 `.gitignore` 確保 master csv 被追蹤但 daily csv 被忽略 (視需求而定，通常 raw data 不進 git)。
3. 確認 `requirements.txt` 完整。

## @ARCH Prompt
請設計「標的探索」架構：
1. 設計 `MasterCrawler` 類別，需支援 `fetch_list()`。
2. 上市 (TWSE) 與上櫃 (TPEx) 的清單來源不同，請設計 `StockMasterAggregator` 來合併兩者。
3. 設計 `TargetSelector` 模組，輸入 master list，輸出 `sample_targets` (例如：隨機 5 檔 + 指定 2330, 52694)。
4. 輸出架構設計 MD 檔。

## @CODER Prompt
請實作標的獲取與驗證流程：
1. 實作 `src/crawlers/master/stock_crawler.py`: 抓取台股代碼表。
2. 實作 `src/crawlers/master/cb_crawler.py`: 抓取可轉債代碼表。
3. 更新 `src/crawlers/daily/` 下的爬蟲，改為接受 `symbol` 參數。
4. 撰寫 `scripts/run_validation_pipeline.py`：
   - Step 1: 抓全清單。
   - Step 2: 挑選 [2330, 52694] + 隨機 3 檔。
   - Step 3: 爬取這 5 檔的日資料。
   - Step 4: 驗證檔案存在且非空。

## @ANALYST Prompt
請執行驗證管線並分析：
1. 執行 `scripts/run_validation_pipeline.py`。
2. 檢查 `data/raw/master/stock_list.csv` 是否超過 1700 筆？
3. 檢查 `data/raw/master/cb_list.csv` 是否超過 200 筆？
4. 打開抓下來的 52694 (CB) 資料，確認是否有 Open/High/Low/Close/Volume。
5. 產出 `docs/target_discovery_report.md`。

