# Phase 1.3.5 - Checkpoint 協議

## ⏸️ Checkpoint 1: 清洗邏輯確認 (After @ARCH)
**觸發條件**: 確認 Raw CSV 結構後。
**檢查項目**:
1. 關鍵字 "代碼" 是否通用於所有 TPEx CSV？(有沒有可能某天變成 "證券代號"？建議多設幾個 Alias)。
2. 編碼策略：Raw 是 Big5/CP950，Processed 轉為 UTF-8 是否確定？
**決策選項**:
- ✅ **通過**: 邏輯可行。
- 🔄 **重修**: 關鍵字定義不清。

## ⏸️ Checkpoint 2: 防呆驗收 (After @ANALYST)
**觸發條件**: 執行破壞性測試後。
**檢查項目**:
1. **Log 檢查**: 是否清楚看到 `[ERROR] Failed to import...`？
2. **Process 檢查**: 程式是否 Exit Code 0 結束 (非 Crash)？
**決策選項**:
- ✅ **通過**: 防呆機制生效，Pipeline 穩健，Phase 1.4 可繼續。
- 🔄 **重修**: 程式遇到錯誤直接崩潰。

