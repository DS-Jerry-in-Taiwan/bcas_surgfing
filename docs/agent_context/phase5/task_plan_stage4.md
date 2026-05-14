# Stage 4 任務規劃 — RiskAssessor 恢復

> **Phase**: Phase 5 (BSR + ddddocr 整合)
> **Stage**: 4/5 — RiskAssessor 恢復
> **更新日期**: 2026-05-13
> **負責角色**: AI Architect Team

---

## 1. 需求確認

### 1.1 任務目標

恢復完整 S/A/B/C 評級鏈，使 `broker_risk_pct` 能從 BSR 資料正確流經 ChipProfiler → RiskAssessor → `daily_analysis_results` 表。

### 1.2 成功標準

| 驗收項目 | 驗證方式 | 預期結果 |
|---------|---------|---------|
| ChipProfiler 可從 `broker_breakdown` 表讀取 BSR 資料 | 執行 `ChipProfiler.analyze(date)` | 正確回傳 risk_ratio |
| RiskAssessor 整合 ChipProfiler 結果 | 執行 `RiskAssessor.run_analysis(date)` | 評級包含風險佔比維度 |
| `broker_risk_pct` 正確寫入 DB | 查詢 `daily_analysis_results` 表 | 欄位值與 chip 計算一致 |
| BSR 查詢失敗時降級處理 | 模擬 BSR 連線失敗 | 使用 0 或前日資料，不拋錯 |
| CLI 相容 | `python -m src.analytics.risk_assessor --date YYYY-MM-DD` | 正常輸出評級結果 |

### 1.3 依賴關係

```
上游: BrokerBreakdownSpider (Stage 3, ✅ 已完成)
  → broker_breakdown 表 (BSR 資料已寫入)
  → PremiumCalculator (Stage 2, ✅ 已完成)
  → daily_analysis_results 表 (含 premium_ratio, is_junk)

下游: EOD Pipeline Stage 3 (eod_pipeline._run_risk)
  → RiskAssessor.run_analysis(date)
  → MarkdownReporter (Stage 4 報表)

測試依賴: PostgreSQL (Docker) 需正常運作
```

---

## 2. 代碼與架構掃描

### 2.1 現有實作分析

#### RiskAssessor (`src/analytics/risk_assessor.py`) — 174 行

| 方法 | 功能 | 狀態 |
|------|------|------|
| `assess(premium, risk)` | S/A/B/C 評級邏輯 | ✅ 完整，無需修改 |
| `generate_signal(rating)` | BUY/HOLD/AVOID 信號 | ✅ 完整，無需修改 |
| `run_analysis(date)` | DB 讀寫全流程 | ⚠️ 需驗證整合 |

`run_analysis()` 流程：
1. 查 `daily_analysis_results` → 取得 `symbol, premium_ratio, is_junk`
2. `ChipProfiler.analyze(date)` → 取得 `{symbol: {risk_ratio, ...}}`
3. 對每檔股票：合併評級 → UPDATE `daily_analysis_results` → UPSERT `trading_signals`

#### ChipProfiler (`src/analytics/chip_profiler.py`) — 159 行

| 方法 | 功能 | 狀態 |
|------|------|------|
| `analyze(date)` | 讀 `broker_breakdown` → 黑名單比對 → risk_ratio | ✅ 完整，無需修改 |
| `load_blacklist()` | 從 `configs/broker_blacklist.json` 載入 | ✅ 完整 |

#### DB Schema (broker_breakdown)

```sql
CREATE TABLE broker_breakdown (
    date DATE, symbol VARCHAR(16), broker_id VARCHAR(16),
    broker_name VARCHAR(64), buy_volume BIGINT, sell_volume BIGINT,
    net_volume BIGINT, rank INT, created_at TIMESTAMP,
    PRIMARY KEY (date, symbol, broker_id)
);
```

BSR spider 寫入格式 vs ChipProfiler 讀取格式完全相容。

#### DB Schema (daily_analysis_results)

```sql
CREATE TABLE daily_analysis_results (
    date DATE, symbol VARCHAR(16), close_price NUMERIC(10,2),
    conversion_value NUMERIC(10,2), premium_ratio NUMERIC(6,4),
    technical_signal VARCHAR(32), risk_score NUMERIC(3,1),
    risk_level VARCHAR(16), broker_risk_pct NUMERIC(5,2),
    final_rating VARCHAR(16), is_junk BOOLEAN, notes TEXT,
    PRIMARY KEY (date, symbol)
);
```

RiskAssessor 寫入欄位: `final_rating`, `risk_score`, `broker_risk_pct`

### 2.2 資料流 (現況)

```
BSR 網站 → BsrClient(OCR) → BrokerBreakdownSpider
  → PostgresPipeline → broker_breakdown 表
                          ↓
                   ChipProfiler.analyze()
                          ↓
                   {symbol: {risk_ratio, matched_brokers, ...}}
                          ↓
    daily_analysis_results (premium_ratio)  ← PremiumCalculator
          ↓                          ↓
          └──── RiskAssessor.assess(premium, risk) ────┘
                          ↓
              UPDATE daily_analysis_results SET
                final_rating, risk_score, broker_risk_pct
              INSERT INTO trading_signals (upsert)
```

### 2.3 變更影響範圍分析

| 檔案 | 操作 | 原因 |
|------|------|------|
| `src/analytics/risk_assessor.py` | 🔍 僅驗證 | 邏輯已完整，無需修改 |
| `src/analytics/chip_profiler.py` | 🔍 僅驗證 | 邏輯已完整，無需修改 |
| `tests/test_risk_assessor.py` | ✅ 已有（mock DB） | 無需修改，但可能需新增整合測試 |
| `tests/test_chip_profiler.py` | ✅ 已有（mock DB） | 無需修改 |
| `tests/test_stage4.py` (新增) | 📝 新增整合測試 | 需真實 DB + BSR 端到端測試 |
| `docs/agent_context/phase5/development_log.md` | 📝 更新 | 記錄 Stage 4 結果 |

---

## 3. 階段實作與測試步驟

### 3.1 Stage 4.1 — 驗證現有 S/A/B/C 評級邏輯 (0.5h)

**動作**:
1. 閱讀 `src/analytics/rules/risk_rules.py` → 確認門檻值正確
2. 閱讀 `src/analytics/risk_assessor.py` → 確認 `assess()` 與 `generate_signal()` 邏輯
3. 閱讀 `src/analytics/chip_profiler.py` → 確認 `analyze()` 從 `broker_breakdown` 讀取 + 黑名單比對

**驗證**:
```bash
python -m pytest tests/test_risk_assessor.py -v  # 16 tests
python -m pytest tests/test_chip_profiler.py -v   # 12 tests
```

**預期產出**: 確認所有單元測試通過，評級邏輯無需修改

### 3.2 Stage 4.2 — 確保 broker_risk_pct 正確傳遞 (1h)

**動作**:
1. 檢查 ChipProfiler 是否可從 `broker_breakdown` 正確讀取 BSR 資料
2. 檢查 RiskAssessor 是否正確接收 ChipProfiler 結果
3. 檢查 `daily_analysis_results` 表的 `broker_risk_pct` 寫入邏輯
4. 實作 BSR 查詢失敗時的降級處理

**降級處理邏輯**:
```
if BSR spider 失敗 (broker_breakdown 無資料):
    → chip_results = {} (empty)
    → risk_ratio = 0.0 (不影響評級)
    → 記錄警報日誌

if 部分 symbol 無 BSR 資料:
    → chip_info = chip_results.get(symbol, {})
    → risk_ratio = chip_info.get("risk_ratio", 0.0)
    → 降級為純溢價率評級
```

**驗證**:
```bash
# 確認 DB broker_breakdown 有 BSR 資料
docker exec bcas-postgres psql -U postgres -d cbas \
  -c "SELECT COUNT(*) FROM broker_breakdown WHERE date = CURRENT_DATE"

# 測試 ChipProfiler 讀取
python -c "
from src.analytics.chip_profiler import ChipProfiler
p = ChipProfiler()
r = p.analyze('2026-05-13')
print(f'Symbols: {len(r)}')
for sym, info in list(r.items())[:3]:
    print(f'  {sym}: risk={info[\"risk_ratio\"]:.1%} matched={info[\"matched_brokers\"]}')
"

# 測試 RiskAssessor
python -m src.analytics.risk_assessor --date 2026-05-13
```

### 3.3 Stage 4.3 — 整合測試 (1.5h)

**新增測試檔案**: `tests/test_stage4_risk_pipeline.py`

**測試案例**:

| 測試案例 | 說明 | mock DB? |
|---------|------|---------|
| `test_chip_profiler_reads_bsr_data` | ChipProfiler 從 broker_breakdown 表讀取 BSR 資料 | ✅ mock |
| `test_risk_assessor_receives_chip_results` | RiskAssessor 正確接收 ChipProfiler 的 risk_ratio | ✅ mock |
| `test_broker_risk_pct_written_to_db` | broker_risk_pct 正確寫入 daily_analysis_results | ✅ mock |
| `test_full_rating_chain_s_to_c` | S/A/B/C 各級別都正確通過完整鏈 | ✅ mock |
| `test_bsr_fallback_on_empty_data` | BSR 無資料時 risk_ratio=0 不拋錯 | ✅ mock |
| `test_chip_profiler_bsr_data_format` | BSR spider 寫入格式與 ChipProfiler 讀取格式相容 | ✅ mock |
| `test_eod_pipeline_stage3` | EOD Pipeline Stage 3 可正常觸發 RiskAssessor | ✅ mock |

**整合測試 (真實 DB)**:
```bash
# 完整 E2E 測試：爬蟲 → 分析 → 風險評級
python -m pytest tests/test_stage4_risk_pipeline.py -v --run-real-db
```

---

## 4. 完成標準與測試指標

### 4.1 打通標準

| 檢查項 | 通過條件 | 驗證方式 |
|--------|---------|---------|
| 單元測試 | 全部通過 | `pytest tests/test_risk_assessor.py tests/test_chip_profiler.py -v` |
| 新增測試 | 7 案例全部通過 | `pytest tests/test_stage4_risk_pipeline.py -v` |
| DB broker_risk_pct | 數值與 ChipProfiler 計算一致 | SQL 查詢比對 |
| 降級處理 | BSR 失敗時不拋錯 | mock BsrClient 拋異常 |
| CLI 相容 | `--date` 參數正常運作 | 執行 CLI 指令 |

### 4.2 量化指標

| 指標 | 當前 | 目標 |
|------|------|------|
| RiskAssessor 測試 | 16 案例 (mock) | 維持 16+ (零回歸) |
| ChipProfiler 測試 | 12 案例 (mock) | 維持 12+ (零回歸) |
| Stage 4 新增測試 | 0 | ≥ 7 案例 |
| broker_risk_pct 準確率 | N/A (無資料) | 與 BSR 原始資料一致 |

---

## 5. 開發過程與結果紀錄

### 5.1 開發日誌記錄要求

每個子階段完成後更新 `docs/agent_context/phase5/development_log.md`：
- 記錄測試通過/失敗數據
- 記錄遇到的問題與解決方案
- 記錄關鍵決策與取捨

### 5.2 Stage 4 完成後更新 project_context.md

- 將 `chip_profiler.py` 狀態從「待恢復」改為「✅ 已恢復」
- 將 `risk_assessor.py` 狀態更新為包含風險佔比評級

---

## 6. 任務邊界與禁止事項

### 6.1 邊界定義

| 項目 | 歸屬 |
|------|------|
| ✅ RiskAssessor.run_analysis() 驗證 | **屬於** Stage 4 |
| ✅ ChipProfiler.analyze() 驗證 | **屬於** Stage 4 |
| ✅ broker_risk_pct 寫入驗證 | **屬於** Stage 4 |
| ✅ 降級處理邏輯實作 | **屬於** Stage 4 |
| ✅ DB 層級整合測試 | **屬於** Stage 4 |
| ❌ RiskAssessor 評級邏輯修改 | **不屬於** (已完整) |
| ❌ ChipProfiler 黑名單比對邏輯修改 | **不屬於** (已完整) |
| ❌ PremiumCalculator 修改 | **不屬於** (Phase 3.1) |
| ❌ EOD Pipeline Stage 4 報表修改 | **不屬於** (Phase 3.3) |
| ❌ BsrClient 修改 | **不屬於** (Stage 2) |
| ❌ BrokerBreakdownSpider 修改 | **不屬於** (Stage 3) |

### 6.2 禁止事項

- 禁止修改 `assess()` 評級邏輯
- 禁止修改 `RATING_THRESHOLDS` 或 `SIGNAL_MAP`
- 禁止新增 DB 表或修改 schema
- 禁止改動 `ChipProfiler` 的黑名單載入機制
- 禁止在降級處理中拋出未捕獲異常
- 禁止依賴真實 DB 端到端測試作為唯一驗證方式 (必須有 mock 測試)

---

## 7. 其他影響因素

### 7.1 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|---------|
| PostgreSQL 未啟動 | 低 | 中 | 使用 mock 測試驗證邏輯；真實 DB 測試需先檢查 `docker ps` |
| BSR 網站變更格式 | 低 | 高 | ChipProfiler 讀 `broker_breakdown` 表而非直接爬 BSR，有隔離 |
| broker_breakdown 無資料 | 中 | 低 | 降級處理：risk_ratio=0，純溢價率評級 |
| 黑名單 JSON 不存在 | 低 | 低 | ChipProfiler 已處理（空字典，不拋錯） |

### 7.2 測試策略

```
測試金字塔（Stage 4）:
         ╱╲
        ╱  ╲       1 E2E (真實 DB 選測)
       ╱    ╲
      ╱      ╲     7 整合測試 (mock DB)
     ╱────────╲
    ╱          ╲   28 既有單元測試 (RiskAssessor 16 + ChipProfiler 12)
   ╱────────────╲
```

### 7.3 回滾策略

若 Stage 4 整合後發現問題：
1. RiskAssessor 和 ChipProfiler 本身無程式碼修改，無需回滾
2. 僅需移除新增的測試檔案（如有）
3. DB 資料不受影響（僅 UPDATE 操作，可重新執行）

---

## 8. 時程預估

| 子階段 | 工時 | 說明 |
|--------|------|------|
| 4.1 驗證評級邏輯 | 0.5h | 閱讀程式碼 + 執行既有測試 |
| 4.2 broker_risk_pct 傳遞 | 1h | 檢查資料流 + 實作降級處理 |
| 4.3 整合測試 | 1.5h | 新增 7 測試案例 + E2E 驗證 |
| **總計** | **3h** | |

---

## 9. 參考資料

- `docs/agent_context/phase5/02_work_breakdown.md` — WBS 原始規劃
- `docs/agent_context/phase5/development_log.md` — 開發日誌
- `src/analytics/risk_assessor.py` — RiskAssessor 實作
- `src/analytics/chip_profiler.py` — ChipProfiler 實作
- `src/analytics/rules/risk_rules.py` — 評級規則常數
- `src/db/init_eod_tables.sql` — DB Schema
- `tests/test_risk_assessor.py` — 現有 16 測試案例
- `tests/test_chip_profiler.py` — 現有 12 測試案例
