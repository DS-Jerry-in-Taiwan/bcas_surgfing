# Phase 1.2.2 - Checkpoint 協議

## ⏸️ Checkpoint 1: API 參數確認 (After @ARCH)
**觸發條件**: @ARCH 完成 API 分析後。
**檢查項目**:
1. 確定的 URL 是什麼？
2. 需要哪些 Header？
3. 日期參數格式是 `YYYYMMDD` 還是 `YYY/MM/DD`？
**決策選項**:
- ✅ **通過**: 參數合理，進入 @CODER 實作。
- 🔄 **重修**: 參數不明確，需重新觀察 DevTools。

## ⏸️ Checkpoint 2: 數據品質確認 (After @ANALYST)
**觸發條件**: CSV 下載並分析後。
**檢查項目**:
1. **正確性**: 這份 CSV 真的是「買賣斷交易行情」嗎？還是「轉換統計」？
2. **可用性**: 欄位是否足夠計算 ATR 與 MA？(需要 OHLC)。
**決策選項**:
- ✅ **通過**: 確認資料源無誤，Phase 1.2.2 結案，併入主線。
- 🔄 **重修**: 下載錯檔案了（例如載到月報表），需調整 Payload `type` 參數。

