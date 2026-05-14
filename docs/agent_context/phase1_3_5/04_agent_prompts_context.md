# Phase 1.3.5 - Agent 執行 Prompts

## @ARCH Prompt
請設計清洗邏輯：
1. **輸入**: TPEx Raw CSV (含 2-3 行標題, 隨後的空行, 結尾的說明)。
2. **演算法**:
   - 開啟檔案 (`encoding='cp950'` 或 `utf-8-sig`)。
   - 逐行讀取。
   - 若該行包含 "代碼" 或 "證券代號"，標記為 Header。
   - 保留 Header 及之後的行。
   - 對於每一行，移除數值欄位中的 `,` (如 `"1,000"` -> `"1000"`)。
3. **輸出**: UTF-8 編碼的標準 CSV。

## @CODER Prompt
請實作 Cleaner 與強化 Importer：
1. **`src/etl/cleaner.py`**:
   - 實作 `CleanTpexCSV` 類別。
   - 提供 CLI 介面：`python src/etl/cleaner.py --input data/raw/daily --output data/processed/daily`。
2. **`src/etl/importer.py`**:
   - 更新讀取路徑為 `data/processed/daily`。
   - 在 `load_daily_quotes` 迴圈中加入：
     ```python
     try:
         df = pd.read_csv(...)
         # ... 入庫邏輯 ...
     except Exception as e:
         logger.error(f"Failed to import {file}: {e}")
         continue
     ```
3. 確保 Log 格式清晰，方便排查。

## @ANALYST Prompt
請驗證清洗與入庫流程：
1. 執行 Cleaner，檢查 `data/processed` 下的檔案，確認第一行就是欄位名，且數值無逗號。
2. 執行 Importer，確認 DB 成功寫入。
3. **破壞測試**: 故意放一個壞掉的 .txt 檔到 input 目錄，確認 Importer 報錯但未崩潰。

