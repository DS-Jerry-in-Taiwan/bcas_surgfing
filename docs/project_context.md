# BCAS Quant 專案上下文摘要

> 最後更新: 2026-05-13
> 用途: 新 session 啟動時讀取此文件，快速掌握專案狀態

---

## 一、專案概述

BCAS Quant 是一個 CBAS 盤後自動化分析系統 (EOD Analytics System)。
每日台股收盤後自動啟動，蒐集現股與可轉債 (CB) 報價及籌碼數據，
計算溢價率與隔日沖風險，產出次日交易戰略清單。

- **版本**: 3.0.0
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
│   │   └── phase5/                BSR + ddddocr 整合規劃
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
- src/spiders/broker_breakdown_spider.py - 分點爬蟲 (需修復 API)
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

## 四、目前進行中的議題

### 核心問題: BrokerBreakdownSpider 資料源失效

TWSE MI_20S API (券商分點買賣超) 已下架，回傳 302 -> 404。

已調查的替代方案:
- TWSE OpenAPI (95 個端點): 無 MI_20S
- twstock SDK: 無分點資料
- FinMind: 有但要付費 Sponsor
- Shioaji (永豐): 需永豐帳戶
- Goodinfo 爬蟲: 已改 SPA
- BSR 網站: 有資料但需要驗證碼

### 最新結論: BSR + ddddocr

BSR 網站 (https://bsr.twse.com.tw/bshtm/) 有完整的分點買賣超資料。

使用 ddddocr (輕量級開源 OCR) 測試結果:
- Captcha 辨識率: 100% (26/26)
- 平均辨識時間: 17ms
- 端到端測試: 成功抓取 2330 台積電今日完整買賣日報 (60 頁)

### 設計規範 (務必遵守)

必須遵循:
- Spider __init__ 接受 pipeline=None 參數
- 使用 self.items + self.add_item(item) 同步呼叫
- 使用 collect_only = True
- 在 run_daily.py 的 step_spiders() 中註冊新爬蟲
- Item 類別註冊至 ITEM_REGISTRY

禁止事項:
- 禁止使用 self._items (必須用 self.items)
- 禁止繞過 self.add_item(item)
- 禁止建立 security_profile 表或 SecurityProfileItem
- 禁止建立 ConversionPriceSpider (CbMasterSpider 已涵蓋)

---

## 五、Phase 5 待執行項目

### 文件位置
docs/agent_context/phase5/ (5 份規劃文件, 2055 行)

### 執行計畫

```
Day 1: OCR 測試 (3h) -> ✅ 已完成 (100% 辨識率)
Day 2: BsrClient 封裝 (6h) -> ✅ 已完成
Day 3: BrokerBreakdownSpider 改寫 (4h) -> ✅ 已完成
Day 4: RiskAssessor 恢復 (3h) -> ✅ 已完成 (Stage 4)
Day 5: E2E 驗證 (2h) -> ⬅️ 當前 (Stage 5)
```

### 待實作模組

| 模組 | 說明 | 狀態 |
|------|------|------|
| src/spiders/bsr_client.py | BSR 網站客戶端 | ✅ 完成 |
| src/spiders/ocr_solver.py | ddddocr 封裝 | ✅ 完成 |
| src/spiders/broker_breakdown_spider.py (改寫) | 改用 BsrClient | ✅ 完成 |
| src/analytics/chip_profiler.py | 黑名單比對 | ✅ 恢復 |
| src/analytics/risk_assessor.py | S/A/B/C 評級 | ✅ 恢復 |

**Phase 5 完成度**: Stage 1-4 ✅ 完成 | **Stage 5 進行中** (E2E 整合驗證)

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

### 9 張表

既有 (5張): stock_master, stock_daily, cb_master, cb_daily (hypertable), tpex_cb_daily
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
| 高階規劃書 | docs/agent_context/phase3/analysis_mode_dev_doc.md | EOD 系統原始需求 |
| Phase 3 開發文檔 | docs/agent_context/phase3_0 ~ phase3_3/ | 各階段開發目標、流程、角色 |
| Phase 4 調查報告 | docs/agent_context/phase4/ | 替代資料源分析 (5 方案) |
| Phase 5 規劃 | docs/agent_context/phase5/ | BSR + ddddocr 整合計畫 |
| Phase 5 Stage 4 任務規劃 | docs/agent_context/phase5/task_plan_stage4.md | RiskAssessor 恢復詳細規劃 |
| Phase 5 Stage 4 Developer Prompt | docs/agent_context/phase5/developer_prompt_stage4.md | 開發者操作指引 |
| Phase 5 Stage 5 任務規劃 | docs/agent_context/phase5/task_plan_stage5.md | E2E 整合驗證規劃 |
| Phase 5 Stage 5 Developer Prompt | docs/agent_context/phase5/developer_prompt_stage5.md | 開發者操作指引 |
| **BSR 解析器 Hotfix** | docs/agent_context/phase5/task_plan_bsr_fix.md | BSR 回傳格式變更修正 |
| 優化路線圖 | docs/OPTIMIZATION_ROADMAP.md | 效能優化規劃 |
| 系統架構 | SYSTEM_ARCHITECTURE.md | 完整架構文件 |
