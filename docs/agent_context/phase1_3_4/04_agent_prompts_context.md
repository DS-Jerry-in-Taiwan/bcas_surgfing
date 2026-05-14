# Phase 1.3.4 - Agent 執行 Prompts

## @ARCH Prompt
請設計批量下載邏輯：
1. **CLI**: 新增 `--start-date` (YYYY-MM-DD) 與 `--end-date` (YYYY-MM-DD)。
2. **優先權**: 若有 `start-date` 則忽略 `--date`，進入 Batch Mode。
3. **安全機制**: 每次請求後 `time.sleep(random.uniform(3, 7))`。
4. **回饋機制**: 使用 `tqdm` 顯示進度條，或每筆 Log 清楚印出 `[Batch] Processing {date} ...`。

## @CODER Prompt
請修改 `src/main_crawler.py`：
1. 引入 `datetime`, `timedelta`, `random`, `time`。
2. 修改 `argparse` 設定。
3. 新增 `run_daily_batch(start_str, end_str)` 函式：
   - 轉換字串為 date 物件。
   - `while current <= end:` 迴圈。
   - `try`: 呼叫 `tpex_daily.run(current)`。
   - `except`: 捕捉錯誤，Log Error，不中斷迴圈。
   - `finally`: `time.sleep(...)`，並 `current += timedelta(days=1)`。
4. 在 `main` 區塊加入 Batch Mode 的判斷分支。

## @ANALYST Prompt
請驗證批量功能：
1. 執行 `python src/main_crawler.py --task daily --start-date 2024-01-01 --end-date 2024-01-05`。
2. 觀察 Log：
   - 是否有 "Processing 2024-01-01"？
   - 是否有間隔停頓？
   - 2024-01-01 (元旦) 是否被正確處理 (無資料/Skip)？
3. 檢查 `data/raw/daily/` 檔案數量。

