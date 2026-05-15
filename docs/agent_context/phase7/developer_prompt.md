# Developer Prompt — Phase 7: 分析鏈修復

## 任務

修復 DataCleaner (GAP-02)，新增 enrich_cb_master (GAP-01)，並用 2026-05-14 歷史資料驗證完整分析鏈。

---

## Step 1: 修 DataCleaner (GAP-02)

### 1.1 先在 DB 補 `master_check` 欄位

```bash
docker exec bcas-postgres psql -U postgres -d cbas -c "
ALTER TABLE stock_daily ADD COLUMN IF NOT EXISTS master_check VARCHAR(32) DEFAULT '';
ALTER TABLE tpex_cb_daily ADD COLUMN IF NOT EXISTS master_check VARCHAR(32) DEFAULT '';
"
```

### 1.2 測試 DataCleaner 可正常執行

```bash
cd /home/ubuntu/projects/bcas_quant && python -c "
import sys; sys.path.insert(0, 'src')
from etl.run_cleaner import DataCleaner
from run_daily import DB_CONFIG
c = DataCleaner(DB_CONFIG)
r = c.run_all()
print(r)
c.close()
"
```

---

## Step 2: 加 `enrich_cb_master()` (GAP-01)

### 2.1 修改 `src/etl/run_cleaner.py`

在 DataCleaner 類別中新增方法：

```python
def enrich_cb_master(self) -> dict:
    """從 cb_code 前4碼推導 underlying_stock（標的股票代號）

    cb_code 格式: SSSSI (前4碼=股票代號, 末碼=發行序號)
    例如: 11011 → 1101 (台泥)
    """
    self.cur.execute("""
        UPDATE cb_master c
        SET underlying_stock = m.symbol
        FROM stock_master m
        WHERE m.symbol = SUBSTRING(c.cb_code, 1, 4)
          AND (c.underlying_stock IS NULL OR c.underlying_stock = '')
    """)
    matched = self.cur.rowcount
    self.conn.commit()

    # 紀錄沒對到的
    self.cur.execute("""
        SELECT cb_code, cb_name FROM cb_master
        WHERE underlying_stock IS NULL OR underlying_stock = ''
        LIMIT 10
    """)
    unmatched = [f"{r[0]} ({r[1]})" for r in self.cur.fetchall()]

    return {
        "cb_master_total_matched": matched,
        "cb_master_unmatched_samples": unmatched,
    }
```

然後在 `run_all()` 中呼叫它：

```python
def run_all(self) -> dict:
    start = datetime.now()
    result = {
        "start_time": start.isoformat(),
        "stock_daily": self.validate_stock_daily(),
        "tpex_cb_daily": self.validate_cb_daily(),
        "cb_master_enrich": self.enrich_cb_master(),  # ← 加這行
    }
    ...
```

### 2.2 測試 enrichment

```bash
cd /home/ubuntu/projects/bcas_quant && python -c "
import sys; sys.path.insert(0, 'src')
from etl.run_cleaner import DataCleaner
from run_daily import DB_CONFIG
c = DataCleaner(DB_CONFIG)
r = c.run_all()
print('=== Enrichment result ===')
print(f'matched: {r[\"cb_master_enrich\"][\"cb_master_total_matched\"]}')
print(f'unmatched samples: {r[\"cb_master_enrich\"][\"cb_master_unmatched_samples\"]}')
c.close()
"
```

### 2.3 確認 DB 已填入

```bash
docker exec bcas-postgres psql -U postgres -d cbas -c "
SELECT underlying_stock, COUNT(*) FROM cb_master GROUP BY underlying_stock ORDER BY underlying_stock;
"
```

---

## Step 3: E2E 驗證完整分析鏈

### 3.1 準備 DB 資料

```bash
cd /home/ubuntu/projects/bcas_quant && python3 << 'PYEOF'
import sys; sys.path.insert(0, 'src')
import psycopg2
from unittest.mock import Mock
from run_daily import DB_CONFIG
from framework.pipelines import PostgresPipeline

# 清除舊資料
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()
for t in ['daily_analysis_results', 'trading_signals']:
    cur.execute(f'DELETE FROM {t}')
conn.commit()
cur.close()

# cb_master 和 tpex_cb_daily 用 2026-05-14 的資料
# (若已存在則跳過)

# stock_daily: 需要將 2330 的收盤價補進去（因為 PremiumCalculator 需要查股價）
# 先用今日資料
from spiders.stock_daily_spider import StockDailySpider
p = PostgresPipeline(table_name='stock_daily', batch_size=500, **DB_CONFIG)
s = StockDailySpider(pipeline=p)
r = s.fetch_daily('2330', 2026, 5)
if s.items: s.flush_items(p)
p.close()

conn.close()
print('DB data prepared')
PYEOF
```

### 3.2 跑完整 EOD 分析鏈

```bash
cd /home/ubuntu/projects/bcas_quant && python3 << 'PYEOF'
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, '.')

from analytics.premium_calculator import PremiumCalculator
from analytics.technical_analyzer import TechnicalAnalyzer
from analytics.risk_assessor import RiskAssessor

DATE = '2026-05-14'
print(f'=== EOD Analytics Chain: {DATE} ===')

# Stage 2
pc = PremiumCalculator()
results = pc.analyze(DATE)
print(f'PremiumCalculator: {len(results)} 筆')
if results:
    pc.save_results(DATE, results)
    # 顯示樣本 + 評級分佈
    ratings = {}
    for r in results:
        ratings[r.final_rating] = ratings.get(r.final_rating, 0) + 1
    print(f'  Distribution: {ratings}')
    for r in results[:3]:
        print(f'  {r.symbol}: premium={r.premium_ratio:.4f}')
else:
    print('  ❌ No results - needs debugging')

# TechnicalAnalyzer
ta = TechnicalAnalyzer()
results2 = ta.analyze(DATE, results)
print(f'\nTechnicalAnalyzer: {len(results2)} 筆')

# Stage 3
ra = RiskAssessor()
results3 = ra.run_analysis(DATE)
print(f'\nRiskAssessor: {len(results3)} 筆')
if results3:
    ratings = {}
    for r in results3:
        ratings[r.final_rating] = ratings.get(r.final_rating, 0) + 1
    print(f'  Rating distribution: {ratings}')
    for r in results3[:5]:
        print(f'  {r.symbol}: rating={r.final_rating} signal={r.signal}')
PYEOF
```

### 3.3 用 EOD Pipeline 完整跑一次

```bash
cd /home/ubuntu/projects/bcas_quant
python src/run_eod_analysis.py --date 2026-05-14 2>&1
```

### 3.4 確認終端報表有內容

報表應產出 S/A/B/C 分組的 CBAS 次日交易戰略清單。

---

## Step 4: 驗證 DB 結果

```bash
docker exec bcas-postgres psql -U postgres -d cbas -c "
SELECT final_rating, COUNT(*) FROM daily_analysis_results GROUP BY final_rating ORDER BY final_rating;
"
docker exec bcas-postgres psql -U postgres -d cbas -c "
SELECT signal, COUNT(*) FROM trading_signals GROUP BY signal;
"
```

---

## 預期產出

1. ✅ DataCleaner 可正常執行 (step_clean)
2. ✅ `cb_master.underlying_stock` 已填入 (matched + unmatched 記錄)
3. ✅ PremiumCalculator 產出 > 0 筆結果
4. ✅ RiskAssessor 產出 S/A/B/C 評級
5. ✅ EOD Pipeline 完整流程產出有內容的報表
6. ✅ 295 單元測試零回歸
