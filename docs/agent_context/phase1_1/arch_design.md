# Project Gamma Surf Phase 1.1 - 爬蟲架構設計

## 1. BaseCrawler 抽象類別
- 位置：src/crawlers/base.py
- 方法：
  - `fetch(url, params=None)`: 發送請求並取得原始資料
  - `parse(response)`: 解析回應內容
  - `save(data, filename)`: 儲存資料至檔案

## 2. RateLimiter Decorator
- 位置：src/crawlers/base.py
- 用法：@RateLimiter(calls_per_sec=1)
- 功能：控制 API 請求頻率，避免被封鎖

## 3. Raw Data 檔案命名規範
- 格式：`{date}_{asset_type}.json` 或 `{date}_{asset_type}.csv`
  - 例：2024-01-01_stock.json、2024-01-01_cb.csv
- 儲存路徑：
  - 現股：data/raw/stock/
  - 可轉債：data/raw/cb/

## 4. 擴充性設計
- 所有爬蟲皆繼承 BaseCrawler，未來可支援 XAU/USD 等新資產類型
- 介面統一，便於批次調度與測試
- RateLimiter 可調整頻率參數，支援不同來源 API