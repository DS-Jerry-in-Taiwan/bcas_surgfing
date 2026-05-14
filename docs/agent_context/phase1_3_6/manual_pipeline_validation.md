# 手動驗證整體 Pipeline 流程

## 1. 執行指令

```bash
python src/main_crawler.py --task all --date YYYY-MM-DD
```

## 2. Checkpoint

- logs/crawler.log 有無錯誤訊息，流程是否依序執行到 Importer。
- data/raw/master/ 產生最新 master 檔案（如 stock_list.csv, cb_list_*.csv）。
- data/clean/daily/ 產生對應 daily 檔案。
- data/clean/daily/ 檔案經清洗、補充主檔欄位（如 master_債券簡稱、master_轉換價格）。
- DB 或入庫目標有正確寫入資料（可查 logs 或 DB 內容）。

## 3. 驗證方式

- 檢查 enriched daily csv 是否有補充主檔欄位且無 NOT_FOUND 異常。
- 檢查 logs/crawler.log 關鍵字：Start/Done: Stock Master、CB Master、TPEx CB Daily、Cleaner、Validate & Enrich、Importer。
- 如有 DB，可查詢最新資料筆數與內容。

---

如上述 checkpoint 均通過，即可確認 pipeline 已打通且資料流正確。