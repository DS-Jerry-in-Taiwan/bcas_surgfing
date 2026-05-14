# Phase 1.2.1 - Checkpoint 協議

## ⏸️ Checkpoint 1: 容錯設計確認 (After @ARCH)
**觸發條件**: @ARCH 完成錯誤處理策略設計後。
**檢查項目**:
1. 是否確保了 `Aggregator` 在合併空 DataFrame 時不會報錯？
2. 是否定義了清楚的 Log Level (Error vs Warning)？
**決策選項**:
- ✅ **通過**: 進入 @CODER 修復。
- 🔄 **重修**: 設計仍未考慮到下游抽樣空的狀況。

## ⏸️ Checkpoint 2: 修復驗證 (After @ANALYST)
**觸發條件**: Pipeline 執行完畢後。
**檢查項目**:
1. **Crash Check**: 確保程式順利跑完 `Exit Code 0`，而非 traceback 報錯。
2. **Data Check**: 確認 `stock_list.csv` 內有上市股票資料。
**決策選項**:
- ✅ **通過**: TPEX 問題已隔離，可繼續 Phase 1.2 的後續工作或進入 Phase 1.3。
- 🔄 **重修**: 程式依然因為 DNS 錯誤而中止。

