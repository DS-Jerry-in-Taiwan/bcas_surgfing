# Developer 每日執行 Prompt（E2E全鏈路整合測試）

**版本**: 1.0  
**建立日期**: 2026-04-16  
**適用對象**: Developer Agent / 開發人員  
**使用頻率**: 每日必讀（工作開始前）

---

## 📋 開發前必讀

### 您的角色
```
您是 E2E全鏈路整合測試專案的開發負責人。
您需要在 6 天內（2026-04-16 ~ 2026-04-19）完成 15 個測試案例的實作、測試、驗收。
```

### 核心指標
| 指標 | 目標值 | 驗收標準 |
|------|--------|---------|
| 測試通過率 | 100% (15/15) | 所有測試必須 PASS |
| 代碼覆蓋率 | >= 80% | 通過 pytest --cov 檢查 |
| 工時預算 | <= 30 小時 | 6 天 × 5 小時/天 |
| 文檔完整度 | 100% | 每日必填進度記錄 |
| 缺陷遺留 | 0 個 | 發現的問題必須全部解決 |

### 禁止事項速查
```
✗ 禁止修改 ETL、資料庫 Schema、主業務流程
✗ 禁止跳過任何測試案例或省略紀錄
✗ 禁止自行定義新測試（須先更新 test_cases.md）
✗ 禁止未經 code review 提交 PR 至主支線
✗ 禁止在主支線進行大規模架構改動
```

---

## 🚀 每日執行流程

### 工作開始前（每天早上）

#### Step 1: 更新進度表 (5分鐘)
```bash
# 開啟進度表，查看今日計劃
vim docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_DAILY_TRACKER.md

# 找到對應日期的章節，例如：
# ### 第 X 天 (YYYY-MM-DD) - [任務名稱]
```

#### Step 2: 確認今日目標 (5分鐘)
```
根據 DEVELOPER_DAILY_TRACKER.md 中的「計劃任務」與「計劃工時」：
- 明確今日要完成什麼
- 預計花多少時間
- 有哪些驗收條件
```

#### Step 3: 準備開發環境 (10分鐘)
```bash
cd /home/ubuntu/projects/bcas_quant

# 驗證環境
python3 -c "import pytest, feapder; print('✓ 環境就緒')"

# 檢查測試框架
pytest tests/test_framework/test_full_system_integration.py --collect-only -q | head -5

# 查看相關檔案
ls -la docs/agent_context/spider_migration_plan/phase_e2e_integration/
```

#### Step 4: 啟動開發 (10分鐘)
```bash
# 根據計劃打開相應的參考檔案
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_QUICK_REFERENCE.md

# 打開實作指南
vim docs/agent_context/spider_migration_plan/phase_e2e_integration/implementation_plan.md

# 打開測試清單對照
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/test_cases.md | grep "E2E-0X"
```

---

## 📅 每日任務清單（逐日模板）

### **第 1 天 (2026-04-16) - 準備與計劃**

#### ✅ 早上任務（2小時）
- [ ] **確認開發環境完全就緒**
  ```bash
  # 檢查 Python 版本
  python3 --version
  
  # 檢查 pytest
  pytest --version
  
  # 檢查 feapder
  python3 -c "import feapder; print(feapder.__version__)"
  
  # 檢查 PostgreSQL
  python3 -c "import psycopg2; conn = psycopg2.connect(...); print('✓ Connected')"
  
  # 驗證測試框架
  pytest tests/test_framework/ --collect-only -q | wc -l
  ```
  
  **驗收檢查**:
  - [ ] Python 版本 >= 3.8
  - [ ] pytest 版本 >= 6.0
  - [ ] feapder 可正常 import
  - [ ] PostgreSQL 連接正常
  - [ ] 測試框架發現 >= 150 個測試

- [ ] **精讀 test_cases.md 確認 15 個測試案例**
  ```bash
  # 查看完整測試清單
  cat docs/agent_context/spider_migration_plan/phase_e2e_integration/test_cases.md
  
  # 統計測試數量
  grep "^| E2E-" docs/agent_context/spider_migration_plan/phase_e2e_integration/test_cases.md | wc -l
  ```
  
  **驗收檢查**:
  - [ ] E2E-01 (5個測試) 理解完整
  - [ ] E2E-02 (4個測試) 理解完整
  - [ ] E2E-03 (3個測試) 理解完整
  - [ ] E2E-04 (3個測試) 理解完整

#### ✅ 下午任務（1.5小時）
- [ ] **複習 implementation_plan.md 技術設計**
  - Mock 策略清晰
  - 流程設計理解
  - 驗收步驟明確

#### 📝 紀錄填寫
```markdown
**2026-04-16 進度記錄**

上午工作:
- [x] 環境驗證完成
  - Python 版本: 3.X.X
  - PostgreSQL 狀態: 已連接
  - 測試發現數: XXX
  
- [x] test_cases.md 確認
  - 完整理解: ✓
  - 問題記錄: 無

下午工作:
- [x] implementation_plan.md 複習
  - Mock 策略清晰度: 清晰
  - 流程理解度: 良好

遇到問題:
- 無

簽核: ____________ (Developer)  日期: 2026-04-16
```

#### ✅ 完成後檢查
- [ ] 環境驗證已簽核
- [ ] 測試清單已理解
- [ ] 技術設計已複習
- [ ] 進度記錄已填寫

---

### **第 2-3 天 (2026-04-17) - 基礎層整合測試實作**

#### ✅ Day 2 上午（4小時）- 實作 E2E-01

- [ ] **E2E-01-01: test_master_then_daily_flow** (1小時)
  ```bash
  # 檢查測試存在
  grep -n "def test_master_then_daily_flow" tests/test_framework/test_full_system_integration.py
  
  # 運行該測試
  pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow::test_master_then_daily_flow -v
  ```
  
  **驗收**:
  - [ ] 測試執行無錯誤
  - [ ] 結果為 PASS ✅
  - [ ] 紀錄時間與問題

- [ ] **E2E-01-02 ~ E2E-01-05** (3小時)
  ```bash
  # 執行完整 E2E-01 測試類
  pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow -v
  ```
  
  **驗收**:
  - [ ] 5 個測試全部 PASS
  - [ ] 覆蓋率檢查通過

#### ✅ Day 2 下午（4小時）- 實作 E2E-02

- [ ] **E2E-02-01 ~ E2E-02-04: TestDeduplicationLogic**
  ```bash
  # 執行完整 E2E-02 測試類
  pytest tests/test_framework/test_full_system_integration.py::TestDeduplicationLogic -v
  ```
  
  **驗收**:
  - [ ] 4 個測試全部 PASS
  - [ ] 去重邏輯驗證完整

#### ✅ Day 3（4小時）- 調整與文檔

- [ ] **修正 Day 2 發現的問題** (2小時)
  - [ ] 性能瓶頸優化
  - [ ] Mock 資料調整
  - [ ] 異常處理完善

- [ ] **更新開發紀錄** (2小時)
  ```bash
  # 更新進度
  vim docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_EXECUTION_GUIDE.md
  
  # Commit 進度
  git add tests/test_framework/test_full_system_integration.py
  git commit -m "feat: E2E-01, E2E-02 測試實作完成 (9/15 通過)"
  ```

#### 📝 Day 2-3 紀錄填寫
```markdown
**2026-04-17 進度記錄**

**Day 2**

上午工作 - E2E-01 實作:
- [x] E2E-01-01 test_master_then_daily_flow
  - 結果: ✅
  - 時間: 50 分鐘
  - 問題: 無

- [x] E2E-01-02 ~ E2E-01-05
  - 結果: 5/5 通過
  - 時間: 180 分鐘
  - 問題: Mock 資料需調整 (已解決)

下午工作 - E2E-02 實作:
- [x] E2E-02-01 ~ E2E-02-04
  - 結果: 4/4 通過
  - 時間: 240 分鐘
  - 問題: 無

**Day 3**
- [x] 問題修正與調整
  - 完成項: Mock 資料調整, 性能優化
  - 時間: 120 分鐘

- [x] 文檔更新
  - DEVELOPER_EXECUTION_GUIDE.md 進度: 100%

累計結果: 9/15 通過

遇到問題:
- [P-001]: Mock 資料格式問題
  - 影響: E2E-01-03 初期失敗
  - 解決: 調整 Mock response 格式
  - 時間: 30 分鐘

簽核: ____________ (Developer)  日期: 2026-04-17
```

---

### **第 4-5 天 (2026-04-18) - 異常回復與多表整合測試**

#### ✅ Day 4（4小時）- E2E-03 異常回復

- [ ] **E2E-03-01: test_network_timeout_retry** (1.5小時)
  ```bash
  pytest tests/test_framework/test_full_system_integration.py::TestErrorRecovery::test_network_timeout_retry -v
  ```
  
- [ ] **E2E-03-02: test_malformed_data_handling** (1小時)
  ```bash
  pytest tests/test_framework/test_full_system_integration.py::TestErrorRecovery::test_malformed_data_handling -v
  ```

- [ ] **E2E-03-03: test_pipeline_failure_rollback** (1.5小時)
  ```bash
  pytest tests/test_framework/test_full_system_integration.py::TestErrorRecovery::test_pipeline_failure_rollback -v
  ```

#### ✅ Day 5（4小時）- E2E-04 多表整合

- [ ] **E2E-04-01: test_stock_dependency_chain** (1.5小時)
- [ ] **E2E-04-02: test_cb_dependency_chain** (1小時)
- [ ] **E2E-04-03: test_cross_table_consistency** (1.5小時)

```bash
# 執行完整 E2E-04 測試類
pytest tests/test_framework/test_full_system_integration.py::TestMultiTableIntegration -v
```

#### 📝 Day 4-5 紀錄填寫
```markdown
**2026-04-18 進度記錄**

**Day 4 - E2E-03 異常回復實作**
- [x] E2E-03-01 network_timeout_retry: ✅ (90分鐘)
- [x] E2E-03-02 malformed_data_handling: ✅ (60分鐘)
- [x] E2E-03-03 pipeline_failure_rollback: ✅ (90分鐘)

**Day 5 - E2E-04 多表整合實作**
- [x] E2E-04-01 stock_dependency_chain: ✅ (90分鐘)
- [x] E2E-04-02 cb_dependency_chain: ✅ (60分鐘)
- [x] E2E-04-03 cross_table_consistency: ✅ (90分鐘)

累計結果: 15/15 通過 ✅

遇到問題:
- 無

簽核: ____________ (Developer)  日期: 2026-04-18
```

---

### **第 6 天 (2026-04-19) - 驗收與結案**

#### ✅ 上午（3小時）- 完整測試執行

- [ ] **執行全部 E2E 測試套件** (2小時)
  ```bash
  # 運行全部測試
  pytest tests/test_framework/test_full_system_integration.py -v --tb=short
  
  # 期望結果: 15/15 PASSED
  ```

- [ ] **檢查代碼覆蓋率** (1小時)
  ```bash
  # 運行覆蓋率檢查
  pytest tests/test_framework/test_full_system_integration.py \
    --cov=src/spiders \
    --cov=src/framework \
    --cov-report=term \
    --cov-report=html
  
  # 期望結果: >= 80% 覆蓋率
  # 詳細報告: htmlcov/index.html
  ```

#### ✅ 下午（3小時）- 結案與簽核

- [ ] **完成 CONCLUSION_REPORT.md** (1.5小時)
  ```bash
  # 編輯結案報告
  vim docs/agent_context/spider_migration_plan/phase_e2e_integration/CONCLUSION_REPORT.md
  
  # 需填寫內容:
  # - 測試結果摘要
  # - 覆蓋率數據
  # - 性能指標
  # - 經驗教訓
  ```

- [ ] **更新 migration_tracker.md** (0.5小時)
  ```bash
  # 標記 E2E 階段為「已完成」
  vim docs/agent_context/spider_migration_plan/migration_tracker.md
  
  # 更新進度至 40%
  ```

- [ ] **代碼 Commit 與簽核** (1小時)
  ```bash
  # 檢查狀態
  git status
  
  # 添加所有變更
  git add tests/test_framework/test_full_system_integration.py
  git add docs/agent_context/spider_migration_plan/phase_e2e_integration/
  git add docs/agent_context/spider_migration_plan/migration_tracker.md
  
  # 提交變更
  git commit -m "feat: E2E全鏈路整合測試完成實作
  
  - 實作全部 15 個測試案例
  - E2E-01 (5個): ✅ 通過
  - E2E-02 (4個): ✅ 通過
  - E2E-03 (3個): ✅ 通過
  - E2E-04 (3個): ✅ 通過
  - 整體通過率: 100% (15/15)
  - 代碼覆蓋率: 85%
  - 工時消耗: 28 小時
  
  詳見 CONCLUSION_REPORT.md"
  
  # 推送到遠程
  git push
  ```

#### 📝 Day 6 結案紀錄
```markdown
**2026-04-19 驗收結案記錄**

**上午 - 完整測試執行**
- [x] 全部 E2E 測試
  - 結果: 15/15 通過 ✅
  - 通過率: 100%
  - 執行時間: 45 秒

- [x] 覆蓋率檢查
  - 框架層: 82%
  - Spiders: 85%
  - Pipeline: 88%
  - 整體: 85%

**下午 - 結案**
- [x] CONCLUSION_REPORT.md 完成
- [x] migration_tracker.md 更新為「已完成」
- [x] Git commit 完成並推送

**最終統計**:
- 總測試數: 15
- 通過數: 15
- 失敗數: 0
- 通過率: 100% ✅
- 開發工時: 28 小時
- 遇到問題數: 2
- 解決成功率: 100%

**經驗教訓**:
1. Mock 資料格式需提前驗證
2. 異常處理測試需充分考慮邊界情況
3. 進度記錄必須每日填寫，方便追蹤

**簽核**:
- Developer: ____________ 日期: 2026-04-19
- Code Reviewer: ____________ 日期: ________
- Project Manager: ____________ 日期: ________

**最終狀態**: ✅ 已完成
```

---

## 🎯 每日告警指標

### 紅綠燈檢查

在每天工作結束時，檢查以下指標：

| 指標 | 綠燈 ✅ | 黃燈 ⚠️ | 紅燈 🔴 | 今日狀態 |
|------|--------|--------|--------|---------|
| 日進度完成度 | >= 90% | 70-89% | < 70% | [ ] |
| 測試通過率 | 100% | 90-99% | < 90% | [ ] |
| 工時消耗 | <= 目標 | 目標+0.5h | > 目標+1h | [ ] |
| 遇到問題數 | 0-1 | 2-3 | >= 4 | [ ] |
| 文檔完整度 | 100% | >= 80% | < 80% | [ ] |

### 若出現黃燈或紅燈

1. **黃燈** ⚠️ : 需要加強關注
   - 明天補救計劃
   - 評估工時影響
   - 通知 PM 知悉

2. **紅燈** 🔴 : 需要立即行動
   - 暫停新任務
   - 集中解決問題
   - 立即回報 PM & 主管
   - 評估是否需要支援

---

## 💾 紀錄填寫要求

### 每日必填項

1. **工作完成情況**
   ```
   [ ] E2E-XX-YY: [結果: ✅/⚠️/❌]
   - 時間: [X 分鐘]
   - 問題: [描述或無]
   ```

2. **遇到的問題**
   ```
   - [P-XXX]: [問題簡述]
     - 影響: [範圍]
     - 解決: [方案]
     - 時間: [X 分鐘]
   ```

3. **每日簽核**
   ```
   簽核: ____________ (Developer)  日期: ________
   ```

### 禁止行為

✗ 不填寫進度記錄  
✗ 口頭匯報（必須書面紀錄）  
✗ 超時仍不更新進度  
✗ 隱瞞遇到的問題  
✗ 未經簽核就合併代碼

---

## 🚀 快速指令速查

### 環境檢查
```bash
# 完整環境驗證
python3 -c "import pytest, feapder, psycopg2; print('✓ All OK')"
```

### 測試執行
```bash
# 運行全部 E2E 測試
pytest tests/test_framework/test_full_system_integration.py -v

# 運行單一測試類
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow -v

# 運行單一測試
pytest tests/test_framework/test_full_system_integration.py::TestFullPipelineFlow::test_master_then_daily_flow -v

# 運行並生成覆蓋率報告
pytest tests/test_framework/test_full_system_integration.py --cov=src --cov-report=html
```

### 進度追蹤
```bash
# 查看本日計劃
cat docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_DAILY_TRACKER.md | grep -A 50 "第 X 天"

# 編輯進度
vim docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_DAILY_TRACKER.md
```

### Git 操作
```bash
# 查看狀態
git status

# 提交進度
git add tests/test_framework/test_full_system_integration.py
git add docs/agent_context/spider_migration_plan/phase_e2e_integration/DEVELOPER_DAILY_TRACKER.md
git commit -m "chore: E2E-XX 進度更新"
git push
```

---

## 📞 遇到問題時的處理流程

### Step 1: 自助排查 (5-10分鐘)
1. 查看 DEVELOPER_QUICK_REFERENCE.md 的 FAQ 章節
2. 查看 implementation_plan.md 的相關設計
3. 查看錯誤訊息與 traceback

### Step 2: 記錄問題 (5分鐘)
```
在 DEVELOPER_DAILY_TRACKER.md 的「遇到問題」欄記錄:
- [P-XXX]: [問題描述]
  - 影響: [影響範圍]
  - 嘗試的解決方案: [列表]
  - 當前狀態: [進行中/待解決]
```

### Step 3: 尋求支援 (視情況)
- **技術問題**: 通知 Code Reviewer
- **進度/工時**: 通知 Project Manager
- **需求澄清**: 通知 Architect Agent

### Step 4: 記錄解決方案
```
一旦問題解決，更新記錄:
- 解決: [最終方案]
- 時間: [X 分鐘]
```

---

## ✅ 完成檢查清單

在標記「完成」前，確認：

- [ ] 今日所有任務已完成
- [ ] 所有測試已運行並記錄結果
- [ ] 進度記錄已詳細填寫
- [ ] 遇到的問題已解決並記錄
- [ ] 代碼已 commit（如有修改）
- [ ] 每日簽核已完成
- [ ] 沒有遺留的 TODO / FIXME 註解
- [ ] 告警指標已檢查（無紅燈）

---

## 💡 最後提醒

### 工作紀律
1. **準時填寫進度** - 每天下班前必須更新 DEVELOPER_DAILY_TRACKER.md
2. **定期 Commit** - 每個測試完成後立即 commit（非日終再提交）
3. **及時回報** - 遇到問題立即記錄，超時需主動通知
4. **質量第一** - 不追求速度，確保每個測試都通過

### 成功關鍵
- ✅ 理解需求 → 參照 test_cases.md
- ✅ 理解設計 → 參照 implementation_plan.md
- ✅ 保持進度 → 每日填寫 DEVELOPER_DAILY_TRACKER.md
- ✅ 及時溝通 → 問題記錄 + 定期更新

---

**開始工作前，請確保已完成「開發前必讀」章節的所有準備！** 🚀

*此 Prompt 供 Developer 每日參考。祝工作順利！*

---

*版本: 1.0 | 建立: 2026-04-16 | 最後更新: 2026-04-16*