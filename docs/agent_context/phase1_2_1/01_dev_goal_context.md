# Phase 1.2.1 - 容錯機制與上櫃資料修復

**階段**: Phase 1.2.1 (Hotfix for TPEX Failure)
**專案**: Project Gamma Surf
**關聯**: 修復 Phase 1.2 Pipeline 因 TPEX DNS 解析失敗而崩潰的問題

## 🎯 開發目標
增強爬蟲與驗證管線的健壯性 (Robustness)，確保單一資料源（TPEX）故障不會癱瘓整個系統。同時，在無法連線 `isin.tpex.org.tw` 時，提供降級執行的能力。

### 核心產出
1.  **健壯的 Master Fetcher**:
    - 更新 `fetch_cb_master.py` 與 `fetch_stock_master.py`。
    - 加入 `try-except` 區塊處理 `requests.exceptions.ConnectionError` 與 `gaierror` (DNS 錯誤)。
2.  **Pipeline 邏輯更新**:
    - 當 TPEX 失敗時，Pipeline 應顯示「⚠️ TPEX 抓取失敗，僅執行 TWSE 驗證」，並繼續執行後續步驟。
3.  **配置檔 (Optional)**:
    - 簡單的 `config.py` 或環境變數，支援 `SKIP_TPEX=True`。

### 驗收標準
- [ ] 模擬 TPEX 斷線（或在當前網路環境下），執行 `run_validation_pipeline.py` **不會崩潰**。
- [ ] 程式能正確產出 `stock_list.csv` (至少包含 TWSE 資料)。
- [ ] Log 清楚記錄 TPEX 連線失敗的警告，但標示 Pipeline 狀態為 "Partial Success"。

