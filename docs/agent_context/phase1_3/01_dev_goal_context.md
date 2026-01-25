# Phase 1.3 - 標的探索與主檔建置

**階段**: Phase 1.3 (Master Data Construction)
**專案**: Project Gamma Surf
**背景**: 承接 Phase 1.2.x 的探索結論，棄用 ISIN 網站，正式採用 TPEx 官網直連方案。

## 🎯 開發目標
建立穩健的 Master List 爬蟲，生成包含全市場「上市現股」與「上櫃可轉債」的靜態清單。並透過抽樣驗證，確保這些清單中的代碼都能在日行情 API 中查到資料。

### 核心產出
1.  **Stock Master Fetcher**: 抓取 TWSE 所有上市普通股代碼與名稱。
2.  **CB Master Fetcher**: 解析 TPEx `listed.html`，抓取所有可轉債代碼、名稱、發行日、到期日。
3.  **Master Data Files**:
    - `data/raw/master/stock_list.csv`
    - `data/raw/master/cb_list.csv`
4.  **驗證報告**: 確認關鍵標的 (如 2330, 52694) 在清單中，且無重複或亂碼。

### 驗收標準
- [ ] `cb_list.csv` 包含 > 200 筆資料，欄位含 [Symbol, Name, IssueDate, MaturityDate]。
- [ ] `stock_list.csv` 包含 > 1,000 筆資料，欄位含 [Symbol, Name]。
- [ ] 針對 `cb_list.csv` 中的代碼，隨機抽取 3 檔能成功呼叫 Phase 1.1 的日線爬蟲。

