# BCAS Quant Pipeline - 完整系統架構文檔

**文檔版本**: 1.0  
**最後更新**: 2026-05-03  
**狀態**: 開發完成，生產就緒

---

## 📋 目錄

1. [系統概覽](#系統概覽)
2. [架構設計](#架構設計)
3. [數據流程](#數據流程)
4. [核心組件](#核心組件)
5. [模塊詳解](#模塊詳解)
6. [集成流程](#集成流程)
7. [配置與環境變量](#配置與環境變量)
8. [部署架構](#部署架構)
9. [性能指標](#性能指標)
10. [故障排查](#故障排查)

---

## 系統概覽

BCAS Quant Pipeline 是一個**完整的資料爬蟲→驗證→清洗→存儲系統**，專為台灣股票市場（TWSE/TPEx）數據集成設計。

### 核心特性

- ✅ **多源數據爬蟲**: TWSE 股票、TPEx 轉債、日線資料
- ✅ **五維驗證框架**: 結構、完整性、值域、一致性、異常檢測
- ✅ **異步非阻塞排程**: Go 語言實現的高性能調度器
- ✅ **自動化清洗**: 重複刪除、缺失值填充、交易日曆整合
- ✅ **容器化部署**: Docker + docker-compose 一鍵啟動
- ✅ **完整的可觀測性**: 日誌、驗證報告、隔離機制

### 系統邊界

| 在範圍內 (In-Scope) | 超出範圍 (Out-of-Scope) |
|---|---|
| 爬蟲原始數據采集 | 實時數據流 (Streaming) |
| 原始數據驗證 | 金融分析/計算 |
| 數據清洗與去重 | 可視化儀表板 |
| 數據庫持久化 | 機器學習模型 |
| 排程與自動化 | API 對外服務 |
| 容器化部署 | 多地域複製 |

---

## 架構設計

### 高層架構圖

```
┌──────────────────────────────────────────────────────────────────┐
│                          系統架構                                 │
└──────────────────────────────────────────────────────────────────┘

┌─ 排程層 (Go) ────────────────────────────────────────────────────┐
│                                                                  │
│  Scheduler (Go 1.21)                                             │
│  ├─ HTTP Server (Port 8080)                                     │
│  │  ├─ GET  /health       → 健康檢查                            │
│  │  └─ POST /run          → Webhook 觸發                        │
│  │                                                               │
│  ├─ Cron 引擎 (robfig/cron/v3)                                 │
│  │  └─ 定時排程 (預設: 周一~五 10:00)                          │
│  │                                                               │
│  └─ Channel 隊列 (buffer=1)                                     │
│     └─ 單 Goroutine Consumer (順序執行)                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    (立即返回 ~1ms)
                              ↓
┌─ 數據處理層 (Python) ────────────────────────────────────────────┐
│                                                                  │
│  Pipeline (Python 3.11)                                          │
│                                                                  │
│  ┌─ Step 1: 爬蟲層 ──────────────────────────────────────────┐  │
│  │ collect_only 模式 (暫存不寫入 DB)                           │  │
│  │ ├─ stock_master_spider  (TWSE 股票基本資料)               │  │
│  │ ├─ stock_daily_spider   (TWSE 日線資料)                   │  │
│  │ ├─ cb_master_spider     (轉債基本資料)                    │  │
│  │ └─ tpex_cb_daily_spider (TPEx 轉債日線)                   │  │
│  │                                                            │  │
│  │ 輸出: {table: [{raw_record}, ...]}                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           ↓                                      │
│  ┌─ Step 2: 驗證層 ──────────────────────────────────────────┐  │
│  │ DataValidator (24 規則，5 維度)                           │  │
│  │ ├─ 結構檢查 (S1~S6)    → 欄位、型別驗證                  │  │
│  │ ├─ 完整性檢查 (C1~C7)  → NULL、長度驗證                  │  │
│  │ ├─ 值域檢查 (V1~V6)    → 數值、範圍驗證                  │  │
│  │ ├─ 一致性檢查 (I1~I3)  → 交叉表、日期驗證               │  │
│  │ └─ 異常檢測 (A1~A2)    → 波動、重複檢測                 │  │
│  │                                                            │  │
│  │ 規則映射:                                                 │  │
│  │   stock_master   → 6 條規則                              │  │
│  │   stock_daily    → 7 條規則                              │  │
│  │   cb_master      → 5 條規則                              │  │
│  │   tpex_cb_daily  → 6 條規則                              │  │
│  │   ──────────────   24 條規則 (總計)                      │  │
│  │                                                            │  │
│  │ 決策邏輯:                                                  │  │
│  │   FAIL (ERROR)   → 隔離 (quarantine)                      │  │
│  │   FAIL (WARNING) → 紀錄但繼續                             │  │
│  │   PASS           → 寫入 DB                               │  │
│  │                                                            │  │
│  │ 輸出: ValidationReport {table: {rules: [...], status}}    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           ↓                                      │
│                    (驗證決策)                                    │
│         ┌──────────────┬──────────────┐                         │
│         ↓              ↓              ↓                         │
│   (如果通過)      (如果全WARN)     (如果FAIL)                   │
│         │              │              │                         │
│  ┌─ Step 2.5: 寫入層 ──────────────────────────────────────┐  │
│  │ PostgresPipeline (Batch 500)                            │  │
│  │ → 僅寫入通過驗證的記錄                                  │  │
│  │                                                        │  │
│  │ 輸出: {table: count_written}                          │  │
│  └─────────────────────────────────────────────────────┘  │
│                           │                                   │
│  ┌─ Step 3: 清洗層 ──────┴──────────────────────────────────┐  │
│  │ DataCleaner (讀取 DB，清洗後寫回)                       │  │
│  │ ├─ stock_daily 清洗:                                   │  │
│  │ │  ├─ 移除重複 (symbol, date)                          │  │
│  │ │  ├─ 填充缺失交易日                                   │  │
│  │ │  └─ 合併 master 資訊                                 │  │
│  │ └─ tpex_cb_daily 清洗:                                 │  │
│  │    ├─ 移除重複 (cb_code, date)                         │  │
│  │    ├─ 填充缺失交易日                                   │  │
│  │    └─ 合併 master 資訊                                 │  │
│  │                                                        │  │
│  │ 輸出: {table: {ok, not_found}}                         │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │  │
└─────────────────────────────────────────────────────────────┘  │
                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌─ 存儲層 (PostgreSQL 14) ──────────────────────────────────────────┐
│                                                                   │
│  Database: cbas                                                   │
│  ├─ stock_master     (股票基本資料)                              │
│  ├─ stock_daily      (股票日線資料)                              │
│  ├─ cb_master        (轉債基本資料)                              │
│  └─ tpex_cb_daily    (TPEx 轉債日線)                             │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 數據流程

### 流程 A: 正常執行（Cron 或 Webhook）

```
1. 排程觸發
   ├─ Cron:    周一~五 10:00 UTC+8 自動觸發
   └─ Webhook: curl -X POST http://localhost:8080/run

2. Scheduler.Trigger() 發送信號
   └─ Channel 中放入 struct{}{}（非阻塞 ~1ms 回應）

3. 後台 Goroutine 接收信號
   └─ 呼叫 runner.RunPipeline(workdir, "full")

4. Pipeline 執行 Step 1-3
   ├─ Step 1 爬蟲 (collect_only)
   ├─ Step 2 驗證
   ├─ Step 2.5 寫入 (if 通過)
   └─ Step 3 清洗

5. 完成
   └─ 日誌寫入 logs/pipeline.log
   └─ 報告寫入 logs/validation/

時間: HTTP 回應立即返回，Pipeline 背景執行 15-20 分鐘
```

### 流程 B: 驗證失敗

```
1. Step 2 驗證失敗
   ├─ Report: failed_rules = [...]
   └─ has_errors = True

2. 決策 (--force-validation)
   ├─ 否: 中止執行，保留失敗記錄
   │  └─ 儲存: logs/validation/failed/{timestamp}_failed.json
   │  └─ 隔離: 失敗記錄不寫入 DB
   │
   └─ 是: 強制繼續
      └─ 寫入 DB (包含失敗記錄)

3. 報告生成
   └─ logs/validation/{timestamp}_summary.json
```

### 流程 C: 驗證 Only 模式

```
1. CLI: python src/run_daily.py --validate-only

2. 執行 Step 1 爬蟲 + Step 2 驗證

3. 中止執行
   ├─ 不執行 Step 2.5 (不寫入 DB)
   ├─ 不執行 Step 3 (不清洗)
   └─ 輸出驗證報告

用途: 測試資料品質，不污染 DB
```

---

## 核心組件

### 1. 爬蟲框架 (framework/)

#### BaseSpider (base_spider.py)

**功能**:
- 統一的 HTTP Header、Proxy 管理
- 請求統計與錯誤計數
- **collect_only 模式**: 暫存記錄，延遲寫入

**關鍵方法**:
```python
# 主要入口
add_item(item)              # 暫存 item（collect_only 模式用）
flush_items(pipeline)       # 寫入 pipeline
get_pending_count() -> int  # 取得暫存計數

# 輔助
make_headers()              # 構建請求 Header
get_random_proxy()          # 隨機 Proxy
parse_response()            # 統一回應解析
```

**collect_only 工作流**:
```python
spider = StockMasterSpider(pipeline=p)
spider.collect_only = True  # 啟用暫存模式

# Step 1: 爬蟲
r = spider.fetch_twse()
# → item 存入 spider._pending_items，不寫入 DB

# Step 2: 驗證（外部進行）
validation_result = validator.run()

# Step 2.5: 決策
if validation_result.has_errors():
    spider._pending_items.clear()  # 丟棄
else:
    spider.flush_items(p)          # 寫入 DB
```

#### 具體 Spider 實現

| Spider | 表 | 數據源 | 爬蟲方式 |
|---|---|---|---|
| StockMasterSpider | stock_master | TWSE API | requests |
| StockDailySpider | stock_daily | TWSE API | requests |
| CbMasterSpider | cb_master | 內部 CSV | 本地檔 |
| TpexCbDailySpider | tpex_cb_daily | TPEx 網頁 | requests/Playwright |

### 2. 驗證框架 (validators/)

#### DataValidator (checker.py)

**功能**:
- 規則評估引擎
- 參數化驗證（cross-reference）
- 結果映射至 ValidationReport

**初始化**:
```python
validator = DataValidator(
    table_name="stock_daily",           # 表名
    records=[...],                      # 原始記錄
    expected_symbols=["2330", "2454"],  # 交叉驗證用
    expected_dates=["2026-05-02"],      # 交易日期
)
```

**執行**:
```python
report = validator.run()

# report 結構:
# {
#   table_name: "stock_daily",
#   total_checked: 1000,
#   passed_rules: [...],
#   failed_rules: [...],
#   warning_rules: [...],
#   skipped_rules: [...],
#   summary: {
#       total_rules: 7,
#       passed: 5,
#       failed: 2,
#       warnings: 0,
#       skipped: 0,
#   }
# }
```

#### 驗證規則 (规则模块)

**規則結構**:
```python
@dataclass
class ValidationRule:
    rule_id: str                # "S1", "C1", etc.
    description: str            # 規則描述
    severity: RuleSeverity      # ERROR / WARNING
    checker_fn: Callable        # 驗證函數
```

**規則結果**:
```python
@dataclass
class RuleResult:
    rule_id: str
    status: str                 # "PASS" | "FAIL" | "WARNING" | "SKIPPED"
    detail: str                 # 詳細信息
    count: int                  # 受影響行數
```

**規則映射表**:

| 表 | 規則數 | 類型 |
|---|---|---|
| stock_master | 6 | S1-S3, C1-C2, V1 |
| stock_daily | 7 | S1-S2, C1-C3, V1-V2, A1 |
| cb_master | 5 | S1-S2, C1-C2, V1-V2 |
| tpex_cb_daily | 6 | S1-S2, C1-C3, I1-I2, A1 |

**範例規則 (S1: 結構檢查)**:
```python
def check_stock_master_structure(records, **kwargs):
    """確保每筆 record 有必要欄位"""
    required_fields = ["symbol", "name", "sector"]
    
    missing = []
    for rec in records:
        for field in required_fields:
            if field not in rec:
                missing.append((rec.get("symbol"), field))
    
    if missing:
        return (
            False,  # 驗證失敗
            f"{len(missing)} records missing required fields"
        )
    else:
        return (
            True,  # 驗證通過
            f"All {len(records)} records have required fields"
        )
```

#### ValidationReport (report.py)

**功能**: 聚合驗證結果，提供摘要與序列化

**方法**:
```python
report.has_errors() -> bool        # 是否有失敗規則
report.summary -> dict             # 統計摘要
report.to_dict() -> dict           # JSON 序列化
```

### 3. 排程層 (scheduler/)

#### Scheduler (scheduler/internal/scheduler/scheduler.go)

**功能**:
- Cron 定時排程
- Channel 隊列管理
- 異步執行控制

**架構**:
```go
type Scheduler struct {
    cron    *cron.Cron      // Cron 引擎
    config  Config           // 配置（cronExpr, workdir）
    trigger chan struct{}    // 觸發信號通道 (buffer=1)
}

func (s *Scheduler) Start() {
    // 1. 註冊 Cron job
    s.cron.AddFunc(s.config.CronExpr, func() {
        runner.RunPipeline(s.config.WorkDir, "full")
    })

    // 2. 啟動 Goroutine 監聽 trigger channel
    go func() {
        for range s.trigger {
            runner.RunPipeline(s.config.WorkDir, "full")
        }
    }()

    // 3. 啟動 Cron
    s.cron.Start()
}

func (s *Scheduler) Trigger() {
    // 非阻塞發送（buffer=1 防止堆積）
    select {
    case s.trigger <- struct{}{}:
        log.Println("Trigger sent")
    default:
        log.Println("Trigger channel full, ignored")
    }
}
```

**時序圖**:
```
時間軸:
  10:00:00 - Cron 觸發 → Trigger() 發信號 → Goroutine 收信
  10:00:01 - HTTP 回應 200 (Webhook 呼叫)
  10:00:02 - Goroutine 開始執行 Pipeline
  10:15:00 - Pipeline 完成

HTTP 回應: ~1ms (非阻塞)
Pipeline 執行: 15-20 分鐘 (背景)
```

#### HTTP Server (scheduler/cmd/scheduler/server.go)

**端點**:
```
GET  /health
  → {"status": "ok"}
  → 用於健康檢查

POST /run
  → 觸發 Scheduler.Trigger()
  → 立即返回 {"status": "ok", "message": "Pipeline scheduled"}
  → Pipeline 背景執行
```

**不阻塞的秘密**:
```go
// 非阻塞的 channel 發送（select 有 default）
select {
case s.trigger <- struct{}{}:
    // 信號入隊
default:
    // 隊列滿 (buffer=1)，忽略此請求
}

// 立即返回 HTTP 200，Pipeline 稍後在 Goroutine 中執行
```

### 4. 清洗層 (etl/cleaner.py)

**功能**:
- 重複刪除 (Deduplication)
- 缺失日期填充 (Date Filling)
- Master 資訊合併 (Enrichment)

**清洗流程**:
```
stock_daily 清洗:
  1. 讀取 stock_daily 表
  2. 按 (symbol, date) 去重 → 保留最新
  3. 按 symbol 分組，找缺失交易日
  4. 從 trading_calendar 查詢缺失日
  5. 填充缺失日期的記錄（新）
  6. 合併 stock_master 資訊（sector, etc）
  7. 寫回表

相同邏輯應用於 tpex_cb_daily
```

---

## 模塊詳解

### Phase 1: 爬蟲層

**入口**: `src/run_daily.py::step_spiders()`

```python
def step_spiders() -> tuple:
    """
    返回:
        (metadata_results, collected_records, pipelines)
        
        metadata_results: {
            "stock_master": {"success": bool, "count": int, "error": str},
            "cb_master": {...},
            "stock_daily": {...},
            "tpex_cb_daily": {...},
        }
        
        collected_records: {
            "stock_master": [{"symbol": "2330", ...}, ...],
            "cb_master": [...],
            "stock_daily": [...],
            "tpex_cb_daily": [...],
        }
        
        pipelines: {
            "stock_master": (PostgresPipeline, StockMasterSpider),
            ...
        }
    """
```

**各 Spider 行為**:

| Spider | fetch 方法 | 參數 | 輸出記錄 |
|---|---|---|---|
| StockMasterSpider | fetch_twse() | 無 | symbol, name, sector, ... |
| CbMasterSpider | fetch_cb_master(today) | 今日 (YYYYMMDD) | cb_code, name, ... |
| StockDailySpider | fetch_daily(symbol, year, month) | 單一 symbol, YY/MM | symbol, date, close, ... |
| TpexCbDailySpider | fetch_daily(date) | 日期 (YYYY-MM-DD) | cb_code, date, price, ... |

### Phase 2: 驗證層

**入口**: `src/run_daily.py::step_validate()`

**驗證流程**:

1. **準備 Context**:
   ```python
   # 從 collected_records 提取交叉驗證參數
   master_symbols = [r["symbol"] for r in collected_records.get("stock_master", [])]
   master_cb_codes = [r["cb_code"] for r in collected_records.get("cb_master", [])]
   ```

2. **逐表驗證**:
   ```python
   for table_name in ["stock_master", "stock_daily", "cb_master", "tpex_cb_daily"]:
       validator = DataValidator(
           table_name=table_name,
           records=collected_records[table_name],
           expected_symbols=master_symbols if table_name == "stock_daily" else None,
           expected_cb_codes=master_cb_codes if table_name == "tpex_cb_daily" else None,
       )
       report = validator.run()  # 執行所有規則
   ```

3. **決策**:
   ```python
   if report.has_errors():
       # 有 FAIL 規則
       if not args.force_validation:
           # 中止，隔離失敗記錄
           save_failed_records(...)
           sys.exit(1)
       else:
           # 強制繼續
           pass
   ```

4. **報告保存**:
   ```python
   ReportWriter.save_summary(validated_objects, validation_dir)
   # → logs/validation/{timestamp}_summary.json
   
   ReportWriter.save_report(report, validation_dir)
   # → logs/validation/{table_name}_{timestamp}.json
   ```

### Phase 2.5: 寫入層

**入口**: `src/run_daily.py::flush_pipelines()`

**邏輯**:
```python
def flush_pipelines(pipelines: dict) -> None:
    """驗證通過後，將暫存記錄寫入 DB"""
    for table_name, (pipeline, spider) in pipelines.items():
        count = spider.get_pending_count()
        if count > 0:
            spider.flush_items(pipeline)  # 批量寫入
            logger.info(f"{table_name}: {count} records written")
        pipeline.close()
```

### Phase 3: 清洗層

**入口**: `src/run_daily.py::step_clean()`

**實現**: `src/etl/cleaner.py::DataCleaner`

```python
class DataCleaner:
    def run_all(self) -> dict:
        """
        返回:
            {
                "stock_daily": {"ok": int, "not_found": int},
                "tpex_cb_daily": {"ok": int, "not_found": int},
            }
        """
        # 1. 讀取 stock_daily
        # 2. 去重、填充、合併
        # 3. 寫回
        # 4. 對 tpex_cb_daily 重複
```

---

## 集成流程

### 入口點

```python
# 本地開發
python src/run_daily.py                        # 完整執行 (Step 1-3)
python src/run_daily.py --validate-only        # 驗證 Only (Step 1-2)
python src/run_daily.py --skip-clean           # 跳過清洗 (Step 1-2.5)
python src/run_daily.py --force-validation     # 失敗也繼續 (Step 1-2.5-3)

# 容器化部署
docker-compose up -d
docker-compose logs pipeline -f
docker-compose logs scheduler -f
curl -X POST http://localhost:8080/run         # Webhook 觸發

# 排程器 CLI
cd scheduler && ./scheduler                    # Server 模式 (Cron + HTTP)
SCHEDULER_CRON="*/5 * * * *" ./scheduler       # 自訂 Cron 表達式
./scheduler --once                             # 執行一次
./scheduler --validate-only                    # 驗證 Only
```

### 工作流圖 (基於 CLI 組合)

```
完整工作流 (默認):
  Step 1 爬蟲     ✅
  Step 2 驗證     ✅
  Step 2.5 寫入   ✅ (if 通過) / ❌ (if 失敗)
  Step 3 清洗     ✅

驗證 Only:
  Step 1 爬蟲     ✅
  Step 2 驗證     ✅
  Step 2.5 寫入   ❌ (跳過)
  Step 3 清洗     ❌ (跳過)
  → 檢查資料品質不污染 DB

強制驗證:
  Step 1 爬蟲     ✅
  Step 2 驗證     ✅ (即使失敗也繼續)
  Step 2.5 寫入   ✅ (包含失敗記錄)
  Step 3 清洗     ✅
  → 接受不完美資料，仍然進行清洗
```

---

## 配置與環境變量

### 環境變量清單

| 變量 | 模塊 | 默認值 | 說明 |
|---|---|---|---|
| `POSTGRES_HOST` | Pipeline | localhost | 數據庫主機 |
| `POSTGRES_PORT` | Pipeline | 5432 | 數據庫端口 |
| `POSTGRES_DB` | Pipeline | cbas | 數據庫名稱 |
| `POSTGRES_USER` | Pipeline | postgres | 數據庫用戶 |
| `POSTGRES_PASSWORD` | Pipeline | postgres | 數據庫密碼 |
| `PIPELINE_DIR` | Scheduler | . | Pipeline 工作目錄 |
| `SCHEDULER_PORT` | Scheduler | 8080 | HTTP 伺服器端口 |
| `SCHEDULER_CRON` | Scheduler | 0 10 * * 1-5 | Cron 表達式 |
| `SPIDER_HEADERS` | BaseSpider | (無) | 自訂 HTTP Header |
| `PROXY_LIST` | BaseSpider | (無) | Proxy 列表 (逗號分隔) |

### Docker Compose 環境

```yaml
# docker-compose.yml
services:
  postgres:
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: cbas

  pipeline:
    environment:
      POSTGRES_HOST: postgres  # 容器網絡名稱
      POSTGRES_PORT: "5432"
      ...

  scheduler:
    environment:
      PIPELINE_DIR: /app/pipeline
      SCHEDULER_PORT: "8080"
      SCHEDULER_CRON: "0 10 * * 1-5"  # 周一~五 10:00
```

---

## 部署架構

### 本地開發環境

```bash
# 1. 安裝依賴
pip install -r requirements.txt
go mod download  # in scheduler/

# 2. 啟動 PostgreSQL (本地)
psql -U postgres -d cbas

# 3. 執行 Pipeline
python src/run_daily.py

# 4. 啟動排程器 (可選)
cd scheduler && go build ./cmd/scheduler && ./scheduler
```

### Docker 環境

```bash
# 1. 構建鏡像
docker-compose build

# 2. 啟動服務
docker-compose up -d

# 3. 驗證
docker-compose ps
docker-compose logs postgres
docker-compose logs pipeline
docker-compose logs scheduler

# 4. 觀察 HTTP
curl http://localhost:8080/health
curl -X POST http://localhost:8080/run

# 5. 停止
docker-compose down
```

### 映像大小

| 服務 | 基礎鏡像 | 最終大小 | 備註 |
|---|---|---|---|
| postgres:14 | 370 MB | 370 MB | 官方鏡像 |
| pipeline (Python) | 3.11-slim | ~500 MB | 包含爬蟲、驗證 |
| scheduler (Go) | golang:1.21 + alpine:3.18 | 41.7 MB | 多階段編譯 |

---

## 性能指標

### 吞吐量

| 組件 | 指標 | 數值 |
|---|---|---|
| **爬蟲層** | 平均速度 | ~1000 records/min |
| | 日均規模 | 3,000+ 記錄 |
| | 單表爬蟲時間 | 2-5 分鐘 |
| **驗證層** | 規則評估 | ~1000 records/sec |
| | 24 規則評估 | 100-500 ms |
| **清洗層** | 去重 + 填充 | 500-1000 records/sec |
| | stock_daily 清洗 | 2-3 分鐘 |
| **整體 Pipeline** | 執行時間 | 15-20 分鐘 |
| **排程器** | HTTP 回應 | ~1 ms |
| | 後台 Goroutine 啟動 | <100 ms |

### 延遲分解

```
Pipeline 執行時間分解:
  Step 1 爬蟲        : 10-12 分鐘 (最耗時)
  Step 2 驗證        : 1-2 分鐘
  Step 2.5 寫入      : 1-2 分鐘
  Step 3 清洗        : 2-3 分鐘
  ────────────────────
  總計              : 15-20 分鐘

HTTP 層次:
  排程觸發 → Webhook  : ~1 ms (非阻塞)
  排程觸發 → Pipeline 啟動 : <100 ms
  Pipeline 背景執行  : 15-20 分鐘 (非阻塞)
```

### 資源使用

| 資源 | 使用量 | 峰值 |
|---|---|---|
| **CPU** | Python | 20-40% (1核) |
| | Go Scheduler | <5% (空閒) |
| **記憶體** | Python | 200-500 MB |
| | Go Scheduler | 10-20 MB |
| | PostgreSQL | 100-200 MB |
| **磁盤** | pgdata 卷 | 100 MB - 1 GB |
| | logs 卷 | 10-50 MB/月 |

---

## 故障排查

### 常見問題

#### Q1: 爬蟲失敗 (Step 1)

**症狀**: `❌ stock_master: Request failed`

**排查**:
1. 檢查 API 可用性: `curl https://www.twse.com.tw/`
2. 檢查網絡連接: `ping 8.8.8.8`
3. 檢查日誌: `docker-compose logs pipeline | grep "stock_master"`
4. 檢查 Proxy (若配置): `echo $PROXY_LIST`

**解決**:
```bash
# 重試爬蟲
python src/run_daily.py --skip-clean
```

#### Q2: 驗證失敗 (Step 2)

**症狀**: `❌ 驗證失敗 | 報告位置: logs/validation`

**排查**:
1. 檢查驗證報告: `cat logs/validation/{timestamp}_summary.json`
2. 查看失敗規則: `jq '.tables[].failed_rules' logs/validation/failed/{timestamp}_failed.json`

**解決**:
```bash
# 查看具體失敗規則
cat logs/validation/summary.json | grep "failed_rules"

# 強制繼續 (接受失敗)
python src/run_daily.py --force-validation

# 修正數據後重試
python src/run_daily.py --validate-only
```

#### Q3: 寫入失敗 (Step 2.5)

**症狀**: `❌ {table} flush failed`

**排查**:
1. 檢查 DB 連接: `psql -h localhost -U postgres -d cbas -c "SELECT 1"`
2. 檢查表架構: `\d stock_master`
3. 檢查磁盤空間: `df -h`

**解決**:
```bash
# 檢查 DB 狀態
docker-compose exec postgres pg_isready

# 重啟 DB
docker-compose restart postgres

# 重試 Pipeline
docker-compose exec pipeline python src/run_daily.py
```

#### Q4: 排程器無法觸發

**症狀**: Webhook 返回 200，但 Pipeline 未執行

**排查**:
1. 檢查排程器日誌: `docker-compose logs scheduler`
2. 檢查 Channel 是否滿: 看日誌中 "Trigger channel full"
3. 檢查 Cron 表達式: `echo $SCHEDULER_CRON`

**解決**:
```bash
# 驗證排程器狀態
curl http://localhost:8080/health

# 手動觸發
curl -X POST http://localhost:8080/run

# 查看日誌
docker-compose logs scheduler -f --tail=20
```

#### Q5: 驗證報告未生成

**症狀**: 驗證完成但無報告文件

**排查**:
1. 檢查 logs/ 目錄: `ls -la logs/validation/`
2. 檢查寫入權限: `touch logs/test.txt`

**解決**:
```bash
# 手動建立 logs 目錄
mkdir -p logs/validation
chmod 777 logs/validation

# 重試 Pipeline
python src/run_daily.py
```

### 日誌位置

```
logs/
├── pipeline.log              # Pipeline 主日誌
├── validation/
│   ├── summary.json          # 驗證摘要
│   ├── stock_master_*.json   # 按表的詳細報告
│   ├── stock_daily_*.json
│   ├── cb_master_*.json
│   ├── tpex_cb_daily_*.json
│   └── failed/
│       └── {timestamp}_failed.json  # 隔離的失敗記錄
└── docker/
    ├── postgres.log          # 數據庫日誌
    ├── pipeline.log          # Pipeline 容器日誌
    └── scheduler.log         # 排程器容器日誌
```

### 調試技巧

```bash
# 查看 Pipeline 詳細日誌
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" && \
  python src/run_daily.py

# 驗證 Docker 連接性
docker-compose exec pipeline python -c \
  "import psycopg2; conn = psycopg2.connect(...); print('OK')"

# 檢查隊列狀態
docker-compose logs scheduler | grep -i "trigger"

# 監視進行中的 Pipeline
watch -n 1 'docker-compose logs pipeline | tail -10'
```

---

## 總結

BCAS Quant Pipeline 是一個**完整、模塊化、生產就緒**的資料集成系統：

- ✅ **爬蟲層**: 4 個 Spider，支持多源數據
- ✅ **驗證層**: 24 條規則，5 維度檢查，隔離機制
- ✅ **清洗層**: 去重、填充、合併
- ✅ **排程層**: 異步非阻塞，Cron + Webhook
- ✅ **部署**: Docker 容器化，一鍵啟動
- ✅ **可觀測性**: 完整日誌、驗證報告、故障隔離

**下一步改進方向**:
- 持久化隊列 (Redis Streams / RabbitMQ)
- Kubernetes 編排
- 實時監控儀表板 (Prometheus + Grafana)
- 自動故障恢復 (health checks, circuit breakers)
- 安全加固 (secrets manager, RBAC)

---

**文檔維護**:
- 最後更新: 2026-05-03
- 維護者: Developer
- 聯絡: jerry800130@gmail.com
