# Phase 1.4.2 - 增強型資料入庫與 Schema 對齊 (目標)

**專案**: Project Gamma Surf
**背景**: Phase 1.3.6 已成功產出增強後的 DataFrame，現在需確保資料庫能接收這些新欄位。

## 🎯 開發目標
1. **Schema 進化**: 更新資料庫表結構，以儲存由 `validate_and_enrich.py` 產出的增強資訊。
2. **Importer 升級**: 修改 `src/etl/importer.py`，將新欄位正確對應並執行 Upsert。
3. **全鏈路驗證**: 執行一鍵式全管線任務，確保數據從爬取到入庫的完整性。

## ✅ 驗收標準
- [ ] `market_daily` 資料表中出現 `convert_price` 與 `bond_short_name` 欄位。
- [ ] 執行 `python3 src/main_crawler.py --task all` 無報錯且資料入庫成功。
- [ ] 資料庫查詢結果顯示 `convert_price` 欄位具備精確數值而非空值。

