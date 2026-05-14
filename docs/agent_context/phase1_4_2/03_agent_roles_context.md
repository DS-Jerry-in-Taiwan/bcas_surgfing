# Phase 1.4.2 - Agent 角色職責

## 🏗️ @ARCH
- **職責**: 負責 Schema 穩定性。
- **重點**: 決定 `convert_price` 的精確度 (建議使用 `NUMERIC(10, 2)`)。

## 💻 @CODER
- **職責**: 負責 ETL 代碼開發。
- **重點**: 修改 Importer 的 Upsert 語句，確保 `ON CONFLICT` 時也會更新這些新欄位。

## 🧪 @ANALYST
- **職責**: 負責數據品質驗收。
- **重點**: 驗證 `NOT_FOUND` 的標記是否被正確處理，或是否應存入特定的欄位中。

