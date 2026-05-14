# Project Gamma Surf Phase 1.2 - Master Data 架構設計

## 1. MasterProvider 介面
- 方法：
  - `get_all_stocks() -> pd.DataFrame`：回傳全市場現股清單（symbol, name, market_type）
  - `get_all_cbs() -> pd.DataFrame`：回傳全市場可轉債清單（symbol, name, market_type, underlying_stock）

## 2. StockMasterAggregator
- 聚合 TWSE（上市）與 TPEx（上櫃）清單，統一欄位格式
- 支援排除已下市/暫停交易標的

## 3. TargetSelector
- 輸入 master list，支援：
  - 指定 symbol（如 2330, 52694）
  - 隨機抽樣 N 檔
- 輸出 sample_targets，供日資料爬蟲批次抓取

## 4. 資料結構
- 現股清單：symbol, name, market_type
- CB 清單：symbol, name, market_type, underlying_stock

## 5. 擴充性設計
- 可支援未來新資產類型（如 ETF、權證）
- 聚合邏輯與選擇器模組化，便於維護與測試