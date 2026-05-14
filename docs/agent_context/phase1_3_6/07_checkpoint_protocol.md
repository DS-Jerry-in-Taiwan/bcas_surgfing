# Phase 1.3.6 - Checkpoint 協議

## ⏸️ Checkpoint 1: 管線架構確認 (After @ARCH)
**目的**: 確保整合後的流程符合「Master 先、Daily 後」的原則，且具備充足的數據校驗。
**檢查項目**:
1. 是否有處理 Master 缺失的邏輯？
2. 數據傳遞是否高效 (DataFrame vs CSV)？
**決策**: ✅ 通過 / 🔄 重修

## ⏸️ Checkpoint 2: 資料完整性確認 (After @ANALYST)
**目的**: 驗證最終入庫的數據是否完美對齊。
**檢查項目**:
1. 隨機選一個 Symbol，比對 [Raw CSV] <-> [Processed CSV] <-> [DB Table]。
2. 模擬網路失敗，確認 Pipeline 會自動中斷。
**決策**: ✅ 通過 / 🔄 重修

