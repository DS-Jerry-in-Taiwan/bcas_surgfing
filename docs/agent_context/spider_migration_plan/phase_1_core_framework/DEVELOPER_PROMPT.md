# Developer Prompt - Phase 1 補充任務

## 概述

本 Prompt 定義 Phase 1 的剩餘工作，Developer Agent 需完成以下項目以確保框架完整可用。

---

## 1. 已完成項目

| 項目 | 狀態 | 檔案 |
|------|------|------|
| BaseSpider 類別邏輯 | ✅ | `src/framework/base_spider.py` |
| BaseItem 資料模型 | ✅ | `src/framework/base_item.py` |
| Pipeline 實作 | ✅ | `src/framework/pipelines.py` |
| 例外定義 | ✅ | `src/framework/exceptions.py` |
| 單元測試 | ✅ | `tests/test_framework/*.py` |

---

## 2. 待完成項目

### 2.1 安裝 Feapder 框架

```bash
# 更新 requirements.txt
echo "feapder" >> requirements.txt

# 安裝
source .venv/bin/activate
pip install feapder
```

### 2.2 建立設定模組

**目標檔案**: `src/settings/feapder_settings.py`

實作規範：`docs/agent_context/spider_migration_plan/phase_1_core_framework/feapder_settings_spec.md`

```python
# src/settings/__init__.py
from .feapder_settings import settings, FeapderSettings

__all__ = ["settings", "FeapderSettings"]
```

### 2.3 建立告警模組

**目標檔案**: `src/framework/alerts.py`

實作規範：`docs/agent_context/spider_migration_plan/phase_1_core_framework/slack_alert_spec.md`

```python
# src/framework/alerts.py 需包含：
# - AlertLevel 枚舉
# - AlertMessage dataclass
# - SlackAlertBackend 類別
# - AlertManager 類別
```

### 2.4 建立 ExampleSpider

**目標檔案**: `src/spiders/example_spider.py`

實作規範：`docs/agent_context/spider_migration_plan/phase_1_core_framework/e2e_test_spec.md`

```python
# src/spiders/__init__.py
from .example_spider import ExampleSpider

__all__ = ["ExampleSpider"]
```

### 2.5 建立單元測試

**目標檔案**: `tests/test_framework/test_alerts.py`

```python
# 測試內容：
# - TestAlertLevel
# - TestAlertMessage
# - TestSlackAlertBackend
# - TestAlertManager
```

**目標檔案**: `tests/test_framework/test_example_spider.py`

```python
# 測試內容：
# - test_single_stock_crawl (TC-01)
# - test_multi_stock_crawl (TC-02)
# - test_csv_pipeline_write (TC-03)
# - test_deduplication (TC-04)
# - test_error_handling (TC-05)
# - test_statistics (TC-06)
```

---

## 3. 完整實作清單

### 3.1 新建目錄結構

```
src/
├── settings/
│   ├── __init__.py          # 匯出 settings
│   └── feapder_settings.py  # 設定模組
├── spiders/
│   ├── __init__.py          # 匯出爬蟲
│   └── example_spider.py    # 範例爬蟲
└── framework/
    └── alerts.py            # 告警模組 (新增)

tests/
└── test_framework/
    ├── test_alerts.py       # 告警測試 (新增)
    └── test_example_spider.py # 範例爬蟲測試 (新增)
```

### 3.2 實作清單

| # | 檔案 | 預估行數 | 優先級 |
|---|------|----------|--------|
| 1 | `src/settings/__init__.py` | 10 | 高 |
| 2 | `src/settings/feapder_settings.py` | 200 | 高 |
| 3 | `src/framework/alerts.py` | 250 | 高 |
| 4 | `src/spiders/__init__.py` | 10 | 高 |
| 5 | `src/spiders/example_spider.py` | 300 | 高 |
| 6 | `tests/test_framework/test_alerts.py` | 150 | 中 |
| 7 | `tests/test_framework/test_example_spider.py` | 200 | 中 |

---

## 4. 測試驗證

### 4.1 執行順序

```bash
# 1. 安裝 Feapder
pip install feapder

# 2. 執行單元測試
python -m pytest tests/test_framework/test_base_*.py -v

# 3. 執行告警測試
python -m pytest tests/test_framework/test_alerts.py -v

# 4. 執行 ExampleSpider 測試
python -m pytest tests/test_framework/test_example_spider.py -v

# 5. 執行全鏈路測試
python -m pytest tests/test_framework/ -v --tb=short
```

### 4.2 通過標準

```
測試類別          | 通過標準
-----------------|----------
現有單元測試      | 57 passed
告警測試         | 10 passed
ExampleSpider 測試 | 6 passed
全鏈路測試        | 73+ passed
```

---

## 5. 環境變數需求

更新 `.env.example`:

```bash
# ===== Database =====
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bcas_quant
DB_USER=postgres
DB_PASSWORD=

# ===== Redis =====
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_KEY=feapder:spider

# ===== Slack Alert =====
SLACK_WEBHOOK_URL=
SLACK_CHANNEL=#crawler-alerts
SLACK_ALERT_ENABLED=false
SLACK_ALERT_LEVEL=ERROR

# ===== Spider Settings =====
SPIDER_HEADERS=
SPIDER_THREAD_COUNT=1
SPIDER_RETRY_TIMES=3
SPIDER_RETRY_DELAY=5

# ===== Proxy =====
PROXY_LIST=
PROXY_ENABLED=false
```

---

## 6. 交付清單

完成後請確保以下檔案存在且測試通過：

- [ ] `src/settings/feapder_settings.py`
- [ ] `src/framework/alerts.py`
- [ ] `src/spiders/example_spider.py`
- [ ] `tests/test_framework/test_alerts.py`
- [ ] `tests/test_framework/test_example_spider.py`
- [ ] `requirements.txt` 包含 `feapder`
- [ ] `.env.example` 已更新

---

## 7. 驗收標準

- [ ] `pip install feapder` 成功
- [ ] `from src.settings import settings` 成功
- [ ] `from src.framework.alerts import alert_manager` 成功
- [ ] `from src.spiders import ExampleSpider` 成功
- [ ] `python -m pytest tests/test_framework/ -v` 通過率 > 95%
- [ ] ExampleSpider 可成功抓取 TWSE 資料並寫入 CSV

---

*Prompt 版本：1.0.0*
*產生時間：2026-04-15*
*Architect Agent*
