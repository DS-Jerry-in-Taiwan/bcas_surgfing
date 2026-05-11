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
```

#### 🔄 管道編排 (Pipeline Orchestration)
```
src/
├── run_daily.py              ✅ 主管道腳本（爬蟲→驗證→清洗）
└── run_discovery.py          ✅ 發現腳本
```

#### 🗄️ 數據庫 (PostgreSQL)
```
Tables:
✅ stock_master       - 上市股票主檔
✅ stock_daily        - 股票日行情
✅ cb_master          - 可轉債主檔
✅ cb_daily           - 可轉債日行情（TimescaleDB hypertable）
✅ tpex_cb_daily      - 櫃買可轉債日行情
```

---

## 🎯 Phase 3 EOD Analytics 需求分析

根據 `analysis_mode_dev_doc.md`，系統需要在盤後執行 **4 個階段**：

| 階段 | 時間 | 狀態 | 關鍵模組 |
|------|------|------|---------|
| **一：資料採集** | 17:00 | ⚠️ 部分有 | BrokerBreakdown, ConversionPrice Spiders |
| **二：價值計算與型態** | 17:15 | ❌ 缺失 | PremiumCalculator, TechnicalAnalyzer |
| **三：籌碼分析與風險** | 17:20 | ❌ 缺失 | RiskAssessor, ChipProfiler |
| **四：報表輸出** | 17:30 | ⚠️ 部分有 | ReportFormatter, Notifiers |

---

## 🔴 缺少的模組與功能清單

### 第一類：數據採集擴展 (3 個)
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `BrokerBreakdownSpider` | HIGH | 抓取買賣超前五大券商分點 | 8-12h |
| `ConversionPriceSpider` | HIGH | 抓取 CB 最新轉換價格 | 4-6h |
| `AsBalanceSpider` | MEDIUM | 抓取 CB 承作餘額 | 4-6h |

### 第二類：核心分析引擎 (4 個)
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `PremiumCalculator` | HIGH | 轉換價值/溢價率計算 | 6-8h |
| `TechnicalAnalyzer` | HIGH | 帶量突破/均線判斷 | 10-14h |
| `RiskAssessor` | HIGH | 隔日沖風險評估 | 12-16h |
| `ChipProfiler` | HIGH | 籌碼分析與評分 | 8-12h |

### 第三類：數據模型層 (4 個)
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `SecurityProfile` | HIGH | 證券檔案對象 | 4-6h |
| `RiskScore` | HIGH | 風險評分對象 | 3-5h |
| `TradingSignal` | HIGH | 交易信號對象 | 3-5h |
| `BrokerBlacklist` | HIGH | 券商黑名單管理 | 3-5h |

### 第四類：報表與通知 (4 個)
| 模組 | 優先級 | 功能 | 工作量 |
|------|--------|------|--------|
| `ReportFormatter` | MEDIUM | Rich-based 視覺化輸出 | 6-8h |
| `TelegramNotifier` | MEDIUM | Telegram 推播 | 3-5h |
| `SlackNotifier` | MEDIUM | Slack 集成 | 3-5h |
| `LineNotifier` | MEDIUM | Line Notify 集成 | 3-5h |

### 第五類：數據庫擴展 (5 個)
| 表/索引 | 優先級 | 工作量 |
|--------|--------|--------|
| `broker_breakdown` | HIGH | 2-4h |
| `security_profile` | HIGH | 2-4h |
| `daily_analysis_results` | HIGH | 2-4h |
| `trading_signals` | HIGH | 2-4h |
| `broker_blacklist` | HIGH | 1-2h |

### 第六類：排程與自動化 (4 個)
| 功能 | 優先級 | 工作量 |
|------|--------|--------|
| EOD Pipeline 流程 | HIGH | 4-6h |
| Cron 配置 | HIGH | 2-3h |
| 錯誤告警 | MEDIUM | 3-5h |
| 性能監控 | MEDIUM | 2-4h |

### 第七類：配置與文檔 (4 個)
| 項目 | 優先級 | 工作量 |
|------|--------|--------|
| `.env` 更新 | MEDIUM | 1-2h |
| API 文檔 | MEDIUM | 2-3h |
| 數據流文檔 | MEDIUM | 2-3h |
| 運維手冊 | MEDIUM | 3-4h |

---

## 📊 完整缺失統計

### 總計
- **缺失模組**: 28 個
- **預估工作量**: 108-164 小時 (含測試)
- **推薦團隊**: 2-3 人
- **推薦時線**: 5-8 週 (每周 20-30h)

### 按優先級分類
```
HIGH (必需，影響核心功能):
  小計: 18 個項目, 80-120 小時

MEDIUM (建議，提升用戶體驗):
  小計: 10 個項目, 28-44 小時
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

## 🏛️ 推薦架構設計

### 新增目錄結構
```
src/
├── analytics/                         ✨ 新增
│   ├── models.py                      # 數據模型
│   ├── premium_calculator.py          # 溢價率計算
│   ├── technical_analyzer.py          # 技術面分析
│   ├── risk_assessor.py               # 風險評估
│   ├── chip_profiler.py               # 籌碼分析
│   └── rules/
│
├── notifiers/                         ✨ 新增
│   ├── base_notifier.py               # 基類
│   ├── telegram_notifier.py           # Telegram
│   ├── slack_notifier.py              # Slack
│   └── line_notifier.py               # Line
│
├── reporters/                         ✨ 新增
│   ├── base_reporter.py               # 基類
│   ├── markdown_reporter.py           # Markdown
│   └── formatter.py                   # Rich 格式化
│
├── pipeline/
│   ├── eod_pipeline.py                ✨ EOD 主管道
│   └── stage_*.py                     ✨ 各階段實現
│
└── run_eod_analysis.py                ✨ EOD 啟動腳本
```

### 新增 PostgreSQL 表
```sql
-- 券商買賣超明細
CREATE TABLE broker_breakdown (
    date DATE,
    symbol VARCHAR(16),
    broker_id VARCHAR(16),
    broker_name VARCHAR(64),
    buy_volume BIGINT,
    sell_volume BIGINT,
    net_volume BIGINT,
    PRIMARY KEY (date, symbol, broker_id)
);

-- 盤後分析結果
CREATE TABLE daily_analysis_results (
    date DATE,
    symbol VARCHAR(16),
    close_price NUMERIC(10,2),
    conversion_value NUMERIC(10,2),
    premium_ratio NUMERIC(5,4),
    risk_score NUMERIC(3,1),
    final_rating VARCHAR(16),  -- S/A/B/C
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol)
);

-- 交易信號
CREATE TABLE trading_signals (
    date DATE,
    symbol VARCHAR(16),
    signal_type VARCHAR(32),  -- BUY/HOLD/AVOID
    confidence NUMERIC(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, symbol, signal_type)
);

-- 券商黑名單
CREATE TABLE broker_blacklist (
    broker_id VARCHAR(16) PRIMARY KEY,
    broker_name VARCHAR(64),
    risk_level VARCHAR(16),  -- HIGH/MEDIUM/LOW
    added_date DATE
);
```

---

## 🔧 集成檢查清單

| 層級 | 檢查項目 | 狀態 |
|------|---------|------|
| 數據採集 | 新增 broker/conversion spiders | ❌ |
| 驗證層 | EOD 分析結果驗證規則 | ❌ |
| 清洗層 | EOD 表清洗邏輯 | ⚠️ |
| 管道 | run_daily.py 新增 EOD 階段 | ❌ |
| 排程 | scheduler 多時間觸發配置 | ❌ |
| 依賴 | requirements.txt (scikit-learn/numpy) | ⚠️ |
| 文檔 | API 文檔 & 運維手冊 | ❌ |

---

## 🚀 實施路線圖

### Phase 3.1 (Week 1-2): 基礎設施
- [ ] 建立 `analytics/` 目錄結構
- [ ] 實現 `SecurityProfile` 數據模型
- [ ] 創建 5 張新 PostgreSQL 表
- **工作量**: 20-28h

### Phase 3.2 (Week 2-3): 核心分析引擎
- [ ] 實現 `PremiumCalculator`
- [ ] 實現 `TechnicalAnalyzer`
- [ ] 實現 `ChipProfiler`
- **工作量**: 30-45h

### Phase 3.3 (Week 3-4): 風險評級
- [ ] 實現 `RiskAssessor`
- [ ] 實現 `TradingSignal` 生成
- **工作量**: 20-30h

### Phase 3.4 (Week 4-5): 報表與通知
- [ ] 實現 `ReportFormatter` + Notifiers
- **工作量**: 15-25h

### Phase 3.5 (Week 5+): 排程與優化
- [ ] 創建 `eod_pipeline.py`
- [ ] Cron/Cloud Scheduler 配置
- **工作量**: 15-25h

---

## 📝 關鍵風險 & 成功因素

### 核心風險
1. 📊 數據源不穩定 (TWSE/TPEX API)
2. 🎯 技術面分析規則複雜度
3. ⏰ 實時性要求 (17:00 deadline)
4. 🛡️ 分點明細爬蟲反爬蟲阻擋

### 成功關鍵
✅ 優先實現 PremiumCalculator + RiskAssessor
✅ 早期進行 E2E 測試
✅ 建立完整的規則驗證套件
✅ 監控數據源穩定性

---

**最後更新**: 2026-05-11
**文檔版本**: 1.0
