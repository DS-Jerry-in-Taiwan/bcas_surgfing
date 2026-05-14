# Phase 1.3.1 - Agent 執行 Prompts

## @ARCH Prompt
請設計 `src/main_crawler.py` 的架構：
1. **CLI 參數**: 
   - `task`: choices=['master', 'daily', 'all'], required=True
   - `date`: type=str, default=today (YYYY-MM-DD)
2. **Logging**: 設定 StreamHandler (Console) 與 FileHandler (`logs/crawler.log`)。
3. **流程控制**:
   - `try-except` 包裹主流程，發生未預期錯誤時記錄 Critical Log。
   - 子模組介面規範：`module.run()`。

## @CODER Prompt
請執行重構與實作：
1. **重構子模組**: 開啟 `src/crawlers/` 下的 `stock_master.py`, `cb_master.py`, `tpex_daily.py` (或其他名稱)。將主邏輯封裝進 `def run(target_date=None):`，並保留 `if __name__ == "__main__": run()` 以便單獨測試。
2. **實作入口**: 建立 `src/main_crawler.py`。
   - 使用 `argparse`。
   - 根據參數 import 對應模組並呼叫 `run()`。
   - 加入豐富的 Info/Error Log。

## @ANALYST Prompt
請驗證入口檔案：
1. 執行 `python src/main_crawler.py --help` 確認參數說明。
2. 執行 `python src/main_crawler.py --task master`，檢查 logs 與 CSV 產出。
3. 執行 `python src/main_crawler.py --task daily --date {最近交易日}`，確認執行無誤。
4. 檢查 `logs/crawler.log` 是否有寫入內容。

