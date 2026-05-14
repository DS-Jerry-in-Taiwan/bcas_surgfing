# Phase 4 - BrokerBreakdown 資料源替代方案評估與實作

**階段**: Phase 4 (Data Source Migration)
**專案**: BCAS Quant v3.0.0 → BrokerBreakdown 資料源修復

**背景**: 
Phase 3.0 實作的 BrokerBreakdownSpider 使用 TWSE MI_20S API，但該 API 已遭 TWSE 下架
(回傳 302 → 404)。經調查 TWSE OpenAPI (95 個端點) 與第三方套件 twstock 後，
確認目前無免費公開 API 可直接取得「單日單股前五大買賣超券商分點」資料。

## 🎯 開發目標

1. **評估替代資料源**: 測試 twstock SDK 及其他可能方案是否能取得分點買賣超資料
2. **資料源遷移**: 若找到替代方案，修改 BrokerBreakdownSpider 使用新資料源
3. **若無替代方案**: 調整 ChipProfiler/RiskAssessor 以適應無分點資料的情境

## 候選方案

| 方案 | 類型 | 費用 | 可靠度 |
|------|------|------|--------|
| **A. twstock SDK** | Python 套件 (TWSE 包裝) | 免費 | 中 |
| **B. FinMind API** | REST API | 部分付費 | 高 |
| **C. Shioaji (永豐) API** | Python SDK | 需券商帳戶 | 高 |
| **D. Goodinfo 爬蟲** | 網頁爬蟲 | 免費 | 低 |
| **E. CMoney 爬蟲** | 網頁爬蟲 | 免費 | 低 |

## 核心產出

| 產出 | 說明 |
|------|------|
| `docs/agent_context/phase4/02_alternatives_analysis.md` | 替代方案分析報告 |
| `docs/agent_context/phase4/03_implementation_plan.md` | 選定方案後的實作計畫 |
| `tests/test_data_source_*.py` | 各方案 POC 測試腳本 |

## 驗收標準

- [ ] twstock SDK 完整測試，確認有無分點資料
- [ ] 至少測試 2 個替代方案
- [ ] 產出替代方案比較表 (費用、可靠度、實作難度)
- [ ] 選定方案後更新 BrokerBreakdownSpider
- [ ] Phase 3.2 ChipProfiler/RiskAssessor 根據結果調整
