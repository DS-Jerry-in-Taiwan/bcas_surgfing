# Stage 4 Developer Prompt — RiskAssessor 恢復

## 任務描述

驗證並恢復完整 S/A/B/C 評級鏈，確保 BSR 資料正確流經 ChipProfiler → RiskAssessor → `daily_analysis_results.broker_risk_pct`。

**Phase 5 已完成進度**:
- Stage 1 (OCR 測試): ✅ ddddocr 辨識率 100%
- Stage 2 (BSR Client): ✅ BsrClient + OcrSolver (59 tests)
- Stage 3 (Spider 改寫): ✅ BrokerBreakdownSpider (77 tests)
- **Stage 4 (RiskAssessor 恢復): ⬅️ 當前任務**
- Stage 5 (E2E 驗證): ⏳ 待執行

---

## 開發目標

### 主要目標
1. 驗證 RiskAssessor S/A/B/C 評級邏輯在 BSR 資料源下正常運作
2. 確保 ChipProfiler 可從 `broker_breakdown` 表正確讀取 BSR 資料
3. 確保 `broker_risk_pct` 正確寫入 `daily_analysis_results` 表
4. 實作 BSR 查詢失敗時的降級處理

### 次要目標
- 新增 7 個整合測試案例 (mock DB)
- 所有既有測試零回歸

---

## 背景資訊

### 資料流

```
BSR 網站 → BsrClient(OCR) → BrokerBreakdownSpider
  → PostgresPipeline → broker_breakdown 表
                          ↓
                   ChipProfiler.analyze(date)
                          ↓
                   {symbol: {risk_ratio, matched_brokers, ...}}
                          ↓
    daily_analysis_results (premium_ratio)  ← PremiumCalculator.analyze(date)
          ↓                          ↓
          └──── RiskAssessor.assess(premium, risk) ────┘
                          ↓
              UPDATE daily_analysis_results SET
                final_rating, risk_score, broker_risk_pct
              INSERT INTO trading_signals (date, symbol, signal_type, confidence, notes)
```

### 評級規則 (無需修改)

```
S (強烈買入): 溢價率 < 2% AND 風險佔比 < 10%
A (可布局):   溢價率 < 3% AND 風險佔比 < 20%
B (觀察):     溢價率 < 5% AND 風險佔比 < 30%
C (避開):     其餘情況
```

### DB schema

`daily_analysis_results` 相關欄位:
- `final_rating` VARCHAR(16) — S/A/B/C
- `risk_score` NUMERIC(3,1) — risk_ratio * 100 (e.g. 5.0 = 5%)
- `broker_risk_pct` NUMERIC(5,2) — risk_ratio * 100 (e.g. 5.00 = 5%)

### 既有測試套件

```bash
# Stage 4 前需確認這些全部通過
python -m pytest tests/test_risk_assessor.py -v    # 16 tests
python -m pytest tests/test_chip_profiler.py -v    # 12 tests
python -m pytest tests/test_bsr_client.py -v       # 59 tests
python -m pytest tests/test_broker_breakdown_spider.py -v  # 18 tests
```

---

## 具體實作要求

### 1. RiskAssessor 與 ChipProfiler 不修改程式碼

這兩個模組在 Phase 3.2 已完整實作且測試通過。Stage 4 的任務是**驗證整合**而非修改邏輯。唯一可能需要新增的是：

**降級處理** — 在 `RiskAssessor.run_analysis()` 或調用端確保 BSR 失敗時不拋錯：
- 若 `ChipProfiler.analyze(date)` 回傳空字典 → `risk_ratio = 0.0`
- 若特定 symbol 無 chip 資料 → `chip_info.get("risk_ratio", 0.0)`

### 2. 新增測試檔案: `tests/test_stage4_risk_pipeline.py`

```python
"""
Stage 4: RiskAssessor Pipeline 整合測試

測試範圍:
  1. ChipProfiler 可從 broker_breakdown 讀取 BSR 格式資料
  2. RiskAssessor.run_analysis() 正確接收 ChipProfiler 結果
  3. broker_risk_pct 正確寫入 daily_analysis_results
  4. 完整評級鏈 (premium + risk → S/A/B/C)
  5. BSR 資料為空時的降級處理
  6. ChipProfiler 與 BSR spider 資料格式相容性
  7. EOD Pipeline Stage 3 觸發 RiskAssessor
"""
```

#### 測試案例 1: `test_chip_profiler_reads_bsr_data`

模擬 `broker_breakdown` 表含 BSR 格式資料，確認 ChipProfiler 正確解析。

```python
@patch("src.analytics.chip_profiler.psycopg2")
def test_chip_profiler_reads_bsr_data(mock_psycopg2):
    """ChipProfiler 可從 broker_breakdown 讀取 BSR 格式資料"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # BSR spider 寫入 broker_breakdown 的資料格式
    mock_cursor.fetchall.return_value = [
        ("2330", "9200", "凱基-台北", 1000, 100, 900),  # 黑名單 HIGH
        ("2330", "9800", "元大-台北", 800, 200, 600),   # 黑名單 HIGH
        ("2330", "8888", "一般券商", 500, 300, 200),     # 非黑名單
    ]

    profiler = ChipProfiler()
    profiler.blacklist = {
        "9200": {"broker_name": "凱基-台北", "risk_level": "HIGH"},
        "9800": {"broker_name": "元大-台北", "risk_level": "HIGH"},
    }

    results = profiler.analyze("2026-05-13")

    assert "2330" in results
    info = results["2330"]
    assert info["suspect_volume"] == 1800  # 1000 + 800
    assert info["total_volume"] == 2300    # 1000 + 800 + 500
    assert info["risk_ratio"] == pytest.approx(0.7826, rel=1e-3)
    assert len(info["matched_brokers"]) == 2
```

#### 測試案例 2: `test_risk_assessor_receives_chip_results`

驗證 RiskAssessor.run_analysis() 內正確調用 ChipProfiler.analyze() 並使用其結果。

```python
@patch("src.analytics.risk_assessor.psycopg2")
@patch("src.analytics.risk_assessor.ChipProfiler")
def test_risk_assessor_receives_chip_results(mock_chip_profiler, mock_psycopg2):
    """RiskAssessor 使用 ChipProfiler 的 risk_ratio 進行評級"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    # daily_analysis_results 資料 (含溢價率)
    mock_cursor.fetchall.return_value = [
        ("2330", 0.01, False),   # premium=1%, 非廢棄
    ]

    # ChipProfiler 回傳 risk_ratio
    mock_profiler = MagicMock()
    mock_chip_profiler.return_value = mock_profiler
    mock_profiler.analyze.return_value = {
        "2330": {"risk_ratio": 0.05, "matched_brokers": ["凱基-台北"]},
    }

    ra = RiskAssessor()
    results = ra.run_analysis("2026-05-13")

    assert len(results) == 1
    r = results[0]
    assert r["symbol"] == "2330"
    assert r["rating"] == "S"     # premium=1%, risk=5% → S
    assert r["risk_ratio"] == 0.05
    assert r["premium_ratio"] == 0.01

    # 驗證 broker_risk_pct 寫入 (risk_ratio * 100)
    update_call = mock_cursor.execute.call_args_list[1]  # 第一個 UPDATE
    assert update_call[0][0] == pytest.raises(...)  # 驗證 SQL
    # 實際驗證: 查看 SQL 參數
    args = update_call[0][1]
    assert args[0] == "S"           # rating
    assert args[1] == 5.0           # risk_score (0.05 * 100)
    assert args[2] == 5.0           # broker_risk_pct (0.05 * 100)
```

#### 測試案例 3: `test_broker_risk_pct_written_to_db`

直接驗證 `daily_analysis_results` 的 UPDATE SQL 語句參數正確。

#### 測試案例 4: `test_full_rating_chain_s_to_c`

測試所有評級透過完整的 premium + risk 鏈：
- premium=1%, risk=5% → S
- premium=2.5%, risk=15% → A
- premium=4%, risk=25% → B
- premium=6%, risk=35% → C

#### 測試案例 5: `test_bsr_fallback_on_empty_data`

BSR 無資料時（ChipProfiler 回傳空字典），不拋錯且 risk_ratio=0。

#### 測試案例 6: `test_chip_profiler_bsr_data_format`

BSR spider 寫入的 broker_breakdown 欄位與 ChipProfiler 讀取欄位完全對應。

#### 測試案例 7: `test_eod_pipeline_stage3`

EOD Pipeline 的 `_run_risk()` 可正常呼叫 RiskAssessor.run_analysis()。

---

## 專案規範

### 必須遵循

- **不在 RiskAssessor / ChipProfiler 中修改任何評級邏輯**
- 使用 `@patch` mock DB 連線進行測試（不依賴真實 DB）
- 測試使用 `MagicMock` 模擬 cursor/connection
- 新增測試檔案命名: `tests/test_stage4_risk_pipeline.py`
- 遵循現有測試風格（class-based, 清晰 docstring）

### 禁止事項

- ❌ 禁止修改 `RATING_THRESHOLDS` 或 `SIGNAL_MAP`
- ❌ 禁止修改 `assess()` 或 `generate_signal()` 方法
- ❌ 禁止修改 ChipProfiler 的黑名單載入機制
- ❌ 禁止新增 DB 表或修改 DB schema
- ❌ 禁止在降級處理中拋出未捕獲異常
- ❌ 禁止依賴真實 PostgreSQL 作為唯一驗證方式

---

## 驗收標準

### 1. 既有測試零回歸

```bash
python -m pytest tests/test_risk_assessor.py tests/test_chip_profiler.py -v
# 結果: 28 passed (16 + 12)
```

### 2. 新增測試全部通過

```bash
python -m pytest tests/test_stage4_risk_pipeline.py -v
# 結果: 7 passed
```

### 3. 降級處理驗證

手動驗證: 當 `broker_breakdown` 表無資料時，RiskAssessor 仍正常執行。

```bash
# 模擬無 BSR 資料
python -c "
from src.analytics.chip_profiler import ChipProfiler
from unittest.mock import patch, MagicMock

with patch('src.analytics.chip_profiler.psycopg2') as mock_db:
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_db.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []  # 空資料

    profiler = ChipProfiler()
    results = profiler.analyze('2026-05-13')
    assert results == {}, f'Expected empty dict, got {results}'
    print('降級處理驗證: ✅ 空資料不拋錯')
"
```

### 4. CLI 相容

```bash
python -m src.analytics.risk_assessor --date 2026-05-13
# 必須正常輸出，不能因缺少 DB 而崩潰（需要真實 DB 時才測試）
```

---

## 預期產出

| 產出 | 路徑 | 說明 |
|------|------|------|
| 測試檔案 | `tests/test_stage4_risk_pipeline.py` | 7 個整合測試案例 |
| 開發日誌更新 | `docs/agent_context/phase5/development_log.md` | 記錄 Stage 4 結果 |
| 降級處理 | 內嵌於現有程式碼（無需修改） | 確認 `risk_ratio=0` 降級路徑通暢 |

---

## 時程

| 子階段 | 工時 | 說明 |
|--------|------|------|
| 4.1 驗證評級邏輯 | 0.5h | 閱讀 + 執行既有測試 |
| 4.2 broker_risk_pct 傳遞 | 1.0h | 檢查資料流 + 降級處理 |
| 4.3 整合測試 | 1.5h | 7 測試案例 + E2E 驗證 |
| **合計** | **3h** | |
