# TPEx CB Daily 資料表 Schema 建議

請參考 notebooks/cb_daily_profile.ipynb 輸出之 SQL Table 定義，並根據實際欄位型態與資料特徵調整。

## 建議 SQL Table 定義

```sql
CREATE TABLE tpex_cb_daily (
  -- 由 @ANALYST 執行 notebook 補齊實際欄位與型態
);
```

## 主鍵建議

- 建議以 (債券代碼, 交易日期) 作為主鍵，確保唯一性。

---

> 本文件為自動產生樣板，請由 @ANALYST 執行分析 notebook 補齊實際欄位與型態。