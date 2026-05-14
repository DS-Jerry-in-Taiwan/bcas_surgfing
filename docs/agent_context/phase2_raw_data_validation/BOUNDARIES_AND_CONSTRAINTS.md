# 邊界與禁止事項

本文件明確劃分 Phase 2 Raw Data Validation 的開發邊界。

---

## ✅ 範圍內（IN SCOPE）

### 檢查內容

| 項目 | 說明 |
|------|------|
| **結構檢查** | 欄位數量、欄位名稱、必要欄位是否齊全 |
| **型態檢查** | 各欄位是否可被正確解析（date 格式、price 為浮點、volume 為整數） |
| **值域檢查** | price > 0、volume >= 0、date 在合理範圍內 |
| **完整性檢查** | 爬取日期範圍內的 row count 是否符合預期 |
| **唯一性檢查** | symbol / cb_code 不重複 |
| **一致性檢查** | Daily 中的 symbol 是否都在 master 中存在 |
| **合理性警告** | 單日漲跌幅 > 10%（標記但不阻斷） |

### 資料類型

- ✅ stock_master（TWSE + TPEx）
- ✅ stock_daily（TWSE 日行情）
- ✅ cb_master（TPEx 可轉債主檔）
- ✅ tpex_cb_daily（TPEx CB 日行情）

### 交易日曆

- ✅ 內建簡單規則（排除週末、國定假日）
- ✅ 支援月份與日期範圍查詢
- ✅ 支援計算預期交易日數

### Pipeline 整合

- ✅ 新增 `--validate-only` CLI flag（驗證不寫入）
- ✅ 新增 `--force-validation` CLI flag（強制繼續）
- ✅ 新增 `--skip-validation` CLI flag（跳過驗證）
- ✅ Validation report 寫入 JSON 檔到 logs/validation/
- ✅ 彙整報告 (summary.json) 產出
- ✅ 驗證結果可判斷是否阻斷 pipeline

### 報表輸出

- ✅ 每個 table 各一份 report JSON
- ✅ 包含 passed / failed / warning rules 清單
- ✅ 每條 rule 的檢查結果與詳細信息
- ✅ Timestamp 與可追蹤性

### 單元測試

- ✅ 針對每條 rule 的 unit test（正常 + 異常）
- ✅ DataValidator 的 integration test
- ✅ TradingCalendar 的單測
- ✅ Pipeline 整合後的 E2E test

---

## ❌ 範圍外（OUT OF SCOPE）

### 不做內容驗證

**理由**：需要 ground truth source 對比（如與另一資料源比對），超出本階段職責。

❌ **禁止**:
- 檢查「某支股票的收盤價是否與 Yahoo Finance 一致」
- 檢查「價格是否合理（相對於歷史價格）」
- 檢查「成交量是否異常高 / 低」（除了極端值標記）

✅ **替代方案**：
- 留給 Phase 3 Anomaly Detection 階段
- 或交由 downstream 分析層處理

### 不做跨期趨勢分析

**理由**：需要存取歷史資料，不適合在驗證層做。

❌ **禁止**:
- 計算 price 相對於過去 N 天的 deviation
- 檢查是否有 gap day（缺少的交易日）相對於歷史
- 檢查每支 symbol 的交易頻率是否下降

✅ **替代方案**：
- Phase 3 或後續分析層處理

### 不修改原始資料

**理由**：Validator 是 read-only，不應在驗證過程中改動資料。

❌ **禁止**:
- 在驗證過程中 truncate / normalize 數據
- 自動修復格式錯誤（如補零）
- 刪除異常值

✅ **替代方案**：
- 若驗證失敗，可選擇 --force 繼續或阻斷
- 數據修復應在 spider/parser 層完成

### 不依賴外部 API

**理由**：外部 API 可能不穩定，驗證層應獨立。

❌ **禁止**:
- 呼叫 TWSE 行事曆 API 以取得交易日
- 呼叫 Yahoo Finance / Google Finance API 做 ground truth check
- 依賴外部服務進行數據驗證

✅ **替代方案**：
- 交易日曆用 built-in rule（排週末 + 內建假日清單）
- 若需精確行事曆，通過環境設定檔或手動維護

### 不操作 DB

**理由**：Validator 應與 persist 層解耦，便於單獨測試和重用。

❌ **禁止**:
- Validator 類直接 connect 到 PostgreSQL
- 在驗證過程中查詢 DB（如檢查 symbol 是否在 master 表中）
- 將驗證結果寫入 validation_log table

✅ **替代方案**：
- Validator 只吃傳入的 records list 與可選參數
- expected_symbols 等信息通過參數注入（從上一步 master 驗證結果傳入）
- 若未來需要記錄，可在 report_writer 層新增 DB 寫入邏輯

### 不覆蓋現有 Pipeline Error Handling

**理由**：Validator 是附加層，不應干擾既有的 try/except 邏輯。

❌ **禁止**:
- 在 validator 中 catch 並吞掉 spider 拋出的異常
- 修改 pipeline batch write 的 retry 邏輯
- 繞過現有的 spider 層 error handling

✅ **替代方案**：
- Validator 異常應自行 catch 並記錄，不往上拋
- Spider error 由 spider 自行處理
- Pipeline 異常由 pipeline 自行處理

---

## ⚠️ 重要注意事項

### 1. 交易日曆的維護

**現狀**：內建簡單規則（排週末 + 固定假日清單）

**問題**：
- 補班日、彈性放假、特殊假期需人工維護
- 2027 年以後的規則尚未定義

**建議**：
- 維護 `src/utils/trading_calendar.py` 中的假日清單
- 每年年初更新一次
- 可考慮從人資系統或勞動部行事曆同步（但不強制要求）

### 2. Raw Records 的定義切齊

**現狀**：Spider 的 parse 方法逐筆產生 Item，再逐筆餵進 pipeline

**問題**：
- 如何定義「raw records」？是 pre-parse 還是 post-parse？
- 目前 spider 未保留完整 raw records list（可能有遺漏）

**建議**：
- 明確定義：raw records = `item.to_dict()` 後的 list（尚未寫入 pipeline 前）
- 修改 spider 在 parse 完成後、pipeline flush 前保存一份 list
- 可選擇只保存一部分（如最後一批）以節省內存

### 3. CB Daily 的完整性檢查困難

**現狀**：TPEx CB daily 不是每個 CB 每日都有交易

**問題**：
- 無法用「預期 row count = trading_days × cb_codes」來檢查
- 某天可能根本沒有任何 CB 交易

**建議**：
- CB daily completeness 改為「至少有一筆交易」（warning only）
- 或「檢查是否每個 cb_code 都出現過至少一次」
- 具體日期的完整性暫不強制檢查

### 4. Stock Master 的完整性標準

**現狀**：stock_master 是「現狀快照」，不是時間序列

**問題**：
- 無法用「預期 row count」判斷是否完整
- TWSE 與 TPEx 的上市公司數每年波動

**建議**：
- Master completeness 改為「TWSE > 1500」與「TPEx > 800」（warning）
- 而非固定數字
- 可根據歷史趨勢調整閾值

### 5. Validator 效能與大數據集

**現狀**：Phase 1 演示只爬 3 支股票、幾個月的數據

**問題**：
- 若全市場爬蟲（2000+ symbols × 365 days = 730k+ rows），validator 會變慢
- 某些 rule（如 uniqueness check）需 O(n) 或 O(n log n) 時間

**建議**：
- 第一版不優化（simple is better）
- 若性能成問題，可考慮：
  - 批次驗證（分 batch 檢查）
  - 抽樣驗證（random sampling）
  - 並行驗證（per table 平行執行）
- 暫不在 Phase 2 實作

### 6. 測試資料的維護與演進

**現狀**：測試資料需人工編寫 mock JSON

**問題**：
- Item schema 改變時，test data 需同步更新
- 無自動檢查機制確保 test data 與 current schema 一致

**建議**：
- 在 CI pipeline 中加入「test data schema validation」步驟
- 若 item 欄位增減，該 CI 應失敗並提醒維護
- 可選擇定期從真實爬蟲結果中取樣更新 test data

### 7. Spider 層的 capture_raw 實作

**現狀**：建議在 spider 中加 `capture_raw` flag

**問題**：
- 不同 spider 的 parse 邏輯不同，實作方式可能也不同
- 需確保每隻 spider 都能正確回傳 raw records list

**建議**：
- 在 `BaseSpider` 中統一定義 `get_raw_records()` 接口
- 各 spider 通過 `self.save_item(item)` 統一保存
- 若某隻 spider 有特殊邏輯（如需 post-process），應在 spider 層解決

### 8. Validation Report 的保留期限

**現狀**：Report JSON 直接寫入 logs/validation/

**問題**：
- 長期運行會積累大量檔案
- 無自動清理機制
- 可能佔用大量磁碟空間

**建議**：
- 設定 retention policy（如保留最近 30 天）
- 可選擇壓縮舊報告或歸檔到遠端存儲
- 暫不在 Phase 2 實作，但設計時應考慮可擴展性

### 9. Validation 失敗的復原策略

**現狀**：若驗證 FAIL，可以 --force-validation 強制繼續

**問題**：
- 用戶可能不知道跳過驗證的後果
- 異常資料進入 DB 會污染下游分析

**建議**：
- 用 --force 時，應明確記錄在 report 中標記為「FORCED」
- 後續 cleaner 或分析層應察覺這個標記
- 可選擇自動產生告警或人工覆核流程（未來功能）

### 10. 與 Cleaner 的協調

**現狀**：Validator 完成後才執行 Cleaner

**問題**：
- Validator 標記的「consistency fail」（symbol 不在 master）與 Cleaner 的「NOT_FOUND」流程可能重複
- 若 Validator 已經知道某筆資料有問題，Cleaner 是否應該跳過？

**建議**：
- 明確定義：Validator 檢查「資料格式、完整性、一致性」，但不修改資料
- Cleaner 檢查「enrichment 與 cross-ref」，進行原地 UPDATE
- 若 Validator 發現 consistency fail，Cleaner 也會在 NOT_FOUND 時記錄
- 不需特殊協調，各自獨立進行

---

## 回顧清單

在開發過程中，定期檢查以下項目是否被遵守：

- [ ] 所有 rule 都是 read-only（不修改資料）
- [ ] Validator 不依賴 DB 連接
- [ ] Validator 不依賴外部 API
- [ ] Raw records 的定義清晰（post-parse, pre-pipeline）
- [ ] 每條 rule 都有通過 & 失敗的範例
- [ ] 單元測試覆蓋 >= 85%
- [ ] 交易日曆規則已維護到 2026 年底
- [ ] Report JSON 結構已定義並可被解析
- [ ] CLI flags (--validate-only, --force, --skip) 已實作
- [ ] Error handling 涵蓋 validator 異常與 spider 失敗
- [ ] 文件已更新（本文件及對應 integration guide）

---

**版本控制**
- v1.0 (2026-04-30): 初版邊界定義
