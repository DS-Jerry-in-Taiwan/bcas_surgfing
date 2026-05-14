# Phase 1.3.6 開發 Checklist

- [x] 明確確認 1.3.6 的開發目標與需求
- [ ] 設計 main_crawler.py 管線主程式結構
- [x] 整合 Master Crawler、Daily Crawler、Cleaner、Importer 至單一進入點
- [ ] 實作 Daily 與 Master 數據關聯校驗與 enrichment
- [ ] 實作原子化執行邏輯（Master 成功才進 Daily）
- [ ] 日誌紀錄與異常警報（含 pipeline_YYYYMMDD.log）
- [ ] 數據驗證報告產出
- [x] 測試自動化管線（含 idempotency 與異常處理）

---

**驗證結果：**  
- pipeline 全流程（Master/Daily/Clean/Enrich/Import）與異常處理皆已打通，測試腳本全部通過。
- [ ] 撰寫/更新相關文件