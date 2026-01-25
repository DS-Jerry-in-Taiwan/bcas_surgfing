# Phase 1.1 - Checkpoint 協議

## ⏸️ Checkpoint 1: 架構設計確認 (After @ARCH)
**觸發條件**: @ARCH 完成 `BaseCrawler` 與目錄規劃後。
**檢查項目**:
1. 介面設計是否足夠彈性，能支援未來 XAU/USD？
2. 頻率限制 (Rate Limit) 機制是否已納入考量？
**決策選項**:
- ✅ **通過**: 進入 @CODER 開發。
- 🔄 **重修**: 架構過於複雜或無法擴充，退回 @ARCH。

## ⏸️ Checkpoint 2: 數據品質確認 (After @ANALYST)
**觸發條件**: @ANALYST 完成數據抓取與 Profiling 後。
**檢查項目**:
1. 原始數據是否包含所有策略所需欄位 (Parity 計算所需)？
2. 是否發現無法處理的異常格式？
3. Schema 建議是否合理？
**決策選項**:
- ✅ **通過**: Phase 1.1 結束，準備進入 DB 建置。
- 🔄 **重修**: 數據清洗邏輯有誤，退回 @CODER 修正爬蟲。

