# Phase 5 — BSR Captcha OCR 解決方案

**階段**: Phase 5 (Data Source Recovery via OCR)
**專案**: BCAS Quant v3.0.0 → BrokerBreakdownSpider Captcha 整合
**日期**: 2026-05-13
**狀態**: 📋 規劃中

---

## 1. 背景與動機

### 1.1 Phase 4 回顧
Phase 4 針對 TWSE MI_20S API 下架進行了全面替代方案評估，結論如下：

| 方案 | 結果 | 原因 |
|------|------|------|
| twstock SDK | ❌ 無分點資料 | 僅提供歷史股價、即時報價、技術分析 |
| FinMind API | ⚠️ 有資料但有限制 | 免費方案有呼叫次數限制，需註冊 Token |
| Shioaji (永豐) | ⚠️ 需券商開戶 | 非免費方案，且可能超出專案範圍 |
| Goodinfo 爬蟲 | ❌ 反爬蟲嚴格 | 需要動態解析，維護成本高 |
| **BSR + OCR** | **✅ 最佳路徑** | 官方資料源，僅需克服 Captcha |

### 1.2 BSR 網站調查結果

BSR 網站 (`https://bsr.twse.com.tw/bshtm/`) 仍有完整的券商分點買賣超資料：

- **架構**: ASP.NET Web Forms (frameset)
- **左框架**: `bsMenu.aspx` — 查詢表單 + Captcha
- **右框架**: `bsWelcome.aspx` — 結果顯示
- **Captcha**: 5 碼文數字 (字母+數字混合)，200x60 PNG
- **所需隱藏欄位**: `__VIEWSTATE`, `__EVENTVALIDATION`, `__VIEWSTATEGENERATOR`

### 1.3 選定技術 — ddddocr

| 特性 | 說明 |
|------|------|
| 套件 | `pip install ddddocr` |
| GitHub | https://github.com/sml2h3/ddddocr (7k+ stars) |
| 模型 | ONNX 輕量模型，專為驗證碼設計 |
| 硬體 | CPU 即可，單張推論 < 100ms |
| 辨識 | 數字 + 英文混合支援 |

---

## 2. 🎯 開發目標

### 主要目標

| # | 目標 | 說明 |
|---|------|------|
| G1 | **驗證 ddddocr 對 BSR Captcha 的辨識率** | 至少 100 次測試，統計成功率 |
| G2 | **實作 BSR 完整查詢流程** | Session → Captcha → OCR → 表單提交 → 結果解析 |
| G3 | **改寫 BrokerBreakdownSpider** | 使用 BSR + OCR 替代 MI_20S API |
| G4 | **恢復 RiskAssessor 完整評級** | 重新啟用 broker_risk_pct 進行 S/A/B/C 評級 |
| G5 | **確保與 run_daily.py 相容** | 維持 collect_only + pipeline 流程 |

### 次要目標

| # | 目標 | 說明 |
|---|------|------|
| G6 | 錯誤處理與降級機制 | Captcha 重試、Session 逾時處理、Circuit Breaker |
| G7 | 監控與日誌 | 記錄 captcha 成功率、請求耗時、錯誤統計 |

---

## 3. 成功標準

### 3.1 OCR 辨識率測試 (Gate Criteria)

| 指標 | 目標 | 說明 |
|------|------|------|
| 測試樣本數 | ≥ 100 | 連續不同 session 下載 |
| 首次辨識成功率 (1st-attempt) | ≥ 80% | 不經重試直接成功的比例 |
| 3 次重試累計成功率 | ≥ 95% | 最多 3 次重試的成功比例 |
| 平均辨識耗時 | < 500ms | 從下載圖片到 OCR 完成 |

### 3.2 功能整合 (Acceptance Criteria)

| 指標 | 目標 | 說明 |
|------|------|------|
| 單股查詢成功率 | ≥ 95% | 含重試機制後的成功查詢 |
| BrokerBreakdownItem 正確性 | 100% | 欄位對應完整，無資料遺失 |
| collect_only 模式 | ✅ 不變 | 維持暫存 → 驗證 → flush 流程 |
| run_daily.py 相容 | ✅ | 無需修改 run_daily.py 主流程 |

### 3.3 RiskAssessor 恢復標準

| 指標 | 目標 |
|------|------|
| broker_risk_pct 回填 | 每日分析中 broker_risk_pct 不為 NULL |
| S/A/B/C 評級使用 broker_risk_pct | 與 RATING_THRESHOLDS 定義一致 |
| ChipProfiler 讀取 BSR 資料 | 從 broker_breakdown 表正確讀取 |

---

## 4. 任務邊界 (Scope)

### 4.1 範圍內 (In-Scope)

- ✅ 安裝並測試 ddddocr
- ✅ 下載 BSR Captcha 圖片進行批量辨識測試
- ✅ 實作 BSR Session 管理 (ASP.NET Web Forms)
- ✅ 實作 Captcha 下載 → OCR → 表單提交 → 結果解析流程
- ✅ 改寫 BrokerBreakdownSpider 支援 BSR 資料源
- ✅ 恢復 RiskAssessor 完整評級邏輯
- ✅ 撰寫測試腳本與整合測試

### 4.2 範圍外 (Out-of-Scope)

- ❌ 不需要註冊任何第三方 API (FinMind, Shioaji 等)
- ❌ 不需要修改 run_daily.py 的主要流程 (step_spiders 保持相容)
- ❌ 不需要修改 DB schema (broker_breakdown 表結構不變)
- ❌ 不需要處理鉅額交易 (RadioButton_Excd) — 只處理一般交易
- ❌ 不需要支援分散式或多線程 Captcha 請求
- ❌ 不重新發明 ddddocr 或訓練自定義模型

---

## 5. 關鍵交付物

| 交付物 | 說明 |
|--------|------|
| `research/backtests/ocr_test_results/` | OCR 測試結果目錄 |
| `research/backtests/ocr_test_results/samples/` | 下載的 captcha 圖片樣本 |
| `src/spiders/bsr_client.py` | BSR 網站客戶端 (Session + Captcha + 表單提交) |
| `src/spiders/ocr_solver.py` | ddddocr 封裝模組 |
| `src/spiders/broker_breakdown_spider.py` | 改寫後的 spider |
| `src/analytics/risk_assessor.py` | 恢復完整評級的 RiskAssessor |
| `tests/test_bsr_client.py` | 整合測試 |
| `docs/agent_context/phase5/development_log.md` | 開發日誌 |

---

## 6. 架構概覽

```
┌─────────────────────────────────────────────────────┐
│                   run_daily.py                       │
│  step_spiders() → validate → flush_pipelines()       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           BrokerBreakdownSpider                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  BsrClient (新模組)                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │  │
│  │  │ Session  │─▶│ Captcha │─▶│ Form Submit  │ │  │
│  │  │ Manager  │  │ OCR      │  │ & Parse      │ │  │
│  │  └──────────┘  └──────────┘  └──────────────┘ │  │
│  │                   ┌──────────┐                 │  │
│  │                   │ ddddocr  │                 │  │
│  │                   └──────────┘                 │  │
│  └────────────────────────────────────────────────┘  │
│  collect_only=True → items[] → flush_items()         │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           ChipProfiler → RiskAssessor                │
│  broker_breakdown table → risk_ratio → S/A/B/C       │
└─────────────────────────────────────────────────────┘
```

---

## 7. 前置條件

| # | 條件 | 確認方法 |
|---|------|---------|
| P1 | Python 3.8+ | `python3 --version` |
| P2 | ddddocr 可安裝 | `pip install ddddocr` |
| P3 | BSR 網站可連線 | `curl -I https://bsr.twse.com.tw/bshtm/` |
| P4 | 現有 BrokerBreakdownSpider 正常 | `python3 -m src.spiders.broker_breakdown_spider --date 20260509 --symbol 2330` |
| P5 | 現有 RiskAssessor 可執行 | `python3 -m src.analytics.risk_assessor --date 2026-05-11` |

---

## 8. 時間估算

| 階段 | 工作項目 | 預估工時 | 依賴 |
|------|---------|---------|------|
| 1 | ddddocr 環境安裝 + 辨識率測試 | 3h | P1, P2, P3 |
| 2 | BsrClient 實作 (Session + Captcha + Submit) | 6h | 階段 1 |
| 3 | BrokerBreakdownSpider 改寫 | 4h | 階段 2 |
| 4 | RiskAssessor 恢復 + 整合測試 | 3h | 階段 3 |
| 5 | run_daily.py 整合 + E2E 驗證 | 2h | 階段 4 |
| **合計** | | **18h** | |

---

## 9. 相關文件

| 文件 | 位置 |
|------|------|
| 工作分解 | `02_work_breakdown.md` |
| OCR 測試計畫 | `03_ocr_test_plan.md` |
| 架構設計 | `arch_design.md` |
| 風險評估 | `05_risk_assessment.md` |
| Phase 4 調查 | `docs/agent_context/phase4/` |
