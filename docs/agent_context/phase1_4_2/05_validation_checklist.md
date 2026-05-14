# Phase 1.4.2 - 驗證清單

## DB Schema
- [ ] 欄位 `convert_price` 已存在。
- [ ] 欄位 `bond_short_name` 已存在。

## Ingestion 邏輯
- [ ] Importer 執行時無 KeyError。
- [ ] Upsert 時新欄位會被正確覆蓋更新。

## 數據完整性
- [ ] 隨機選取一筆 CB 數據，其 `convert_price` 需大於 0。

