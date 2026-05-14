# Phase 1.4 - Checkpoint 協議

## ⏸️ Checkpoint 1: Schema 設計確認 (After @ARCH)
**觸發條件**: 完成 `init.sql` 與 `docker-compose.yml` 設計後。
**檢查項目**:
1. **Hypertable**: 是否正確對 `market_daily` 啟用 TimescaleDB 功能？
2. **PK 設計**: `(ts, symbol)` 這樣的複合主鍵是否符合查詢需求？
**決策選項**:
- ✅ **通過**: Schema 設計完善，進入 ETL 開發。
- 🔄 **重修**: 表結構設計不合理。

## ⏸️ Checkpoint 2: 入庫數據驗收 (After @ANALYST)
**觸發條件**: 執行完 ETL 匯入後。
**檢查項目**:
1. **數據一致性**: 抽查 DB 資料與 CSV 原始檔是否一致。
2. **效能**: 匯入速度是否在合理範圍？
**決策選項**:
- ✅ **通過**: 資料庫建置完成，Phase 1 正式結案，準備進入 Phase 2 (Alpha Engine)。
- 🔄 **重修**: 資料遺失或格式錯誤。

