# E2E 全鏈路整合測試 - Developer 快速參考卡

**版本**: 1.0 | **建立**: 2026-04-16 | **責任人**: Developer Agent

---

## 📋 核心文件一覽表

| 用途 | 檔案名稱 | 重點內容 |
|------|---------|---------|
| **目標澄清** | `README.md` | 測試目標、情境流程、環境依賴 |
| **技術設計** | `implementation_plan.md` | Mock策略、流程設計、驗收步驟 |
| **測試清單** | `test_cases.md` | 15個測試案例及預期結果 (E2E-01~04) |
| **工作規範** | `DEVELOPER_PROMPT.md` | 職責邊界、禁止事項、完成定義 |
| **執行指南** | `DEVELOPER_EXECUTION_GUIDE.md` | 6天開發流程、日誌模板 |
| **進度追蹤** | `DEVELOPER_DAILY_TRACKER.md` | 每日進度表、告警設置 |
| **結案報告** | `CONCLUSION_REPORT.md` | 測試結果、經驗教訓、簽核 |

---

## 🎯 測試指標與目標

### 測試覆蓋清單
```
E2E-01: TestFullPipelineFlow (P0)
  ├─ E2E-01-01: test_master_then_daily_flow
  ├─ E2E-01-02: test_cb_master_then_daily_flow
  ├─ E2E-01-03: test_empty_symbol_list
  ├─ E2E-01-04: test_statistics_aggregation
  └─ E2E-01-05: test_pipeline_close_integrity

E2E-02: TestDeduplicationLogic (P0)
  ├─ E2E-02-01: test_duplicate_stock_daily
  ├─ E2E-02-02: test_duplicate_cb_daily
  ├─ E2E-02-03: test_updated_at_changes
  └─ E2E-02-04: test_different_dates_no_dedup

E2E-03: TestErrorRecovery (P1)
  ├─ E2E-03-01: test_network_timeout_retry
  ├─ E2E-03-02: test_malformed_data_handling
  └─ E2E-03-03: test_pipeline_failure_rollback

E2E-04: TestMultiTableIntegration (P1)
  ├─ E2E-04-01: test_stock_dependency_chain
  ├─ E2E-04-02: test_cb_dependency_chain
  └─ E2E-04-03: test_cross_table_consistency
```

### 驗收指標
| 指標 | 目標 | 說明 |
|------|------|------|
| 測試通過率 | 100% (15/15) | 所有測試案例必須通過 |
| 覆蓋率 | >= 80% | 代碼覆蓋率檢查 |
| 工時預算 | <= 30 小時 | 6天完成 (每天5小時) |
| 文檔完整 | 100% | 所有紀錄詳細簽核 |
| 無遺留缺陷 | 0 | 發現的問題必須全部解決 |

---

## 🚀 快速開始（Day 1）

### 第一步：環境檢查 (30分鐘)
```bash
cd /home/ubuntu/projects/bcas_quant

# 1. 檢查環境
python3 -c "import pytest; import feapder; print('✓ 依賴就緒')"

# 2. 檢查測試框架
pytest tests/test_framework/ --collect-only -q | wc -l

# 3. 驗證資料庫
python3 -c "import psycopg2; conn = psycopg2.connect(...); print('✓ DB連接')"
```

### 第二步：閱讀核心文件 (1.5小時)
```bash
# 依序閱讀這 4 個檔案
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/README.md
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/test_cases.md
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/implementation_plan.md
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_PROMPT.md
```

### 第三步：制定計劃 (1.5小時)
1. 將 `DEVELOPER_DAILY_TRACKER.md` 第 1 天記錄 Day 1 工作計劃
2. 確認 15 個測試案例的理解無誤
3. 預估每個測試的工時與依賴關係

### 第四步：記錄簽核 (30分鐘)
在 `DEVELOPER_DAILY_TRACKER.md` 簽核 Day 1 完成

---

## 💻 核心命令速查

### 查看文件
```bash
# 查看測試清單
grep "^| E2E-" docs/agent_context/spider_migration_plan/phase_e2e_integration/test_cases.md

# 查看測試代碼
cat tests/test_framework/test_full_system_integration.py
```

### 執行測試
```bash
# 執行全部測試
pytest tests/test_framework/test_full_system_integration.py -v

# 執行單一測試類
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow -v

# 執行單一測試方法
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow::test_master_then_daily_flow -v

# 執行並顯示覆蓋率
pytest tests/test_framework/test_full_system_integration.py --cov=src --cov-report=term

# 執行並生成 HTML 覆蓋率報告
pytest tests/test_framework/test_full_system_integration.py --cov=src --cov-report=html
# 開啟: htmlcov/index.html
```

### 更新進度
```bash
# 更新日進度
vim docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_DAILY_TRACKER.md

# Commit 開發成果
git add tests/test_framework/test_full_system_integration.py
git add docs/agent_context/spider_migration_plan/phase_e2e_integration/
git commit -m "feat: E2E [具體內容]"
git push
```

---

## ⚠️ 禁止事項速查

✗ **禁止直接**修改 ETL、資料庫 Schema、主業務流程  
✗ **禁止跳過**任何測試案例或省略紀錄  
✗ **禁止自行定義**新的測試場景（須先更新 test_cases.md）  
✗ **禁止未經** code review 提交 PR 至主支線  
✗ **禁止**在主支線上進行大規模架構改動

---

## 📊 進度儀表板

### 預計進度表
| 天次 | 日期 | 任務 | 測試 | 目標 | 進度 |
|------|------|------|------|------|------|
| D1 | 2026-04-16 | 準備、計劃 | - | 環境就緒 | [%] |
| D2-3 | 2026-04-17 | E2E-01, E2E-02 | 9/15 | 基礎通過 | [%] |
| D4-5 | 2026-04-18 | E2E-03, E2E-04 | 15/15 | 全部通過 | [%] |
| D6 | 2026-04-19 | 驗收、結案 | 15/15 | 100% | [%] |

### 紅綠燈指標
| 狀態 | 含義 | 條件 |
|------|------|------|
| 🟢 GREEN | 按計劃推進 | 完成度 >= 90% |
| 🟡 YELLOW | 需要注意 | 完成度 70-89% |
| 🔴 RED | 需要幫助 | 完成度 < 70% |

---

## 💡 常見問題與解決

### Q1: 測試失敗，應該怎麼做？
**A**: 
1. 查看錯誤訊息與 traceback
2. 參照 `implementation_plan.md` 中的 Mock 策略
3. 檢查是否遺漏了前置條件（如資料庫隔離、Mock 設置）
4. 若無法自行解決，在 `DEVELOPER_DAILY_TRACKER.md` 記錄問題，尋求支援

### Q2: 如何驗證我的實作完整性？
**A**:
1. 執行 `pytest tests/test_framework/test_full_system_integration.py -v`
2. 檢查覆蓋率 >= 80%
3. 對比 `test_cases.md` 確保所有 15 個測試都有實作
4. 在 `DEVELOPER_DAILY_TRACKER.md` 記錄驗收結果

### Q3: 發現上游代碼有缺陷，應該怎麼辦？
**A**:
1. **不要直接修改**上游代碼
2. 在 GitHub 開啟 Issue，詳細描述問題
3. 在 `DEVELOPER_DAILY_TRACKER.md` 記錄此阻礙
4. 通知 Project Manager，尋求優先級調整

### Q4: 工時超預算，應該怎麼做？
**A**:
1. 立即通知 Project Manager
2. 識別是哪個測試導致延誤
3. 評估是否需要調整計劃或尋求支援
4. 記錄於 `DEVELOPER_DAILY_TRACKER.md` 風險欄

---

## 📞 支援聯絡

| 問題類型 | 聯絡人 | 方式 |
|---------|--------|------|
| 技術問題 | Code Reviewer | Slack / 面對面 |
| 進度/工時 | Project Manager | 每日站會 / Slack |
| 需求澄清 | Architect Agent | GitHub Issue / 會議 |
| 環境問題 | DevOps Team | Slack / 工單 |

---

## 📝 關鍵完成定義檢查清單

完成本階段前，確認以下**所有項目**均已完成：

- [ ] 所有 15 個 E2E 測試案例 100% 通過
- [ ] 代碼覆蓋率 >= 80%
- [ ] 所有開發日誌已詳細記錄
- [ ] `CONCLUSION_REPORT.md` 已填寫完整
- [ ] 所有遇到的問題都已記錄與解決
- [ ] PR 已通過 code review
- [ ] `migration_tracker.md` 已更新為「已完成」
- [ ] 未有任何 TODO / FIXME 註解遺留
- [ ] Developer、Reviewer、PM 三方簽核完成

---

## 🎓 進階參考

- **進階調試**: 執行 `pytest -vvv` 查看詳細 trace
- **性能分析**: 執行 `pytest --durations=10` 找出最慢的測試
- **覆蓋率詳情**: 開啟 `htmlcov/index.html` 查看逐行覆蓋

---

**祝開發順利！有任何問題隨時詢問。** 🚀

---

*此卡由 Architect Agent 建立供 Developer 快速參考。*  
*版本: 1.0 | 最後更新: 2026-04-16*