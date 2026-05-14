# Phase 1.4.1 - Agent 執行 Prompts

## @ARCH Prompt
請檢查 Schema 相容性：
1. 檢查 `sql/init.sql` 中 `market_master` 的定義。
2. 確保 `issue_date` 和 `maturity_date` **沒有** `NOT NULL` 約束。
3. 如果有，請修改 `init.sql` 並重新啟動 Docker (`docker-compose down -v && docker-compose up -d`) 以套用變更。

## @CODER Prompt
請修復 `src/etl/importer.py` 中的 `load_cb_master` 函式：
1. 先印出 CSV 的 columns：`print(f"DEBUG: CSV Columns: {df.columns.tolist()}")`。
2. 修改讀取邏輯：
   ```python
   # 範例邏輯
   issue_date = row['issue_date'] if 'issue_date' in row else None
   maturity_date = row['maturity_date'] if 'maturity_date' in row else None

```

3. 確保傳給 DB Client 的資料字典中，缺失的日期欄位值為 `None`。

## @ANALYST Prompt

請驗證修復結果：

1. 執行 `python -m src.etl.importer`。
2. 觀察 Console 是否還有 Traceback。
3. 連線 DB 執行：`SELECT symbol, name, issue_date FROM market_master WHERE asset_type='CB' LIMIT 5;`
4. 確認 `issue_date` 為 NULL (空白)。

