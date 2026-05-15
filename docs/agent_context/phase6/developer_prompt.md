# Developer Prompt — Phase 6: E2E 整合驗證執行

> **目標**: 執行 `run_daily.py` + `run_eod_analysis.py` 完整端到端流程，使用真實資料驗證每一階段
> **依據**: `docs/agent_context/phase6/task_plan.md`
> **預計工時**: 4-6h
> **前置條件**: PostgreSQL 已運行、虛擬環境已啟用

---

## 你的任務

按照以下 6 個 Phase 依序執行，並在 `docs/agent_context/phase6/development_log.md` 中記錄每個階段的結果。

**關鍵原則**:
- 不要修改任何爬蟲、分析邏輯或 DB schema
- 遇到錯誤先記錄，再決定是否繼續
- 所有指令都在 `/home/ubuntu/projects/bcas_quant` 目錄下執行
- PYTHONPATH 需要包含 `src/` 目錄

---

## Phase 0: 前置準備

### 0.1 提交未 commit 的 schema 變更

```bash
git add src/db/init_eod_tables.sql
git commit -m "feat: add source_url/source_type to broker_breakdown"
```

### 0.2 確認 DB schema 已套用

```bash
docker exec bcas-postgres psql -U postgres -d cbas -c "\d broker_breakdown"
```

確認輸出包含 `source_url` 和 `source_type` 欄位。

### 0.3 確認 DB 連線

```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from run_daily import DB_CONFIG
import psycopg2
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute('SELECT table_name FROM information_schema.tables WHERE table_schema=\\'public\\' ORDER BY table_name')
tables = [r[0] for r in cur.fetchall()]
print(f'DB 連線成功，共 {len(tables)} 張表: {tables}')
cur.close()
conn.close()
"
```

### 0.4 確認相依套件

```bash
pip install -r requirements.txt 2>&1 | tail -5
```

---

## Phase A: 逐個爬蟲真實資料測試

逐一執行以下 5 個爬蟲，記錄每個的 success 和 items 數量。

### A.1 StockMasterSpider
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from unittest.mock import Mock
from spiders.stock_master_spider import StockMasterSpider
s = StockMasterSpider(pipeline=Mock())
r = s.fetch_twse()
print(f'StockMaster: success={r.success}, items={len(s.items)}')
assert r.success and len(s.items) > 100
"
```

### A.2 CbMasterSpider
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from unittest.mock import Mock
from spiders.cb_master_spider import CbMasterSpider
s = CbMasterSpider(pipeline=Mock())
r = s.fetch_cb_master()
print(f'CbMaster: success={r.success}, items={len(s.items)}')
"
```

### A.3 StockDailySpider
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from unittest.mock import Mock
from spiders.stock_daily_spider import StockDailySpider
s = StockDailySpider(pipeline=Mock())
r = s.fetch_daily('2330', 2026, 5)
print(f'StockDaily(2330): success={r.success}, items={len(s.items)}')
"
```

### A.4 TpexCbDailySpider
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from unittest.mock import Mock
from datetime import datetime
from spiders.tpex_cb_daily_spider import TpexCbDailySpider
s = TpexCbDailySpider(pipeline=Mock())
today = datetime.now().strftime('%Y-%m-%d')
r = s.fetch_daily(today)
print(f'TpexCbDaily({today}): success={r.success}, items={len(s.items)}')
"
```

### A.5 BrokerBreakdownSpider
```bash
cd /home/ubuntu/projects/bcas_quant
python -c "
import sys; sys.path.insert(0, 'src')
from datetime import datetime
from spiders.broker_breakdown_spider import BrokerBreakdownSpider
s = BrokerBreakdownSpider(pipeline=Mock())
today = datetime.now().strftime('%Y%m%d')
r = s.fetch_broker_breakdown(today, '2330')
print(f'BrokerBreakdown(2330): success={r.success}, items={len(s.get_items())}')
s.close()
"
```

### A.6 驗收表

| 爬蟲 | success | items 數 | 狀態 |
|------|:-------:|:--------:|:----:|
| StockMaster | | | ⬜ |
| CbMaster | | | ⬜ |
| StockDaily | | | ⬜ |
| TpexCbDaily | | | ⬜ |
| BrokerBreakdown | | | ⬜ |

---

## Phase B: run_daily.py 逐步執行

### B.1 --validate-only 模式

```bash
cd /home/ubuntu/projects/bcas_quant
python src/run_daily.py --validate-only 2>&1
```

記錄: 終端輸出摘要、exit code、任何 Exception

### B.2 --force-validation 完整執行

```bash
cd /home/ubuntu/projects/bcas_quant
python src/run_daily.py --force-validation 2>&1
```

驗證 DB 寫入:
```bash
docker exec bcas-postgres psql -U postgres -d cbas -c "
SELECT 'stock_master' as tbl, COUNT(*) FROM stock_master
UNION ALL SELECT 'broker_breakdown', COUNT(*) FROM broker_breakdown
UNION ALL SELECT 'stock_daily', COUNT(*) FROM stock_daily
UNION ALL SELECT 'cb_master', COUNT(*) FROM cb_master
UNION ALL SELECT 'tpex_cb_daily', COUNT(*) FROM tpex_cb_daily
"
```

檢查報表輸出:
```bash
ls -la logs/validation/
ls -la logs/ 2>/dev/null
```

---

## Phase C: run_eod_analysis.py 完整 EOD 流程

### C.1 Stage 1 (爬蟲 + flush)
```bash
cd /home/ubuntu/projects/bcas_quant
python src/run_eod_analysis.py --stage 1 2>&1
```

### C.2 Stage 2 (分析)
```bash
cd /home/ubuntu/projects/bcas_quant
DATE=$(date +%Y-%m-%d)
python src/run_eod_analysis.py --stage 2 --date $DATE 2>&1
```

### C.3 Stage 3 (風險評級)
```bash
cd /home/ubuntu/projects/bcas_quant
DATE=$(date +%Y-%m-%d)
python src/run_eod_analysis.py --stage 3 --date $DATE 2>&1
```

### C.4 Stage 4 (報表)
```bash
cd /home/ubuntu/projects/bcas_quant
DATE=$(date +%Y-%m-%d)
python src/run_eod_analysis.py --stage 4 --date $DATE 2>&1
```

### C.5 完整執行
```bash
cd /home/ubuntu/projects/bcas_quant
DATE=$(date +%Y-%m-%d)
python src/run_eod_analysis.py --date $DATE 2>&1
```

### C.6 驗收表

| Stage | 狀態 | 備註 |
|-------|:----:|------|
| Stage 1: 爬蟲 | ⬜ | |
| Stage 2: 分析 | ⬜ | daily_analysis_results count? |
| Stage 3: 風險 | ⬜ | trading_signals count? |
| Stage 4: 報表 | ⬜ | |

---

## Phase D: 資料驗證與正確性檢查

### D.1 DB 資料完整性

```sql
docker exec -it bcas-postgres psql -U postgres -d cbas -c "
-- broker_breakdown source_type
SELECT source_type, COUNT(*) FROM broker_breakdown GROUP BY source_type;

-- 評級分佈
SELECT final_rating, COUNT(*) FROM daily_analysis_results 
GROUP BY final_rating ORDER BY final_rating;

-- 信號分佈
SELECT signal, COUNT(*) FROM trading_signals GROUP BY signal;

-- 2330 完整資料鏈
SELECT d.symbol, d.date, a.premium_ratio, a.final_rating, t.signal
FROM stock_daily d
LEFT JOIN daily_analysis_results a ON d.symbol = a.symbol
LEFT JOIN trading_signals t ON d.symbol = t.symbol
WHERE d.symbol = '2330' LIMIT 5;
"
```

### D.2 匯總驗收表

| 檢查項 | 結果 | 備註 |
|--------|:----:|------|
| 5 spiders 都成功 | ⬜ | |
| Validation 通過 | ⬜ | |
| DB 寫入正確 | ⬜ | |
| EOD 分析完成 | ⬜ | |
| 評級合理 | ⬜ | |
| 報表產出 | ⬜ | |

---

## Phase E: 問題記錄 + 文件更新

### E.1 更新 development_log.md

在 `docs/agent_context/phase6/development_log.md` 中記錄：
- 執行日期
- 各 Phase 結果摘要
- DB 各表最終 count
- 發現的新問題

### E.2 更新 project_context.md

更新 `docs/project_context.md`：
- Phase 5 狀態改為「✅已完成」
- 新增 Phase 6 條目
- 補充 CSV hotfix 記錄
- 更新測試總數

### E.3 更新 Issue Log

在 `docs/agent_context/phase6/task_plan.md` §6 更新每個 issue 狀態。

---

## 預期產出

1. ✅ `run_daily.py --validate-only` 成功執行
2. ✅ `run_daily.py --force-validation` 成功執行
3. ✅ `run_eod_analysis.py` 各階段成功執行
4. ✅ DB 各表有正確資料
5. ✅ `development_log.md` 更新
6. ✅ `project_context.md` 更新
7. ✅ Issue Log 完整記錄
