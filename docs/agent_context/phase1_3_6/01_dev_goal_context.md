# Phase 1.3.6 - 數據集成與自動化管線優化 (開發目標)

**專案**: Project Gamma Surf
**目標**: 整合 Master (主檔) 與 Daily (行情) 的更新流程，實作「每日同步、清洗組合、批次入庫」的一鍵式自動化管線。

## 🎯 核心目標
1. **流程整合**: 將分散的 Master Crawler, Daily Crawler, Cleaner 與 Importer 整合進單一進入點 `src/main_crawler.py`。
2. **數據關聯 (Enrichment)**: 在入庫前，確保 Daily 行情數據能與最新的 Master 主檔資料進行校驗。
3. **穩定性優化**: 實作原子化執行邏輯，確保 Master 更新成功後才進行行情入庫，避免數據孤兒。

## 📦 預期產出
- `src/main_crawler.py`: 核心管線調度程式。
- `logs/pipeline_YYYYMMDD.log`: 詳細的管線執行日誌。
- 數據驗證報告: 證明每日同步後，DB 內的主檔與行情資料完全對齊。

## ✅ 驗收標準
- 執行 `python src/main_crawler.py --date today` 可自動跑完 [Master -> Daily -> Clean -> Ingest]。
- 當 Daily 資料出現 Master 清單中不存在的新標定時，系統能自動警報或嘗試補齊主檔。
- 重複執行管線時，資料庫數據不重複 (Idempotency)。

