# Phase 1.3.4 - TPEx 日行情批量下載與回補

**階段**: Phase 1.3.4 (Batch Download)
**專案**: Project Gamma Surf
**背景**: 目前爬蟲一次只能抓一天。為了建立歷史資料庫，需要能一次抓取一個月或一年的資料。

## 🎯 開發目標
更新 `src/main_crawler.py`，新增 `--start-date` 與 `--end-date` 參數，並實作批量迭代邏輯。

### 核心產出
1.  **Updated CLI**: 支援 `python src/main_crawler.py --task daily --start-date 2024-01-01 --end-date 2024-01-31`。
2.  **Batch Logic**: 
    - 自動迭代日期。
    - **Random Sleep**: 每次請求後隨機暫停 3~10 秒。
    - **Error Handling**: 假日或 404 錯誤不中斷迴圈。
3.  **Verification**: 成功抓取指定區間內的 CSV 檔案。

### 驗收標準
- [ ] 能正確解析區間參數。
- [ ] 執行過程中明顯觀察到間隔停頓 (Sleep)。
- [ ] 遇到假日（TPEx 無資料）時，Log 顯示 "No Data" 或 "Skip" 但程式繼續執行。
- [ ] 資料夾 `data/raw/daily/` 中產生多個日期的 CSV。

