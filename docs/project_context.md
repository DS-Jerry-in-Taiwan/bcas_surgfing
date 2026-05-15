# BCAS Quant 專案上下文摘要

> 最後更新: 2026-05-15
> 用途: 新 session 啟動時讀取此文件，快速掌握專案狀態

---

## 一、專案概述

BCAS Quant 是一個 CBAS 盤後自動化分析系統 (EOD Analytics System)。
每日台股收盤後自動啟動，蒐集現股與可轉債 (CB) 報價及籌碼數據，
計算溢價率與隔日沖風險，產出次日交易戰略清單。

- **版本**: 3.1.0
- **語言**: Python (7,160+ 行) + Go (scheduler)
- **資料庫**: PostgreSQL 14 (Docker)
- **部署**: Docker Compose (postgres + pipeline + scheduler)

---

## 二、系統架構

### 目錄結構

```
bcas_quant/
├── src/
│   ├── run_daily.py              日間主管道 (09:00 爬蟲->驗證->清洗)
│   ├── run_eod_analysis.py       EOD 主管道 (17:00~17:30 4 階段)
│   ├── framework/                核心框架層
│   │   ├── base_spider.py        BaseSpider (collect_only 模式)
│   │   ├── base_item.py          BaseItem + 7 個 Item + ITEM_REGISTRY
│   │   ├── pipelines.py          PostgresPipeline / CsvPipeline
│   │   ├── alerts.py             AlertManager + SlackAlertBackend
│   │   └── exceptions.py         異常階層
│   ├── spiders/                  爬蟲層
│   │   ├── stock_master_spider.py   上市股票主檔
│   │   ├── stock_daily_spider.py    股票日行情
│   │   ├── cb_master_spider.py      可轉債主檔
│   │   ├── tpex_cb_daily_spider.py  CB 日行情
│   │   └── broker_breakdown_spider.py 券商分點買賣超 (需修復)
│   ├── analytics/                EOD 分析引擎
│   │   ├── models.py             AnalysisResult 數據模型
│   │   ├── premium_calculator.py  轉換價值 + 溢價率計算
│   │   ├── technical_analyzer.py  技術面分析 (MA5/MA20/突破/型態)
│   │   ├── chip_profiler.py       籌碼分析 (黑名單比對，Stage 4 啟動)
│   │   ├── risk_assessor.py       S/A/B/C 評級 + 交易信號
│   │   └── rules/                 規則常數
│   ├── reporters/                報表輸出
│   │   ├── markdown_reporter.py    Markdown 報表
│   │   └── formatter.py            Rich 彩色輸出
│   ├── notifiers/                推播通知
│   │   ├── telegram_notifier.py    Telegram 推播
│   │   └── terminal_notifier.py    終端輸出
│   ├── pipeline/                 EOD 管道
│   │   └── eod_pipeline.py        4 階段主管道
│   ├── validators/               資料驗證 (8 個規則模組)
│   ├── etl/                      清洗層
│   ├── configs/                  設定
│   │   └── broker_blacklist.json   券商黑名單 (10 筆)
│   └── db/
│       ├── init_eod_tables.sql    (4 張分析用表)
│       └── seed_broker_blacklist.sql
├── scheduler/                    Go 排程器
├── tests/                        測試
│   ├── test_broker_breakdown_spider.py
│   ├── test_phase3_items.py
│   ├── test_phase3_integration.py
│   ├── test_premium_calculator.py
│   ├── test_technical_analyzer.py
│   ├── test_chip_profiler.py
│   ├── test_risk_assessor.py
│   ├── test_phase3_reporting.py
│   ├── test_eod_pipeline.py
│   └── test_bsr_captcha.py       (獨立 OCR 測試)
├── docs/
│   ├── agent_context/            開發階段文檔
│   │   ├── phase1_1 ~ phase1_4/   Phase 1 (爬蟲基礎)
│   │   ├── phase2_raw_data_validation/ Phase 2 (資料驗證)
│   │   ├── phase3_0 ~ phase3_3/   Phase 3 (EOD 分析系統)
│   │   ├── phase4/                BrokerBreakdown 替代方案調查
│   │   ├── phase5/                BSR + ddddocr 整合規劃 (已完成)
│   │   └── phase6/                E2E 整合驗證
│   └── project_context.md         本文件
└── scripts/
    └── start_eod.sh              EOD 啟動腳本
```

### EOD 4 階段流程

```
17:00 Stage 1: 爬蟲 (5 個 spiders -> collect_only -> validate -> flush)
17:15 Stage 2: 分析 (PremiumCalculator + TechnicalAnalyzer)
17:20 Stage 3: 風險 (ChipProfiler + RiskAssessor -> S/A/B/C 評級)
17:30 Stage 4: 報表 (MarkdownReporter -> Terminal/Telegram)
```

### 啟動方式

```bash
# 完整 EOD 流程
python src/run_eod_analysis.py

# 只看說明
python src/run_eod_analysis.py --help

# 只跑特定階段
python src/run_eod_analysis.py --stage 1   # 爬蟲
python src/run_eod_analysis.py --stage 2   # 分析
python src/run_eod_analysis.py --stage 3   # 風險
python src/run_eod_analysis.py --stage 4   # 報表
```

---

## 三、Phase 3 已完成功能

### Phase 3.0 - 基礎設施
- src/db/init_eod_tables.sql - 4 張分析用表
- src/spiders/broker_breakdown_spider.py - 分點爬蟲 (BSR+OCR, ✅已恢復)
- src/configs/broker_blacklist.json - 10 筆券商黑名單
- src/framework/base_item.py - 3 個新 Item 類
- src/run_daily.py - 整合 BrokerBreakdownSpider

### Phase 3.1 - 核心分析引擎 (測試通過 25+33 案例)
- src/analytics/premium_calculator.py - 溢價率計算
- src/analytics/technical_analyzer.py - 技術面分析

### Phase 3.2 - 風險評級系統 (測試通過 16+38 案例)
- src/analytics/chip_profiler.py - 黑名單比對 (Stage 4 啟動)
- src/analytics/risk_assessor.py - S/A/B/C 評級

### Phase 3.3 - 報表與自動化 (測試通過 10+11 案例)
- src/reporters/markdown_reporter.py
- src/reporters/formatter.py
- src/notifiers/telegram_notifier.py
- src/notifiers/terminal_notifier.py
- src/pipeline/eod_pipeline.py
- src/run_eod_analysis.py

### 測試覆蓋
- 總計: 208 個測試案例全部通過
- Phase 3.0: 75 案例
- Phase 3.1: 58 案例
- Phase 3.2: 54 案例
- Phase 3.3: 21 案例

---

## 四、Phase 5 & 6 完成狀態

### Phase 5 — BSR + ddddocr 整合 ✅ 已完成

BSR 網站客戶端 + ddddocr OCR 解決券商分點買賣超資料源問題。

| Stage | 說明 | 測試 | 狀態 |
|-------|------|:----:|:----:|
| Stage 1 | ddddocr OCR 測試 (100% 辨識率) | — | ✅ |
| Stage 2 | BsrClient (session/captcha/CSV) | 69 tests | ✅ |
| Stage 3 | BrokerBreakdownSpider 改寫 | 18 tests | ✅ |
| Stage 4 | RiskAssessor 恢復 (S/A/B/C 評級鏈) | 72 tests | ✅ |
| Stage 5 | E2E 整合驗證 | 16 tests | ✅ |
| 🔥 Hotfix | BSR CSV 格式變更 (437 券商解析成功) | (含於 Stage 2) | ✅ |
| 🔥 TWSE Retry | rate limit 指數退避重試 | 3 tests | ✅ |

**BSR CSV Hotfix**: BSR 網站改變回傳格式（HTML table → bsContent.aspx CSV），`BsrClient._parse_result()` 已支援雙格式：
先檢測 CSV 下載連結 → 下載 CSV → 解析彙總 437 家券商 → fallback 舊 table_blue

### Phase 6 — E2E 整合驗證 ✅ 已完成

首次使用真實資料執行完整 Pipeline 端到端驗證。

| 階段 | 結果 | 說明 |
|------|:----:|------|
| 5 個爬蟲真實資料測試 | ✅ | 全部 success=True |
| run_daily.py (validate-only) | ✅ | 295 單元測試通過 |
| run_daily.py (force-validation, flush) | ✅ | DB 寫入驗證通過 |
| run_eod_analysis.py (4 階段) | ✅ | 零崩潰，非阻斷設計正常 |
| EOD Pipeline import path 修復 | ✅ | run_eod_analysis.py sys.path 修正 |

### 已知 Issue

| ID | 問題 | 影響 | 嚴重度 | 狀態 |
|----|------|------|:------:|:----:|
| E2E-001 | CbMasterSpider CSV column mismatch (0 vs 22) → cb_master 0 筆 | PremiumCalculator 無法計算溢價率 | 🟡 中 | **Open** |
| E2E-002 | StockDailySpider 硬編碼只有 2330 | 僅 1 檔股票有日行情 | 🟢 低 | **Open** |
| E2E-004 | Clean 階段 `master_check` 欄位不存在於 DB | step_clean 失敗 | 🟡 中 | **Open** |

### 測試統計

| 測試群組 | 測試數 | 狀態 |
|---------|:------:|:----:|
| BsrClient | 69 | ✅ |
| BrokerBreakdownSpider | 18 | ✅ |
| RiskAssessor + ChipProfiler | 72 | ✅ |
| PremiumCalculator + TechnicalAnalyzer | 58 | ✅ |
| Phase 3 報表 + Pipeline | 21 | ✅ |
| Phase 3 Items + 整合 | 57 | ✅ |
| **核心邏輯 (phase5 + 回歸)** | **295** | **✅ 零回歸** |

---

## 六、資料庫

### Docker PostgreSQL
```bash
# DB 已啟動 (container: bcas-postgres)
docker exec bcas-postgres psql -U postgres -d cbas -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
```

### DB 連線設定
```python
from src.run_daily import DB_CONFIG
# DB_CONFIG = dict(host="localhost", port=5432, database="cbas", user="postgres", password="postgres")
```

### 8 張表 (實際存在)

既有 (4張): stock_master, stock_daily, stock_daily (hypertable 已移除), cb_master, tpex_cb_daily
Phase 3 (4張): broker_breakdown, daily_analysis_results, trading_signals, broker_blacklist

---

## 七、測試指令

```bash
# 全部測試
python -m pytest tests/ -v

# Phase 3 測試 (208 案例)
python -m pytest tests/test_broker_breakdown_spider.py tests/test_phase3_items.py tests/test_phase3_integration.py tests/test_premium_calculator.py tests/test_technical_analyzer.py tests/test_chip_profiler.py tests/test_risk_assessor.py tests/test_phase3_reporting.py tests/test_eod_pipeline.py -v

# BSR Captcha 獨立測試
python tests/test_bsr_captcha.py --count 10
```

---

## 八、相關文檔索引

| 文件 | 位置 | 說明 |
|------|------|------|
| 高階規劃書 | `docs/agent_context/phase3/analysis_mode_dev_doc.md` | EOD 系統原始需求 |
| Phase 5 開發日誌 | `docs/agent_context/phase5/development_log.md` | BSR+OCR 整合完整記錄 |
| BSR 解析器 Hotfix | `docs/agent_context/phase5/task_plan_bsr_fix.md` | BSR CSV 格式變更修正 |
| Phase 6 任務規劃 | `docs/agent_context/phase6/task_plan.md` | E2E 整合驗證 (本階段) |
| Phase 6 Developer Prompt | `docs/agent_context/phase6/developer_prompt.md` | E2E 驗證執行指引 |
| 優化路線圖 | `docs/OPTIMIZATION_ROADMAP.md` | 效能優化規劃 |
| 系統架構 | `SYSTEM_ARCHITECTURE.md` | 完整架構文件 |
