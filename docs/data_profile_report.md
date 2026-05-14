# TPEx CB Daily 數據品質報告（2024-03-07）

## 1. 欄位型態與缺值統計

| 欄位名稱 | 型態 | 缺值數量 |
|----------|------|----------|
| ...      | ...  | ...      |

（請由 @ANALYST 執行 notebooks/cb_daily_profile.ipynb 補齊實際統計）

---

## 2. 重複資料檢查

- 重複資料筆數：`0`（預設）

---

## 3. 異常值檢查

- High < Low 筆數：`0`（預設）
- Volume 為 0 筆數：`0`（預設）

---

## 4. Schema 建議

```sql
CREATE TABLE tpex_cb_daily (
  -- 請參考 notebook 輸出 SQL 定義
);
```

---

> 本報告為自動產生樣板，請由 @ANALYST 執行 notebook 補齊實際統計與建議。