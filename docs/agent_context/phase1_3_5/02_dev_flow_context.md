# Phase 1.3.5 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 分析雜訊結構 (@ARCH) -> ⏸️ Checkpoint 1
- **觀察**: 打開一個 Raw CSV。
- **特徵**: 真實表頭通常包含「代碼」、「證券代號」或「Bond Code」。
- **策略**: 逐行讀取 -> 尋找關鍵字 -> 鎖定 Header 行 -> 保留 Header 與其後的 Data 行 -> 存入 `data/processed`。

### Step 2: 實作清洗器 (@CODER)
- **檔案**: `src/etl/cleaner.py`。
- **功能**:
    - `clean_file(input_path, output_path)`: 執行上述邏輯。
    - `batch_clean(raw_dir, processed_dir)`: 批次處理。
    - 處理千分位逗號：在清洗階段順便將 `"1,234.56"` 轉為 `"1234.56"`。

### Step 3: 強化 Importer (@CODER)
- **修改**: `src/etl/importer.py`。
- **功能**:
    - 改為讀取 `data/processed/daily/`。
    - 在 `pd.read_csv` 外層包裹 `try-except`。
    - 增加 Log：成功印 `[INFO]`，失敗印 `[ERROR]` 及 Traceback。

### Step 4: 整合驗證 (@ANALYST) -> ⏸️ Checkpoint 2
- 執行 `python src/etl/cleaner.py`。
- 檢查 Processed CSV 內容。
- 執行 `python -m src.etl.importer` 確認入庫無誤。

