# E2E 全鏈路整合測試 - Developer 執行指南

**版本**: 1.0  
**建立日期**: 2026-04-16  
**最後更新**: 2026-04-16  
**責任人**: Developer Agent  
**狀態**: 🔄 進行中

---

## 執行前準備清單

在開始開發前，請確保已完成以下檢查：

- [ ] 已閱讀 `README.md` 了解測試目標與全體情境
- [ ] 已閱讀 `implementation_plan.md` 理解技術設計與 Mock 策略
- [ ] 已閱讀 `test_cases.md`，掌握所有 15 個細節測試案例
- [ ] 已閱讀 `DEVELOPER_PROMPT.md`，理解工作流程與任務邊界
- [ ] 已確認 `tests/test_framework/test_full_system_integration.py` 存在
- [ ] 已配置本地開發環境（PostgreSQL running, .env 設置）
- [ ] 已執行 `pytest tests/test_framework/test_full_system_integration.py --collect-only` 確認測試發現

---

## 開發執行流程

### 1. 環境與前置條件驗證 (Day 1 - 2小時)

**任務**: 確認開發環境完全就緒

```bash
# 進入專案
cd /home/ubuntu/projects/bcas_quant

# 檢查環境
python3 -c "import pytest; print(f'pytest: {pytest.__version__}')"
python3 -c "import feapder; print(f'feapder: {feapder.__version__}')"
python3 -c "import psycopg2; print('PostgreSQL driver OK')"

# 驗證測試框架
pytest tests/test_framework/ -v --co -q | wc -l

# 啟動 PostgreSQL（若未啟動）
# systemctl start postgresql 或 docker-compose up -d postgres

# 驗證數據庫連接
python3 -c "import psycopg2; conn = psycopg2.connect(dsn='...'); print('DB Connected')"
```

**驗收條件**:
- [x] 所有依賴包可正常 import
- [x] PostgreSQL 服務正常運行
- [x] pytest 可發現至少 150+ 個測試案例

**紀錄**: 在下方補充您的驗證結果

```markdown
**環境驗證報告** (2026-04-16)
- Python 版本: [填寫版本]
- pytest 版本: [填寫版本]
- feapder 版本: [填寫版本]
- PostgreSQL 版本: [填寫版本]
- 測試發現數: [填寫數字]
- 環境就緒時間: [填寫時間點]
```

---

### 2. 測試案例解讀與計畫設定 (Day 1 - 3小時)

**任務**: 精讀 test_cases.md，逐項確認測試覆蓋計畫

| 測試類別 | 測試ID | 測試數 | 優先級 | 預計完成日期 | 狀態 |
|---------|--------|-------|--------|------------|------|
| TestFullPipelineFlow | E2E-01 | 5 | P0 | 2026-04-17 | ⏳ |
| TestDeduplicationLogic | E2E-02 | 4 | P0 | 2026-04-17 | ⏳ |
| TestErrorRecovery | E2E-03 | 3 | P1 | 2026-04-18 | ⏳ |
| TestMultiTableIntegration | E2E-04 | 3 | P1 | 2026-04-18 | ⏳ |
| **合計** | - | **15** | - | - | - |

**預期測試覆蓋**:
- 框架層 (Phase 1): ~55 個測試
- 主檔層 (Phase 2): ~37 個測試
- 日行情層 (Phase 3): ~40 個測試
- E2E 整合層: ~15 個測試 (本任務範圍)
- **總計**: ~147 個測試, **目標通過率**: 100%

**紀錄**:

```markdown
**測試計畫確認** (2026-04-16)
- 完整理解測試需求: ✓ / ✗
- 已簽署測試計畫表: ✓ / ✗
- 預計工作量: [填寫小時數]
- 團隊技能評估: [評語]
```

---

### 3. 技術實現 - Phase 1, 2, 3 基礎整合測試 (Day 2-3 - 12小時)

**任務**: 實作 TestFullPipelineFlow (E2E-01) 與 TestDeduplicationLogic (E2E-02)

#### Step 3.1: 複習 implementation_plan.md 中的 Mock 策略與流程設計

- Mock HTTP 回應（stock_master, cb_master, stock_daily）
- Pipeline Mock（去重邏輯、資料庫寫入）
- 統計計算與驗證邏輯

#### Step 3.2: 開發 test_full_system_integration.py

**檔案位置**: `tests/test_framework/test_full_system_integration.py`

**期望結構**:

```python
class TestFullPipelineFlow:
    """E2E-01: 全流程整合測試"""
    
    def setup_method(self):
        """測試前準備"""
        # 1. 建立 Mock Pipeline
        # 2. Mock HTTP responses
        # 3. 設置測試資料庫隔離
        pass
    
    def test_master_then_daily_flow(self):
        """E2E-01-01: 股票主檔 + 日行情完整流程"""
        # 實現: 見 implementation_plan.md Task 2
        pass
    
    # ... 其他 4 個測試方法

class TestDeduplicationLogic:
    """E2E-02: 去重邏輯驗證"""
    
    def test_duplicate_stock_daily(self):
        """E2E-02-01: 相同 symbol_date 二次寫入去重驗證"""
        pass
    
    # ... 其他 3 個測試方法
```

**驗收條件**:
- [x] 所有 E2E-01 與 E2E-02 的測試通過
- [x] 覆蓋率 >= 80%
- [x] 無未捕捉異常

**執行驗證**:

```bash
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow -v
pytest tests/test_framework/test_full_system_integration.py::TestDeduplicationLogic -v

# 檢查覆蓋率
pytest tests/test_framework/test_full_system_integration.py --cov=src/spiders --cov-report=term
```

**紀錄**: (逐日更新此處)

```markdown
**Phase 1-2-3 基礎整合測試開發進度**

**Day 2 (2026-04-17)**
- 任務: 實作 TestFullPipelineFlow (E2E-01)
- 開發時間: [起始時間] - [結束時間]
- 完成項目: [E2E-01-01, E2E-01-02, ...]
- 遇到問題: [詳細描述]
- 解決方案: [實施細節]
- 測試結果: [通過/失敗] (X/5)

**Day 3 (2026-04-17)**
- 任務: 實作 TestDeduplicationLogic (E2E-02)
- 開發時間: [起始時間] - [結束時間]
- 完成項目: [E2E-02-01, E2E-02-02, ...]
- 遇到問題: [詳細描述]
- 解決方案: [實施細節]
- 測試結果: [通過/失敗] (X/4)
```

---

### 4. 技術實現 - 異常回復與多表整合測試 (Day 4-5 - 8小時)

**任務**: 實作 TestErrorRecovery (E2E-03) 與 TestMultiTableIntegration (E2E-04)

#### Step 4.1: TestErrorRecovery (E2E-03)

**測試場景**:
- 網路超時、重試機制
- 資料格式異常、容錯邏輯
- Pipeline 異常、回滾策略

```python
class TestErrorRecovery:
    """E2E-03: 異常回復能力驗證"""
    
    def test_network_timeout_retry(self):
        """E2E-03-01: 網路超時自動重試"""
        pass
    
    def test_malformed_data_handling(self):
        """E2E-03-02: 格式錯誤容錯"""
        pass
    
    def test_pipeline_failure_rollback(self):
        """E2E-03-03: Pipeline 異常回滾"""
        pass
```

**驗收條件**:
- [x] 所有 E2E-03 測試通過
- [x] 重試邏輯正常運作
- [x] 異常記錄正確完整

#### Step 4.2: TestMultiTableIntegration (E2E-04)

**測試場景**:
- 多表資料一致性 (stock_master → stock_daily)
- CB主檔 → CB日行情 完整流程
- 交叉參照完整性驗證

```python
class TestMultiTableIntegration:
    """E2E-04: 多表資料整合驗證"""
    
    def test_stock_dependency_chain(self):
        """E2E-04-01: stock_master → stock_daily 依賴鏈完整"""
        pass
    
    def test_cb_dependency_chain(self):
        """E2E-04-02: cb_master → cb_daily 依賴鏈完整"""
        pass
    
    def test_cross_table_consistency(self):
        """E2E-04-03: 跨表資料一致性驗證"""
        pass
```

**驗收條件**:
- [x] 所有 E2E-04 測試通過
- [x] 資料依賴關係驗證無誤
- [x] 跨表一致性檢查完成

**執行驗證**:

```bash
pytest tests/test_framework/test_full_system_integration.py::TestErrorRecovery -v
pytest tests/test_framework/test_full_system_integration.py::TestMultiTableIntegration -v

# 完整測試
pytest tests/test_framework/test_full_system_integration.py -v --tb=short
```

**紀錄**:

```markdown
**異常回復 & 多表整合測試開發進度**

**Day 4 (2026-04-18)**
- 任務: 實作 TestErrorRecovery (E2E-03)
- 開發時間: [起始] - [結束]
- 完成項目: [E2E-03-01, E2E-03-02, E2E-03-03]
- 遇到問題: [描述]
- 解決方案: [詳細]
- 測試結果: [通過/失敗] (X/3)

**Day 5 (2026-04-18)**
- 任務: 實作 TestMultiTableIntegration (E2E-04)
- 開發時間: [起始] - [結束]
- 完成項目: [E2E-04-01, E2E-04-02, E2E-04-03]
- 遇到問題: [描述]
- 解決方案: [詳細]
- 測試結果: [通過/失敗] (X/3)
```

---

### 5. 完整測試執行與驗收 (Day 6 - 4小時)

**任務**: 執行全部測試，確保 100% 通過率與完整覆蓋

```bash
# 執行完整 E2E 測試套件
pytest tests/test_framework/test_full_system_integration.py -v --tb=short

# 統計覆蓋率
pytest tests/test_framework/test_full_system_integration.py \
  --cov=src/spiders \
  --cov=src/framework \
  --cov-report=html \
  --cov-report=term

# 檢查報告
# 覆蓋率報告: htmlcov/index.html

# 性能基線測試
pytest tests/test_framework/test_full_system_integration.py -v --durations=10
```

**驗收檢查清單**:

| 檢查項目 | 標準 | 結果 | 簽核 |
|---------|------|------|------|
| 全部測試通過 | 100% | [ ] | [ ] |
| 代碼覆蓋率 | >= 80% | [ ] | [ ] |
| 性能基線 | 無回歸 | [ ] | [ ] |
| 異常處理 | 完整 | [ ] | [ ] |
| 紀錄完整 | 是 | [ ] | [ ] |

**紀錄**:

```markdown
**完整測試驗收報告** (2026-04-19)

**測試執行結果**:
- 總測試數: [填寫]
- 通過數: [填寫]
- 失敗數: [填寫]
- 通過率: [填寫] %
- 執行時間: [填寫] s

**覆蓋率分析**:
- 框架層覆蓋率: [填寫] %
- Spiders 覆蓋率: [填寫] %
- Pipeline 覆蓋率: [填寫] %
- 整體覆蓋率: [填寫] %

**性能基線**:
- 平均執行時間: [填寫] s
- 最慢測試: [填寫名稱], [填寫時間] s
- 異常: [填寫]

**結論**: [填寫結論]
```

---

### 6. 開發紀錄與驗收總結 (Day 6 - 2小時)

**任務**: 更新 CONCLUSION_REPORT.md 與開發日誌

**必須包含**:

1. **開發時間線**
   - 每日任務完成情況
   - 遇到的問題與解決時間
   - 決策與調整記錄

2. **測試結果摘要**
   - 所有 15 個測試案例的通過情況
   - 覆蓋率數據
   - 性能指標

3. **經驗教訓**
   - 在開發過程中發現的問題
   - 改進建議
   - 未來可優化的地方

4. **簽核與核准**
   - Developer 簽名與日期
   - Code Reviewer 簽名與日期
   - Project Manager 簽名與日期

**執行指令**:

```bash
# 更新 CONCLUSION_REPORT.md
vim docs/agent_context/spider_migration_plan/phase_e2e_integration/CONCLUSION_REPORT.md

# Commit 開發紀錄
git add docs/agent_context/spider_migration_plan/phase_e2e_integration/
git commit -m "feat: E2E全鏈路整合測試完成實作

- 實作 TestFullPipelineFlow (E2E-01): 5/5 測試通過
- 實作 TestDeduplicationLogic (E2E-02): 4/4 測試通過
- 實作 TestErrorRecovery (E2E-03): 3/3 測試通過
- 實作 TestMultiTableIntegration (E2E-04): 3/3 測試通過
- 整體通過率: 100% (15/15)
- 代碼覆蓋率: 85%

[詳見 CONCLUSION_REPORT.md]"
```

---

## 開發中遇到的問題與解決方案

**模板**: 遇到問題時請記錄於此

| 問題ID | 日期 | 問題描述 | 影響範圍 | 解決方案 | 解決時間 | 狀態 |
|--------|------|---------|---------|---------|---------|------|
| [P-001] | [日期] | [描述] | [範圍] | [方案] | [時間] | ✅ |

---

## 禁止事項檢查

- [ ] **禁止**: 直接修改 ETL/資料庫 schema（若發現問題須提 Issue）
- [ ] **禁止**: 跳過任何測試案例或自行簡化需求
- [ ] **禁止**: 省略任何開發紀錄或口頭驗收
- [ ] **禁止**: 在未經 code review 前提交 PR 至主支線
- [ ] **禁止**: 衍生新的測試場景而不更新 test_cases.md

---

## 任務完成標準 (Definition of Done)

在標記此任務為「完成」前，請確認以下所有項目已滿足：

- [ ] 所有 15 個 E2E 測試案例 100% 通過
- [ ] 代碼覆蓋率 >= 80%
- [ ] 所有測試紀錄詳細完整
- [ ] CONCLUSION_REPORT.md 已填寫並簽核
- [ ] 開發日誌中所有問題已記錄與解決
- [ ] PR 已通過 code review
- [ ] migration_tracker.md 已更新進度
- [ ] 無遺留的 TODO 或 FIXME 註解

---

## 快速參考

### 常用指令

```bash
# 進入專案與測試目錄
cd /home/ubuntu/projects/bcas_quant
cd docs/agent_context/spider_migration_plan/phase_e2e_integration

# 查看參考文件
cat README.md                 # 測試目標
cat implementation_plan.md    # 技術設計
cat test_cases.md             # 測試清單
cat DEVELOPER_PROMPT.md       # 工作規範

# 執行測試
pytest tests/test_framework/test_full_system_integration.py -v
pytest tests/test_framework/test_full_system_integration.py -v --cov

# Git 操作
git status
git add [files]
git commit -m "message"
git push origin [branch]

# 查看進度
cat CONCLUSION_REPORT.md
```

### 關鍵檔案快速查詢

| 用途 | 檔案路徑 |
|------|---------|
| 測試目標 | `README.md` |
| 技術設計 | `implementation_plan.md` |
| 測試清單 | `test_cases.md` |
| 工作規範 | `DEVELOPER_PROMPT.md` |
| 測試代碼 | `tests/test_framework/test_full_system_integration.py` |
| 進度紀錄 | `CONCLUSION_REPORT.md` |
| 所有階段進度 | `../migration_tracker.md` |

---

## 開發指導與支援

- **若遇到技術問題**: 參照 `DEVELOPER_PROMPT.md` 中的「實作任務」章節
- **若需理解需求**: 詳讀 `README.md` 與 `test_cases.md`
- **若需調整計畫**: 與 Project Manager 溝通，記錄於此文件並更新 `test_cases.md`
- **若發現上游缺陷**: 提出 GitHub Issue，抄送主責人，勿直接修正

---

**祝順利！🚀**

---

*此文件由 Architect Agent 創建，供 Developer 參考與執行。*  
*最後更新: 2026-04-16 | 版本: 1.0*