# Phase 1.2 - 標的探索與驗證

**階段**: Phase 1.2 (Target Discovery & Verified Crawling)
**專案**: Project Gamma Surf
**關聯**: 修正 Phase 1.1 的驗證缺漏

## 🎯 開發目標
建立「獲取全市場標的清單」的能力，並基於此清單動態選擇代表性標的進行深度爬蟲與驗證，確保數據管道的涵蓋率與正確性。

### 核心產出
1.  **Master Fetcher (清單爬蟲)**:
    - `StockMasterFetcher`: 抓取全台股上市櫃代碼清單 (預期 > 1,700 檔)。
    - `CBMasterFetcher`: 抓取全市場可轉債代碼清單 (預期 > 200 檔)。
2.  **Target Selector (標的選擇器)**:
    - 簡單邏輯：從清單中隨機或指定挑選 N 檔 (包含熱門股 2330 與冷門股)。
3.  **Daily Crawler (日資料爬蟲 - 升級版)**:
    - 支援傳入 `asset_id` 列表進行批次抓取。
4.  **驗證報告**: 證明抓到的清單是完整的，且日資料非空。

### 驗收標準
- [ ] 成功產出 `data/raw/master/stock_list.csv` (筆數正確)。
- [ ] 成功產出 `data/raw/master/cb_list.csv` (筆數正確)。
- [ ] 自動化測試能從上述清單隨機挑選 3 檔，並成功抓取其日線資料。
- [ ] 確認 CB 資料包含「轉換價」或能透過關聯取得。

