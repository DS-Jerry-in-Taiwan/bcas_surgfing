# Phase 1.3.2 - Checkpoint 協議

## ⏸️ Checkpoint 1: 錯誤原因確認 (After @ARCH/@CODER Debug Run)
**觸發條件**: 加入 Debug Log 並執行一次失敗後。
**檢查項目**:
1. **Status Code**: 是 403 (Forbidden)? 404 (Not Found)? 還是 200 (OK but content error)?
2. **Response Body**: 是 "System Error"? "Invalid Parameter"? 還是 Cloudflare 驗證頁?
**決策選項**:
- 🔧 **調整 Headers**: 若 403，通常是 Referer 或 User-Agent 問題。
- 🔧 **調整參數**: 若 200 但內容為空，通常是日期格式錯 (如週末或格式不符)。

## ⏸️ Checkpoint 2: 修復驗收 (After @ANALYST)
**觸發條件**: 修正代碼並成功執行後。
**檢查項目**:
1. **資料落地**: CSV 檔案真的產生了嗎？
2. **內容正確**: 打開 CSV，欄位是否對齊？
**決策選項**:
- ✅ **通過**: 問題解決，回到 Phase 1.4 (DB)。
- 🔄 **重修**: 依然抓不到資料。

