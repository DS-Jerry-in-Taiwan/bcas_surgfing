# Phase 1.3.6 - Agent 執行 Prompts

## @ARCH Prompt
請為 `src/pipeline/daily_update.py` 設計整合架構：
1. 引用所有先前開發的模組。
2. 設計 `PipelineManager` 類別。
3. 定義嚴格的順序：
   - A. 更新 Master List。
   - B. 爬取 Daily Raw Data。
   - C. 清洗 Data (Cleaner)。
   - D. 資料校驗：確認 Daily 中的 Symbol 存在於 Master 表。
   - E. 批次寫入 DB (Importer)。
4. 考慮原子性：任何一步失敗，後續不執行。

## @CODER Prompt
請實作整合管線 `src/pipeline/daily_update.py`:
1. 實作 `argparse` 支援單日與區間同步。
2. 整合 `MasterCrawler`, `DailyCrawler`, `DataCleaner`, `DBImporter`。
3. 實作「主檔自動補齊警告」：
   ```python
   missing = set(daily_df['symbol']) - set(master_df['symbol'])
   if missing:
       logger.warning(f"Found new symbols in daily data: {missing}")

```

4. 確保所有日誌統一輸出到 `logs/pipeline.log`。

## @ANALYST Prompt

請執行全流程驗證：

1. 執行 `python src/pipeline/daily_update.py --date 2024-01-24`。
2. 驗證資料夾 `data/processed/` 是否產生對應檔案。
3. 連線資料庫，執行 SQL 確認：
* `market_master` 與 `market_daily` 的關聯性。
* 資料量是否正確。



