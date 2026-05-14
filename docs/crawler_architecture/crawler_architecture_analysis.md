# 現有爬蟲架構現況分析

---

## 1. 系統現狀摘要
- 本爬蟲系統專注於特定網站的資料獲取，自訂請求流程與資料解析。
- 使用多個抽象模組分工，例如 base_scraper 為基礎模板，web_scraper 具體實作針對網頁片段抽取、API 輔助與異常處理。
- 主要流程為先由硬編碼起始 URL 集合出發，依序排程到各類型 handler 處理（頁面、API 或特殊路徑）。
- pipeline 以同步（同步或簡易 asyncio）策略推進，不支援進階分批插拔動態調度。
- 主要程序流程為串接：資料源取得 > HTML/Payload 解析 > 初步清洗過濾 > 存儲。

## 2. 架構元件與流程
- URL/任務來源 hardcode，無專屬 task queue/任務池。
- 各任務狀態與資料未有持久化狀態機制。重入、排程或錯誤恢復需仰賴 logging 或重啟程序。
- 無明確 pipeline 節點、異常分流與分段統計，目前錯誤多以 try-except 捕捉警告並人工介入。
- 防反爬措施低：如隨機 UA、等待時間、Cookie/Token 簡單插補。
- 落地流程純檔案寫入或簡易 DB，與主幹爬蟲流程高度綁定。
- 測試（如有）以單元為主，缺少流程重放與完整多任務驗證框架。

## 3. 技術堆疊
- Python 3.x
- requests、aiohttp 等 HTTP 客戶端
- lxml、BeautifulSoup、正則表達式解析文檔
- logging、exceptions 基礎錯誤監控
- 目標資料存儲類型為 local file/DB (sqlite/postgres)，無大規模分流或 Elastic Search

## 4. 主要限制與痛點
- 擴展性瓶頸：每新增一類型網站或新格式資料，皆需拉出新 handler/流程，造成主程式膨脹
- 狀態管理困難：異常恢復、重拉、重派需人工判讀，無記錄中心化
- pipeline 無法高度模組化、插拔與分段測試
- 未支援分散部署或多 agent 動態調控

## 5. 主要改善需求（對比 Agent 架構）
- 務必引入 task queue/middleware agent 解耦執行流程
- 帶入分段任務追蹤、批次插拔、重試率與異常統計
- 任務池和狀態流轉需可持久化且快速查詢（例如用 Redis、DB）

---

> 文件負責：opencode
> 製定時間：2026/04/14
> 本分析為 Agent 架構轉型前，針對現有系統所做之歸納。