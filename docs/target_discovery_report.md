# Phase 1.2.1 驗證報告

## 測試情境
- 模擬 TPEX DNS 失敗，僅能取得 TWSE（上市）清單。

## Pipeline 執行結果
- TWSE master list 正常產出，日資料驗證通過。
- TPEX 來源失敗，log 顯示：
  - `WARNING:root:TPEX source unreachable...`
  - `WARNING:root:TPEX CB source unreachable...`
  - `WARNING:root:⚠️ TPEX source unreachable or CB list empty, proceeding with TWSE only. [Partial Success]`
- Pipeline 最終顯示：`Validation pipeline completed with warnings (Partial Success).`

## 結論
- 容錯 hotfix 成功，TPEX 失敗時系統可降級執行 TWSE 驗證，流程不中斷。
- Log 記錄明確，方便後續監控與維運。