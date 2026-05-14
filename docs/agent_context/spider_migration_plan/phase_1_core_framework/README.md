# Phase 1: 核心 Feapder 框架整合

## 概述

Phase 1 專注於建立 Feapder 框架的基礎設施，包括核心類別、配置系統、告警機制與打通測試。

---

## 文件架構

```
phase_1_core_framework/
├── README.md                    # 本文件
├── feapder_settings_spec.md     # 配置系統規範
├── slack_alert_spec.md          # Slack 告警機制規範
├── e2e_test_spec.md             # 全鏈路打通測試規範
└── DEVELOPER_PROMPT.md          # Developer Agent 工作指引
```

---

## Phase 1 任務地圖

```
┌─────────────────────────────────────────────────────────────────┐
│                      Phase 1: 核心 Feapder 框架整合              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │ Task 1       │    │ Task 2       │    │ Task 3       │    │
│  │ 框架類別實作  │───▶│ 配置系統     │───▶│ 告警機制     │    │
│  │ (已完成)      │    │ (待實作)     │    │ (待實作)     │    │
│  └──────────────┘    └──────────────┘    └──────────────┘    │
│         │                                    │               │
│         │               ┌──────────────┐    │               │
│         └──────────────▶│ Task 4       │◀───┘               │
│                         │ 打通測試     │                      │
│                         │ (待實作)     │                      │
│                         └──────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 文件說明

### 1. feapder_settings_spec.md

定義 `.env` 環境變數到 Feapder 配置的對接規範。

**主要內容：**
- 環境變數命名規範
- `DatabaseConfig` 資料類別
- `RedisConfig` 資料類別
- `SlackAlertConfig` 資料類別
- `FeapderSettings` 全域配置

**實作目標：**
```python
from src.settings import settings
settings.database.connection_string  # postgresql://...
settings.redis.url                    # redis://...
settings.slack_alert.is_configured    # True/False
```

### 2. slack_alert_spec.md

定義 Slack 告警機制的觸發點與實作規範。

**觸發點：**
- `on_exception` → ERROR
- `parse` 返回空 → WARNING
- `save_item` 異常 → ERROR
- `end_callback` → INFO

**實作目標：**
```python
from src.framework.alerts import alert_manager, AlertLevel

alert_manager.error(title="Error", message="...")
alert_manager.info(title="Completed", message="...")
```

### 3. e2e_test_spec.md

定義 ExampleSpider 需完成的完整流程測試。

**測試案例：**
| ID | 名稱 | 驗證目標 |
|----|------|----------|
| TC-01 | 單筆爬取 | 成功抓取 TWSE 資料 |
| TC-02 | 多筆爬取 | 批次處理多支股票 |
| TC-03 | CSV 寫入 | Pipeline 正確寫入 |
| TC-04 | 去重測試 | 不重複寫入 |
| TC-05 | 錯誤處理 | 異常被正確處理 |
| TC-06 | 統計追蹤 | 數值正確記錄 |

### 4. DEVELOPER_PROMPT.md

提供給 Developer Agent 的完整工作指引。

**實作清單：**
- [x] `src/settings/feapder_settings.py`
- [x] `src/framework/alerts.py`
- [x] `src/spiders/example_spider.py`
- [x] `tests/test_framework/test_alerts.py`
- [x] `tests/test_framework/test_example_spider.py`

---

## 進度追蹤

### 已完成

- [x] BaseSpider 類別邏輯
- [x] BaseItem 資料模型
- [x] Pipeline 實作
- [x] 例外定義
- [x] 單元測試（57 個）

### 待完成

- [x] 安裝 Feapder 框架
- [x] 實作 `src/settings/feapder_settings.py`
- [x] 實作 `src/framework/alerts.py`
- [x] 實作 `src/spiders/example_spider.py`
- [x] 實作告警單元測試
- [x] 實作 ExampleSpider 測試
- [x] 全鏈路打通測試

---

## 驗收標準

Phase 1 完成條件：

```
1. 所有新實作通過單元測試
2. ExampleSpider 可完整執行
3. CSV 輸出正確
4. Slack 告警可觸發（需已配置）
5. 測試覆蓋率 > 80%
```

---

## 技術參考

### Feapder 文件
- GitHub: https://github.com/shengxuanyao/feapder
- 文件: https://feapder.com/

### Slack Block Kit
- 文件: https://api.slack.com/reference/block-kit

---

## 下一階段

Phase 1 完成後進入 [Phase 2: 主檔爬蟲遷移](../phase_2_master_migration/)

---

*文件版本：1.0.0*
*更新時間：2026-04-15*
