# Phase 1.2.1 - Master Fetcher 容錯設計

## 1. fetch_list/fetch_cb_list/fetch_twse/fetch_tpex 規範
- 當遇到 requests.exceptions.RequestException、socket.gaierror、Timeout 等網路錯誤時：
  - 捕捉 Exception，log.warning("TPEX 來源連線失敗，僅執行 TWSE")
  - 回傳空 DataFrame（pd.DataFrame([])）

## 2. Aggregator 合併邏輯
- 聚合時使用 `pd.concat([twse_df, tpex_df], ignore_index=True)`，即使 tpex_df 為空也不會報錯。
- 若 tpex_df 為空，僅產出 TWSE master list，pipeline 可繼續執行。

## 3. Log Level
- TPEX 失敗時 log.warning，TWSE 失敗時 log.error。
- pipeline 最終狀態：若 TPEX 失敗，顯示 "Partial Success" 並繼續後續驗證。

## 4. 下游相容性
- TargetSelector、日爬蟲等下游模組需能處理 CB 清單為空的情境，不拋出 IndexError。