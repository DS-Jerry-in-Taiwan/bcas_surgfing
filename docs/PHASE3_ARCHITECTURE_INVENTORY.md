# BCAS Quant - Phase 3 EOD Analytics 系統盤點分析

## 📋 文件概述
本文件根據 `/docs/agent_context/phase3/analysis_mode_dev_doc.md` 的需求，盤點目前架構與新增 Phase 3 EOD Analytics 系統所缺少的模組和功能。

---

## 🏗️ 現有架構掃描結果

### 1. 核心系統版本
- **系統版本**: 3.0.0
- **主要語言**: Python (6497 行代碼) + Go (scheduler)
- **資料庫**: PostgreSQL 14 (Docker)
- **容器化**: Docker Compose (pipeline + scheduler + postgres)

### 2. 現有模組結構

#### 📦 數據採集層 (Data Ingestion)
```
src/spiders/
├── batch_spider.py           ✅ 基礎爬蟲框架
├── stock_master_spider.py    ✅ 上市股票主檔
├── stock_daily_spider.py     ✅ 日行情
├── cb_master_spider.py       ✅ 可轉債主檔
├── tpex_cb_daily_spider.py   ✅ 櫃買可轉債日行情
├── checkpoint_manager.py     ✅ 斷點恢復
└── example_spider.py         ✅ 範例爬蟲

src/framework/
├── base_spider.py            ✅ BaseSpider 類別
├── pipelines/                ✅ PostgreSQL Pipeline
└── ...其他輔助模組
```

#### 🔍 驗證層 (Data Validation)
```
src/validators/
├── checker.py                ✅ 數據驗證引擎
├── report.py                 ✅ 驗證報告類
├── report_writer.py          ✅ 報告寫入
├── stock_master_rules.py     ✅ 股票主檔規則
├── stock_daily_rules.py      ✅ 日行情驗證規則
├── cb_master_rules.py        ✅ 可轉債主檔規則
└── tpex_cb_daily_rules.py    ✅ 櫃買可轉債規則
```

#### 🧹 清洗層 (Data Cleaning/ETL)
```
src/etl/
├── run_cleaner.py            ✅ 清洗編排
├── cleaner.py                ✅ 數據清洗邏輯
├── importer.py               ✅ 數據匯入
└── validate_and_enrich.py    ✅ 驗證和豐富化

src/configs/
└── ...配置文件
```

#### 🔄 管道編排 (Pipeline Orchestration)
```
src/
├── run_daily.py              ✅ 主管道腳本（爬蟲→驗證→清洗）
└── run_discovery.py          ✅ 發現腳本
```

#### 🗄️ 數據庫
```
Tables (PostgreSQL):
✅ stock_master       - 上市股票主檔
✅ stock_daily        - 股票日行情
✅ cb_master          - 可轉債主檔
✅ cb_daily           - 可轉債日行情（TimescaleDB hypertable）
✅ tpex_cb_daily      - 櫃買可轉債日行情
```

#### 🐐 排程系統 (Go)
```
scheduler/
├── cmd/scheduler/main.go     ✅ 排程器主程式
└── ...Go 模組
```

---

## 🎯 Phase 3 EOD Analytics 需求分析

根據 `analysis_mode_dev_doc.md`，系統需要在盤後執行 **4 個階段**：

### 階段一：資料採集 (Data Ingestion) ✅ **已有**
- **觸發時間**: 17:00
- **功能**: 抓取現股/CB 收盤價、買賣超明細、成交量、轉換價格
- **現狀**: 
  - ✅ `StockMasterSpider` 抓取現股
  - ✅ `CbMasterSpider` 抓取 CB 主檔
  - ✅ `StockDailySpider` 抓取日行情
  - ✅ `TpexCbDailySpider` 抓取 CB 日行情
  - ⚠️ **缺**: 分點進出明細爬蟲 (Broker Breakdown)

### 階段二：價值計算與型態分析 (Analytics Engine) ❌ **缺少**
- **觸發時間**: 17:15
- **功能**: 
  - 計算轉換價值 (Conversion Value)
  - 計算溢價率 (Premium Ratio)
  - 技術面標記 (Breakout/MA detection)
  - 廢棄標的篩選 (>5% premium 剔除)
- **現狀**: 完全缺失
- **需要新建**:
  - `PremiumCalculator` 類別
  - `TechnicalAnalyzer` 類別
  - Analytics 規則引擎

### 階段三：籌碼分析與風險評級 (Risk Assessment) ❌ **缺少**
- **觸發時間**: 17:20
- **功能**:
  - 黑名單比對 (Broker blacklist matching)
  - 隔日沖風險計算 (Day-trading risk calculation)
  - 籌碼評分 (Chip profile scoring: S/A/B/C)
  - 綜合評級輸出 (Final rating)
- **現狀**: 完全缺失
- **需要新建**:
  - `RiskAssessor` 類別
  - `ChipProfiler` 類別
  - 風險評級模型

### 階段四：報表輸出 (Reporting) ⚠️ **部分有**
- **觸發時間**: 17:30
- **功能**:
  - 視覺化報表 (Markdown/ASCII)
  - 推播通知 (Slack/Telegram/Terminal)
  - 明日交易清單
- **現狀**: 
  - ✅ 基礎日誌輸出
  - ❌ 終端視覺化報表 (需 Rich library)
  - ❌ 推播集成 (Slack/Telegram/Line)

---

## 🔴 缺少的模組與功能清單

### 第一類：數據採集擴展
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `BrokerBreakdownSpider` | HIGH | 抓取買賣超前五大券商分點 | 8-12h |
| `ConversionPriceSpider` | HIGH | 抓取 CB 最新轉換價格 | 4-6h |
| `AsBalanceSpider` | MEDIUM | 抓取 CB 承作餘額 | 4-6h |

### 第二類：核心分析引擎
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `PremiumCalculator` | HIGH | 轉換價值/溢價率計算 | 6-8h |
| `TechnicalAnalyzer` | HIGH | 帶量突破/均線判斷 | 10-14h |
| `RiskAssessor` | HIGH | 隔日沖風險評估 | 12-16h |
| `ChipProfiler` | HIGH | 籌碼分析與評分 | 8-12h |

### 第三類：數據模型層
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `SecurityProfile` | HIGH | 證券檔案對象 (stock + cb metadata) | 4-6h |
| `RiskScore` | HIGH | 風險評分對象 | 3-5h |
| `TradingSignal` | HIGH | 交易信號對象 | 3-5h |
| `BrokerBlacklist` | HIGH | 券商黑名單管理 | 3-5h |

### 第四類：報表與通知
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `ReportFormatter` | MEDIUM | Rich-based 視覺化輸出 | 6-8h |
| `TelegramNotifier` | MEDIUM | Telegram 推播 | 3-5h |
| `SlackNotifier` | MEDIUM | Slack 集成 | 3-5h |
| `LineNotifier` | MEDIUM | Line Notify 集成 | 3-5h |

### 第五類：數據庫擴展
| 表/索引 | 優先級 | 目的 | 工作量 |
|--------|--------|------|--------|
| `broker_breakdown` | HIGH | 券商買賣超明細 | 2-4h |
| `security_profile` | HIGH | 證券統一檔案 | 2-4h |
| `daily_analysis_results` | HIGH | 盤後分析結果 | 2-4h |
| `trading_signals` | HIGH | 交易信號記錄 | 2-4h |
| `broker_blacklist` | HIGH | 已知短線客名單 | 1-2h |

### 第六類：排程與自動化
| 功能 | 優先級 | 說明 | 工作量 |
|------|--------|------|--------|
| EOD Pipeline 流程 | HIGH | 17:00/15/20/30 多階段觸發 | 4-6h |
| Cron 配置 | HIGH | Linux crontab/GCP Cloud Scheduler | 2-3h |
| 錯誤告警 | MEDIUM | Pipeline 失敗通知 | 3-5h |
| 性能監控 | MEDIUM | 執行時間追蹤 | 2-4h |

### 第七類：配置與文檔
| 項目 | 優先級 | 內容 | 工作量 |
|------|--------|------|--------|
| `.env.example` 更新 | MEDIUM | EOD 特定參數 (API keys, 券商名單位置等) | 1-2h |
| API 文檔 | MEDIUM | PremiumCalculator/RiskAssessor 文檔 | 2-3h |
| 數據流文檔 | MEDIUM | Phase 3 完整數據流圖 | 2-3h |
| 運維手冊 | MEDIUM | 部署/故障排查指南 | 3-4h |

---

## 📊 完整缺失統計

### 按優先級分類
```
HIGH (必需，影響核心功能):
  - 數據採集擴展: 3 個模組 (16-24h)
  - 分析引擎: 4 個模組 (36-50h)
  - 數據模型: 4 個對象 (13-21h)
  - 數據庫: 5 張表/索引 (9-16h)
  - 排程自動化: 2 項 (6-9h)
  小計: 18 個項目, 80-120 小時

MEDIUM (建議，提升用戶體驗):
  - 報表通知: 4 個模組 (15-23h)
  - 排程告警: 2 項 (5-9h)
  - 配置文檔: 4 項 (8-12h)
  小計: 10 個項目, 28-44 小時

總計: 28 個模組/功能, 108-164 小時工作量
```

### 按工作類型分類
```
新建 Python 類/模組: 15 個 (60-90h)
數據庫設計: 5 項 (9-16h)
排程配置: 2 項 (6-9h)
文檔編寫: 4 項 (8-12h)
集成測試: 需另計 (20-30h)
```

---

## 🏛️ 架構設計建議

### 推薦目錄結構

```
src/
├── spiders/
│   ├── ...既有爬蟲...
│   ├── broker_breakdown_spider.py     ✨ 新增
│   └── conversion_price_spider.py     ✨ 新增
│
├── analytics/                         ✨ 新增目錄
│   ├── __init__.py
│   ├── models.py                      # SecurityProfile, RiskScore, TradingSignal
│   ├── premium_calculator.py          # PremiumCalculator 類
│   ├── technical_analyzer.py          # TechnicalAnalyzer 類
│   ├── risk_assessor.py               # RiskAssessor 類
│   ├── chip_profiler.py               # ChipProfiler 類
│   └── rules/
│       ├── technical_rules.py         # 技術面規則
│       ├── risk_rules.py              # 風險評級規則
│       └── scoring_rules.py           # 評分規則
│
├── notifiers/                         ✨ 新增目錄
│   ├── __init__.py
│   ├── base_notifier.py               # 通知基類
│   ├── telegram_notifier.py           # Telegram
│   ├── slack_notifier.py              # Slack
│   ├── line_notifier.py               # Line Notify
│   └── terminal_notifier.py           # 終端輸出
│
├── reporters/                         ✨ 新增目錄
│   ├── __init__.py
│   ├── base_reporter.py               # 報表基類
│   ├── markdown_reporter.py           # Markdown 格式
│   ├── ascii_reporter.py              # ASCII 表格
│   └── formatter.py                   # Rich formatter
│
├── validators/
│   ├── ...既有驗證...
│   └── eod_analysis_rules.py          ✨ 新增 EOD 分析驗證
│
├── pipeline/
│   ├── eod_pipeline.py                ✨ 新增 EOD 主管道
│   └── stage_*.py                     ✨ 各階段實現
│
├── configs/
│   ├── eod_config.py                  ✨ 新增 EOD 配置
│   └── broker_blacklist.json          ✨ 新增 券商黑名單
│
└── run_eod_analysis.py                ✨ 新增 EOD 啟動腳本
```

### 新增 PostgreSQL 表

```sql
-- 券商買賣超明細
CREATE TABLE broker_breakdown (
    date DATE,
    symbol VARCHAR(16),
    broker_id VARCHAR(16),
    broker_name VARCHAR(64),
    buy_count INTEGER,
    buy_volume BIGINT,
    sell_count INTEGER,
    sell_volume BIGINT,
    net_volume BIGINT,
    PRIMARY KEY (date, symbol, broker_id)
);

-- 統一證券檔案
CREATE TABLE security_profile (
    symbol VARCHAR(16) PRIMARY KEY,
    type VARCHAR(16),  -- 'STOCK' or 'CB'
    name VARCHAR(64),
    issuer VARCHAR(64),
    issue_date DATE,
    maturity_date DATE,
    conversion_price NUMERIC(10,2),
    metadata JSONB
);

-- 盤後分析結果
CREATE TABLE daily_analysis_results (
    date DATE,
    symbol VARCHAR(16),
    close_price NUMERIC(10,2),
    conversion_value NUMERIC(10,2),
    premium_ratio NUMERIC(5,4),
    technical_signal VARCHAR(32),
    risk_score NUMERIC(3,1),
    risk_level VARCHAR(16),  -- S/A/B/C
    broker_risk_pct NUMERIC(5,2),
    final_rating VARCHAR(16),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol)
);

-- 交易信號
CREATE TABLE trading_signals (
    date DATE,
    symbol VARCHAR(16),
    signal_type VARCHAR(32),  -- 'BUY'/'HOLD'/'AVOID'
    confidence NUMERIC(3,2),
    entry_range TEXT,
    stop_loss NUMERIC(10,2),
    target NUMERIC(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, signal_type)
);

-- 券商黑名單
CREATE TABLE broker_blacklist (
    broker_id VARCHAR(16),
    broker_name VARCHAR(64),
    category VARCHAR(32),  -- 'DAY_TRADER', 'SUSPECTED', 'FLAGGED'
    risk_level VARCHAR(16),  -- 'HIGH', 'MEDIUM', 'LOW'
    notes TEXT,
    added_date DATE,
    PRIMARY KEY (broker_id)
);

-- 創建索引
CREATE INDEX idx_broker_breakdown_date_symbol ON broker_breakdown(date, symbol);
CREATE INDEX idx_daily_analysis_date ON daily_analysis_results(date);
CREATE INDEX idx_trading_signals_date ON trading_signals(date);
```

---

## 🔧 集成檢查清單

### 與現有系統整合點

1. **數據採集層 (run_daily.py)**
   - ❌ 需新增 step_broker_breakdown() 調用
   - ❌ 需新增 step_conversion_price() 調用

2. **驗證層 (validators/)**
   - ✅ DataValidator 已支援自定義規則
   - ❌ 需新增 EOD 分析結果驗證規則

3. **清洗層 (etl/)**
   - ✅ 架構支援新表清洗
   - ⚠️ 需自定義 EOD 表清洗邏輯

4. **排程層 (scheduler/)**
   - ✅ Go 排程器支援多時間觸發
   - ❌ 需新增 17:00/15/20/30 多階段配置

5. **數據庫 (PostgreSQL)**
   - ✅ 架構支援新表
   - ⚠️ 需執行 init_eod_tables.sql

6. **Docker**
   - ✅ docker-compose.yml 可新增服務
   - ⚠️ 需新增分析工具依賴 (scikit-learn/numpy)

---

## 🚀 實施路線圖

### Phase 3.1 (Week 1-2): 基礎設施
- [ ] 建立 `analytics/` 目錄結構
- [ ] 實現 `SecurityProfile` 數據模型
- [ ] 創建 5 張新 PostgreSQL 表
- [ ] 加載券商黑名單 CSV
- **工作量**: 20-28h

### Phase 3.2 (Week 2-3): 核心分析引擎
- [ ] 實現 `PremiumCalculator`
- [ ] 實現 `TechnicalAnalyzer`
- [ ] 實現 `ChipProfiler`
- [ ] 單元測試 & 驗證
- **工作量**: 30-45h

### Phase 3.3 (Week 3-4): 風險評級
- [ ] 實現 `RiskAssessor`
- [ ] 集成評分規則
- [ ] 實現 `TradingSignal` 生成
- [ ] 集成測試
- **工作量**: 20-30h

### Phase 3.4 (Week 4-5): 報表與通知
- [ ] 實現 `ReportFormatter`
- [ ] 實現多個 `Notifier` 類
- [ ] 終端和推播集成
- **工作量**: 15-25h

### Phase 3.5 (Week 5+): 排程與優化
- [ ] 創建 `eod_pipeline.py`
- [ ] 整合到 `run_daily.py`
- [ ] Cron/Cloud Scheduler 配置
- [ ] 性能優化和監控
- **工作量**: 15-25h

---

## 📝 總結

### 缺失模組總數: **28 個**
### 預估工作量: **108-164 小時** (含測試)
### 推薦團隊規模: **2-3 人**
### 推薦時線: **5-8 週** (每周 20-30h)

### 核心風險
1. 數據源不穩定 (TWSE/TPEX API) ⚠️
2. 技術面分析規則複雜度 ⚠️
3. 實時性要求 (17:00 deadline) ⚠️
4. 分點明細爬蟲反爬蟲阻擋 ⚠️

### 成功關鍵
✅ 優先實現 PremiumCalculator + RiskAssessor
✅ 早期進行 E2E 測試
✅ 建立完整的規則驗證套件
✅ 監控 TWSE/TPEX 數據源穩定性

