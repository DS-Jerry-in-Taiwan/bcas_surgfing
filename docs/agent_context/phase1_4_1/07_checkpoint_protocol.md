# Phase 1.4.1 - Checkpoint 協議

## ⏸️ Checkpoint 1: 欄位確認 (After @ARCH/@CODER Diagnosis)
**觸發條件**: 確認 CSV 真實欄位後。
**檢查項目**:
1. CSV 真的缺欄位嗎？(預期是)。
2. DB Schema 是否需要修改？(若原本設為 NOT NULL 就需要)。
**決策選項**:
- ✅ **通過**: 確認問題點，進行修復。
- 🔄 **重修**: 發現 CSV 是空的或亂碼。

## ⏸️ Checkpoint 2: 入庫驗收 (After @ANALYST)
**觸發條件**: 執行修正後的 Importer 後。
**檢查項目**:
1. **Crash Free**: 程式順利跑完 `Exit Code 0`。
2. **Data Exist**: DB 內有資料。
**決策選項**:
- ✅ **通過**: 資料庫入庫功能修復，Phase 1.4 結案。
- 🔄 **重修**: 雖然 Master 過了，但 Daily 入庫失敗 (需一併檢查)。

