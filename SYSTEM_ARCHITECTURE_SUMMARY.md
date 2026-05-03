# BCAS Quant Pipeline - 系統架構梳理 (摘要版)

## 📋 完整架構文檔已生成

**完整文檔位置**: `docs/agent_context/phase2_raw_data_validation/SYSTEM_ARCHITECTURE.md`  
**文檔大小**: 970 行  
**覆蓋內容**: 10 大主題，包含架構圖、流程圖、配置表、故障排查指南

---

## 🎯 架構核心要點

### 1. 排程層 (Go)
```
Cron 排程 (robfig/cron/v3)          HTTP Webhook
  ├─ 表達式: "0 10 * * 1-5"           ├─ GET /health (健康檢查)
  └─ 周一~五 10:00 自動觸發           └─ POST /run (即時觸發)
       │                                   │
       └─────────────────┬─────────────────┘
                         ↓
              Scheduler.Trigger()
              (Channel buffer=1)
                         ↓
           Goroutine Consumer (單一)
           for range s.trigger {}
                         ↓
          runner.RunPipeline(...)
                    (背景執行)

HTTP 回應: ~1ms (非阻塞)
Pipeline: 15-20 分鐘 (背景)
```

### 2. 數據處理層 (Python)

#### Step 1: 爬蟲 (collect_only 模式)
```
4 Spiders 並行爬蟲:
├─ StockMasterSpider   → stock_master (6 條規則)
├─ StockDailySpider    → stock_daily (7 條規則)
├─ CbMasterSpider      → cb_master (5 條規則)
└─ TpexCbDailySpider   → tpex_cb_daily (6 條規則)

爬蟲結果暫存在內存 (_pending_items)
不寫入 DB，等待驗證決策

輸出: {table: [{raw_record}, ...]}
```

#### Step 2: 驗證 (24 規則，5 維度)
```
DataValidator 框架:
├─ 結構檢查 (S1-S3): 欄位、型別驗證
├─ 完整性檢查 (C1-C3): NULL、長度驗證
├─ 值域檢查 (V1-V2): 數值、範圍驗證
├─ 一致性檢查 (I1-I2): 交叉表、日期驗證
└─ 異常檢測 (A1-A2): 波動、重複檢測

驗證決策:
├─ PASS       → 寫入 DB (Step 2.5)
├─ FAIL (ERROR) → 隔離 (logs/failed/)
└─ FAIL (WARNING) → 紀錄但繼續

輸出: ValidationReport (passed/failed/warning/skipped)
```

#### Step 2.5: 寫入
```
PostgresPipeline (批量 batch=500):
├─ 僅寫入通過驗證的記錄
├─ 驗證失敗的記錄隔離不寫入
└─ 交易日期、匯率等完整性檢查

輸出: {table: count_written}
```

#### Step 3: 清洗
```
DataCleaner (讀 DB → 清洗 → 寫回):

stock_daily 清洗:
├─ 去重 (symbol, date)
├─ 找缺失交易日
├─ 從 TradingCalendar 填充
└─ 合併 stock_master 資訊

tpex_cb_daily 清洗:
├─ 去重 (cb_code, date)
├─ 找缺失交易日
├─ 從 TradingCalendar 填充
└─ 合併 cb_master 資訊

輸出: {table: {ok: count, not_found: count}}
```

### 3. 存儲層 (PostgreSQL 14)
```
Database: cbas
├─ stock_master (股票基本資料) - 已驗證、已清洗
├─ stock_daily (股票日線) - 已驗證、已清洗、已去重、已填充
├─ cb_master (轉債基本資料) - 已驗證、已清洗
└─ tpex_cb_daily (TPEx 轉債日線) - 已驗證、已清洗、已去重、已填充
```

---

## 🔄 工作流決策矩陣

| CLI 命令 | Step 1 | Step 2 | Step 2.5 | Step 3 | 用途 |
|---|:---:|:---:|:---:|:---:|---|
| `python src/run_daily.py` | ✅ | ✅ | ✅ | ✅ | 完整執行 |
| `--validate-only` | ✅ | ✅ | ❌ | ❌ | 測試品質，不污染 DB |
| `--skip-clean` | ✅ | ✅ | ✅ | ❌ | 跳過清洗 |
| `--force-validation` | ✅ | ✅ | ✅* | ✅ | 失敗也繼續 (* 包含失敗記錄) |

---

## 📊 性能指標

### 吞吐量
```
爬蟲層:    ~1000 records/min
驗證層:    ~1000 records/sec (24 規則)
清洗層:    ~500-1000 records/sec
整體:      15-20 分鐘 / 日運行
日均量:    3,000+ 記錄
```

### 延遲分解
```
HTTP 觸發:      ~1 ms (非阻塞)
Pipeline 啟動:  <100 ms
Step 1 爬蟲:    10-12 分鐘 ⚠️ (最耗時)
Step 2 驗證:    1-2 分鐘
Step 2.5 寫入:  1-2 分鐘
Step 3 清洗:    2-3 分鐘
──────────────────────────
總計:           15-20 分鐘
```

### 資源使用
```
CPU:     20-40% (1 核)
內存:    200-500 MB (Pipeline)
磁盤:    100 MB - 1 GB (pgdata)
Docker:  41.7 MB (Go Scheduler)
```

---

## 🔧 配置要點

### 環境變量
```
# Pipeline 連接
POSTGRES_HOST=postgres              # DB 主機
POSTGRES_PORT=5432                  # DB 端口
POSTGRES_DB=cbas                    # DB 名稱

# Scheduler
SCHEDULER_PORT=8080                 # HTTP 端口
SCHEDULER_CRON="0 10 * * 1-5"       # Cron 表達式
PIPELINE_DIR=/app/pipeline          # Pipeline 目錄

# 爬蟲 (可選)
SPIDER_HEADERS=...                  # 自訂 Header
PROXY_LIST=...                      # Proxy 列表
```

### Docker Compose
```yaml
services:
  postgres:           # DB 容器
  pipeline:           # 爬蟲+驗證+清洗
  scheduler:          # Go 排程器

volumes:
  pgdata:             # 數據持久化
  logs:               # 日誌、驗證報告
```

---

## 📝 核心設計決策

### 1. collect_only 模式
```
為什麼:
  ├─ 爬蟲只採集，不寫入
  ├─ 驗證層決策是否寫入
  └─ 失敗的記錄隔離，不污染 DB

實現:
  ├─ spider.collect_only = True
  ├─ item 暫存於 spider._pending_items
  └─ validation pass 後才 flush
```

### 2. 異步非阻塞排程
```
為什麼:
  ├─ HTTP 快速回應 (SLA < 5ms)
  ├─ Pipeline 後台執行 (可能 15+ 分鐘)
  └─ 不阻塞 webhook 發起方

實現:
  ├─ Channel 發信號 (非阻塞 send)
  ├─ Goroutine consumer (單一)
  ├─ buffer=1 防止堆積
  └─ HTTP 立即返回，Pipeline 背景跑
```

### 3. 24 規則 5 維度驗證
```
為什麼:
  ├─ 結構檢查: 防止解析失敗
  ├─ 完整性檢查: 防止缺失值
  ├─ 值域檢查: 防止異常值
  ├─ 一致性檢查: 防止邏輯錯誤
  └─ 異常檢測: 防止重複/波動

好處:
  ├─ 不只檢查格式，還檢查合理性
  ├─ 多層防護，降低髒數據進 DB
  ├─ 隔離機制，不污染現有數據
  └─ 驗證報告，便於事後審查
```

### 4. TradingCalendar 交易日曆
```
功能:
  ├─ 識別交易日/非交易日
  ├─ 計算缺失的交易日
  ├─ 填充缺失日期的記錄
  └─ 內置 2026 年台灣假日

適用:
  ├─ stock_daily 清洗
  └─ tpex_cb_daily 清洗
```

---

## 🚀 部署流程

### 本地開發
```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 啟動 DB (本地 PostgreSQL 或 Docker)
docker run -d -p 5432:5432 postgres:14

# 3. 執行 Pipeline
python src/run_daily.py

# 4. 啟動排程器 (可選)
cd scheduler && go build ./cmd/scheduler && ./scheduler
```

### Docker 部署
```bash
# 1. 構建
docker-compose build

# 2. 啟動
docker-compose up -d

# 3. 驗證
curl http://localhost:8080/health
curl -X POST http://localhost:8080/run

# 4. 觀看日誌
docker-compose logs -f pipeline
docker-compose logs -f scheduler
```

---

## 📋 故障排查快速指南

| 問題 | 檢查 | 解決 |
|---|---|---|
| 爬蟲失敗 | `docker logs pipeline \| grep error` | 重試或檢查 API 可用性 |
| 驗證失敗 | `cat logs/validation/failed/*.json` | 查看失敗規則，修正數據 |
| DB 寫入失敗 | `docker exec postgres psql` | 檢查連接、空間 |
| 排程無法觸發 | `docker logs scheduler` | 檢查 cron expr、channel 狀態 |
| 性能慢 | `docker stats` | 檢查 CPU/內存使用 |

---

## 📚 文檔導航

| 文檔 | 用途 |
|---|---|
| **SYSTEM_ARCHITECTURE.md** (970 行) | 完整系統架構、組件詳解、故障排查 |
| **SCHEDULER_IMPLEMENTATION.md** | 排程器 4 階段實現進度 |
| **DEVELOPMENT_PLAN.md** | 驗證層設計思路 |
| **BUILDER_PROMPT.md** | 開發者實作指南 |
| **DELIVERY_SUMMARY.md** | 整體進度摘要 |

---

## ✅ 當前狀態

- ✅ 所有核心功能完成
- ✅ 127 個單元測試通過 (92% 覆蓋率)
- ✅ Docker 容器化就緒
- ✅ 完整架構文檔
- ⚠️ 監控告警 (基礎級別)
- ⚠️ 持久化隊列 (未實現)
- ⚠️ Kubernetes 編排 (未實現)

**生產就緒度**: 6.25 / 10 (開發完成，可用於非關鍵環境)

---

**文檔版本**: 1.0  
**最後更新**: 2026-05-03  
**維護者**: Developer
