# Phase 1.4.1 - Agent 角色職責

## 🏗️ @INFRA
- **職責**: 無。

## 📐 @ARCH
- **職責**: 調整資料庫約束 (Constraints)。
- **重點**: 
    - 決定放寬 Schema 限制：`market_master` 的日期欄位應改為 **Nullable**。
    - 這是因為 Phase 1.3 改變了策略（從官網爬清單 -> 改為從日行情反推），資料源變了，Schema 也要跟著適配。

## 💻 @CODER
- **職責**: 修改 Python 程式碼以防禦 KeyError。
- **重點**:
    - **Defensive Coding**: 不要假設 CSV 永遠有所有欄位。
    - 使用 `df.get('issue_date', None)` 或是 `record.get('issue_date')`。

## 🧪 @ANALYST
- **職責**: 驗證資料庫狀態。
- **重點**:
    - 確認入庫後的 `issue_date` 是 `NULL` 而不是錯誤的預設值 (如 1970-01-01)。

