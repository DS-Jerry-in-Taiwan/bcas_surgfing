# Phase 1.3.4 - 開發流程

## 📅 執行步驟 (混合模式)

### Step 1: 邏輯設計 (@ARCH) -> ⏸️ Checkpoint 1
- **CLI 設計**: 若使用者同時提供 `--date` 和 `--start-date` 該如何處理？(優先使用區間)。
- **日期迭代**: 使用 `pandas.date_range` 或 `datetime.timedelta` 生成日期列表。
- **風控策略**: 定義 Sleep 區間 (min=3s, max=8s)。

### Step 2: 程式實作 (@CODER)
- **修改 `src/main_crawler.py`**:
    - 更新 `parse_args()` 加入 `start_date`, `end_date`。
    - 實作 `run_batch_dailies(start, end)`。
    - 在迴圈中呼叫 `tpex_daily.run(date)`。
    - 加入 `time.sleep(random.uniform(3, 8))`。
    - `try-except` 包裹單次爬取，捕捉異常。

### Step 3: 驗證測試 (@ANALYST) -> ⏸️ Checkpoint 2
- **測試 1**: 小範圍 (3天) 測試，確認 Sleep 生效。
- **測試 2**: 跨週末測試 (包含週六日)，確認程式未崩潰且正確跳過假日。

