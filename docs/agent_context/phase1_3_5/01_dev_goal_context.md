# Phase 1.3.5 - 資料清洗與標準化

**階段**: Phase 1.3.5 (Data Cleaning)
**專案**: Project Gamma Surf
**背景**: TPEx 下載的 CSV 包含多行描述文字 (Header Info) 與結尾說明 (Footer)，導致 `pd.read_csv` 解析失敗或欄位對齊錯誤。

## 🎯 開發目標
1.  **清洗器 (Cleaner)**: 實作 `src/etl/cleaner.py`，能自動識別 CSV 的「真實表頭列 (Header Row)」，去除上方雜訊與下方說明，產出標準 CSV。
2.  **流程整合**: 將清洗步驟整合進 `main_crawler.py` 或獨立執行。
3.  **強健入庫**: 更新 `importer.py`，加入 `try-except` 區塊，當單一檔案格式錯誤時，記錄 Error Log 並跳過，而非中斷程式。

### 核心產出
1.  **Cleaner Module**: `src/etl/cleaner.py`。
2.  **Processed Data**: `data/processed/daily/*.csv` (清洗後的檔案)。
3.  **Robust Importer**: 更新後的 `src/etl/importer.py`。

### 驗收標準
- [ ] 清洗後的 CSV 用 Excel 或 Pandas 打開時，第一列即為欄位名稱 (e.g., "代碼", "名稱"...)。
- [ ] `importer.py` 能順利讀取清洗後的檔案並入庫。
- [ ] 若遇到無法清洗的壞檔，程式會輸出 `[ERROR] File {filename} format invalid` 但繼續處理下一個。

