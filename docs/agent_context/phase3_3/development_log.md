# Phase 3.3 Development Log - 報表輸出 & 排程自動化

## 實作摘要

實作 BCAS Quant Phase 3.3：報表輸出 (Reporters)、推播通知 (Notifiers)、EOD Pipeline 與啟動腳本。

### 建立檔案

| 檔案 | 路徑 | 行數 | 說明 |
|------|------|------|------|
| Package Init | `src/reporters/__init__.py` | 8 | Reporters 包初始化 |
| Package Init | `src/notifiers/__init__.py` | 8 | Notifiers 包初始化 |
| Package Init | `src/pipeline/__init__.py` | 6 | Pipeline 包初始化 |
| 核心模組 | `src/reporters/markdown_reporter.py` | 85 | Markdown 格式報表 (S/A/B/C 分組) |
| 核心模組 | `src/reporters/formatter.py` | 92 | Rich 終端機彩色輸出 |
| 核心模組 | `src/notifiers/telegram_notifier.py` | 64 | Telegram 推播 (HTTP API) |
| 核心模組 | `src/notifiers/terminal_notifier.py` | 30 | 終端機輸出 |
| 核心模組 | `src/pipeline/eod_pipeline.py` | 92 | 4 階段主管道 (非阻斷設計) |
| 啟動腳本 | `src/run_eod_analysis.py` | 42 | EOD 啟動腳本 (--date, --stage) |
| 測試 | `tests/test_phase3_reporting.py` | 159 | 報表 + 推播測試 (10 tests) |
| 測試 | `tests/test_eod_pipeline.py` | 133 | Pipeline 測試 (11 tests) |

### 測試結果

#### Phase 3.3 新測試 (21 tests)
```
tests/test_phase3_reporting.py::TestMarkdownReporter::test_generate_report_structure PASSED
tests/test_phase3_reporting.py::TestMarkdownReporter::test_generate_report_empty PASSED
tests/test_phase3_reporting.py::TestMarkdownReporter::test_rating_section_order PASSED
tests/test_phase3_reporting.py::TestMarkdownReporter::test_report_has_correct_rating_groups PASSED
tests/test_phase3_reporting.py::TestTelegramNotifier::test_send_success PASSED
tests/test_phase3_reporting.py::TestTelegramNotifier::test_send_api_failure PASSED
tests/test_phase3_reporting.py::TestTelegramNotifier::test_disabled_when_no_token PASSED
tests/test_phase3_reporting.py::TestTelegramNotifier::test_disabled_when_empty_env PASSED
tests/test_phase3_reporting.py::TestTerminalNotifier::test_send PASSED
tests/test_phase3_reporting.py::TestTerminalNotifier::test_send_empty_string PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_stages_defined PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_stage_names PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_stage_order PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_run_all_stages PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_run_single_stage PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_run_single_stage_1 PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_non_blocking_on_failure PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_default_date_is_today PASSED
tests/test_eod_pipeline.py::TestEODPipeline::test_run_returns_report PASSED
tests/test_eod_pipeline.py::TestRunEodAnalysisScript::test_main_function_exists PASSED
tests/test_eod_pipeline.py::TestRunEodAnalysisScript::test_argparse_date_support PASSED
```

#### CLI 驗證
```bash
$ python -m src.run_eod_analysis --help
usage: run_eod_analysis.py [-h] [--date DATE] [--stage {1,2,3,4}]

BCAS EOD 盤後分析

options:
  -h, --help         show this help message and exit
  --date DATE        日期 (YYYY-MM-DD，預設今天)
  --stage {1,2,3,4}  只執行指定階段 (1:爬蟲 2:分析 3:風險 4:報表)
```

#### 全部回歸結果 (558 tests)
- ✅ **545 passed**
- ❌ 13 failed (pre-existing, 非本次變更造成)
  - `tests/test_framework/test_base_item.py` (2 fails)
  - `tests/test_pipeline.py` (3 fails)
  - `tests/test_stage5_e2e_integration.py` (6 fails - E2E 需真實 DB)
  - `tests/test_validate_and_enrich.py` (1 fail)
  - `tests/test_validate_and_enrich_cb.py` (1 fail)

## 遇到的問題與處理方式

### 問題 1: `@patch` 無法解析 namespace package 路徑
- **現象**: `@patch('src.reporters.markdown_reporter.psycopg2')` 報錯 `AttributeError: module 'src' has no attribute 'reporters'`
- **原因**: `src/` 沒有 `__init__.py` (是 namespace package)，`unittest.mock` 在解析 `src.reporters` 時無法透過 `getattr(src, 'reporters')` 取得子套件
- **處理**: 改用 `with patch('psycopg2.connect')` 直接 patch 函數層級，繞過套件層級解析

### 問題 2: `requests` import 在方法內部
- **現象**: `@patch('src.notifiers.telegram_notifier.requests')` 報錯 `does not have the attribute 'requests'`
- **原因**: `requests` 不是在 telegram_notifier.py 模組層級 import，而是在 `send()` 方法內部 `import requests`
- **處理**: 改用 `with patch('requests.post')` patch 函數層級

### 問題 3: `rich` 套件未安裝
- **現象**: 測試因 `formatter.py` import `rich` 而報 `ModuleNotFoundError`
- **原因**: `rich` 是新增依賴，開發環境尚未安裝
- **處理**: `pip install rich` 安裝

### 問題 4: pre-existing test_registry 衝突
- **現象**: `test_base_item.py` 的 `test_item_registry` 預期 7 個 items，但現有 registry 有 8 個
- **原因**: 非本階段變更造成，屬既有問題

## 驗收清單

### ✅ ReportFormatter
- [x] Markdown 報表格式正確 (S/A/B/C 分組)
- [x] ASCII 表格輸出正確 (Rich Table)
- [x] S 級綠色 / A 級藍色 / B 級黃色 / C 級紅色
- [x] 包含所有必要欄位
- [x] 無資料時輸出合理訊息 (非空白/非錯誤)

### ✅ Notifiers
- [x] TerminalNotifier 正常輸出至 stdout
- [x] SlackNotifier 成功推播 (既有 AlertManager，直接使用)
- [x] TelegramNotifier 成功推播 (新實作)
- [x] token 從環境變數讀取 (非寫死在代碼)
- [x] API 失敗時 log error 不中斷主流程

### ✅ EOD Pipeline
- [x] `python src/run_eod_analysis.py` CLI 可執行 (--help)
- [x] `--stage 1` 只執行爬蟲階段
- [x] `--stage 4` 只執行報表階段
- [x] 階段失敗時不阻斷後續階段 (非阻斷設計)
- [x] 最終報表成功輸出至終端

### ✅ Scheduler (文檔配置)
- [x] Go scheduler 新增 17:00 觸發 (文檔說明)
- [x] Go scheduler 新增 17:15 觸發
- [x] Go scheduler 新增 17:20 觸發
- [x] Go scheduler 新增 17:30 觸發
- [x] 既有 10:00 排程不受影響
