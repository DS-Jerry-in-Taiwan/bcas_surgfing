# Data Profile Report (2026-01)

## 1. TWSE 現股日成交資訊（2330）

- 檔案：data/raw/stock/2026-01_stock.json
- 欄位檢查：
  - 日期格式：民國年已轉換為西元年
  - 數值欄位（Open/High/Low/Close/Volume）均為數字型態
- 重複資料：無
- High 是否永遠 >= Low：通過檢查
- 缺值狀況：無 Null/0 值異常
- 主鍵建議：日期 + 股票代碼

## 2. TPEx 可轉債日成交資訊

- 檔案：data/raw/cb/2026-01-25_cb.csv
- 欄位檢查：
  - 日期格式：YYYY-MM-DD
  - Volume 欄位為 0 時，Price 欄位檢查無異常
- 重複資料：無
- High 是否永遠 >= Low：通過檢查
- 缺值狀況：無 Null/0 值異常
- 主鍵建議：日期 + CB 代碼

## 3. 結論與建議

- 兩份數據格式與品質均符合預期
- 建議 Schema：
  - 現股：date, stock_id, open, high, low, close, volume
  - CB：date, cb_id, open, high, low, close, volume, price