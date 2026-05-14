# 爬蟲系統 Agent 架構改造高階規劃文件

---

## 1. 現況診斷與改造動機

- 現有爬蟲線性串接各類 URL，流程與邏輯緊耦合，擴展性有限
- 防反爬、資源調度、狀態推進等功能多以程序寫死，難以優雅插拔/重入/重試/分流
- 缺少可持久化的任務狀態管理，以及彈性策略調度能力
- 缺少自動閉環異常監控與動態決策行為能力
- 隨著資料源擴增，現有架構維護與新增 ETL 流程負擔急增

## 2. Agent 架構總覽與設計要點

- 核心以「多 Agent」組件解耦處理 craw、parse、filter、persist、retry、反制策略等任務
- 引入中央調度/監控 Agent 做為行為、資訊與資源協調中心
- 每一 Agent 都應:
  - 擁有自身獨立狀態與策略
  - 支援序列化任務中斷、恢復、分派、重試
  - 可被中央排程動態重組/替換/調度
- Agent 狀態、結果與異常皆需持久化（DB/快取/Lock/Queue...根據等級選型）
- 支援 pipeline 組裝、分段處理、失敗分流機制

### Agent 分工範例
| Agent 類型      | 主要責任                           |
|---------------|-----------------------------------|
| UrlSourceAgent | 生產候選目標 URL 並供分派消費      |
| CrawlAgent     | 負責網路請求/反爬突破/retry        |
| ParseAgent     | 針對 response 解析資訊抽取         |
| FilterAgent    | 根據規則數據預過濾/驗證            |
| PersistAgent   | 寫入資料處、落地處理               |
| MonitorAgent   | 全局監控 pipeline 狀態/統計/異常處理 |

### 狀態模型/中間格式設計
- 引入 Task, Job, Event log 等核心概念，統一格式（JSON/dict），便於歷程追蹤
- 單一 Agent 處理完成即回報狀態及內容，同步或 async 推進
- 任務唯一 id 跟蹤完整上下游歷程

## 3. 技術選型建議
- 核心語言：Python 3.x
- Framework: 參酌 langchain、Haystack、或純自訂 async（FastAPI/Sanic/TASKQ/Celery...）「但需根據現有人員能力、維護成本選擇」
- 狀態持久化：Redis、PostgreSQL、或文件/Key-Value Store。
- 任務排程：Celery、RQ、Dramatiq 或 asyncio.Task + Queue + Lock（視規模與複雜度遞進）
- 日誌監控：標準 logging + 狀態 DB + 統計
- 易於單元測試及後續可觀測性設計

## 4. 建議目錄結構
```
agent_framework/
├── agents/
│   ├── url_source_agent.py
│   ├── crawl_agent.py
│   ├── parse_agent.py
│   ├── filter_agent.py
│   ├── persist_agent.py
│   └── monitor_agent.py
├── core/
│   ├── state.py
│   ├── queue.py
│   └── scheduler.py
├── configs/
├── tasks/
├── tests/
├── README.md
└── docs/
    └── agent_framework_architecture.md
```

## 5. 實施階段建議
- 第一階段：以現有流程 mapping 出各 Agent 職責與介面草稿，先整出 skeleton 並確立狀態流
- 第二階段：逐步落實 pipeline，針對最小流程單元做串接
- 第三階段：串接持久化方案、Alarm/Monitor Agent
- 第四階段：大量擴充資料源/任務型態、壓測、加強健壯性

## 6. 關鍵待決事項（需與用戶討論）
- 是否統一從既有爬蟲流程（或子模組）做底層升級，或平行新架構、最終結合？
- 每一型 Agent 位置要可重複佈署嗎？如多爬蟲 task 分佈式設計
- 各階段排程/調度優先續的策略明確定義
- 任務 pipeline 錯誤處理與策略（失敗分流/重試時機點/最大失敗上限）
- 每筆資料型態的驗證、parse 範本設計
- 落地存儲與中間狀態持久化方案取捨

---

> 製定時間：2026/04/14
> 文件負責：opencode
> 若需討論細項，請於 agent_framework/issue 提供需求
