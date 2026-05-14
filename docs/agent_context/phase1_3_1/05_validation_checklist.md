# Phase 1.3.1 - 驗證清單

## 介面驗證
- [ ] `python src/main_crawler.py --help` 顯示正確說明。
- [ ] 支援 `--task` 與 `--date` 參數。

## 結構驗證
- [ ] `src/crawlers/` 下的模組已被重構，具備 `run()` 函式。
- [ ] 直接執行子模組 (如 `python src/crawlers/master/cb_master.py`) 仍然可以運作 (Backward Compatibility)。

## 執行驗證
- [ ] **Master Mode**: 能依序執行 Stock 與 CB Master 爬蟲。
- [ ] **Daily Mode**: 能執行日行情爬蟲。
- [ ] **Logging**: Log 檔案包含 TIMESTAMP, LEVEL, MESSAGE。

