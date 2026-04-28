#!/usr/bin/env python3
"""
整合測試：驗證爬蟲 + 清洗全流程

流程：
1. 清空 DB
2. 抓取 2026/01 ~ 2026/04 的資料
3. 清洗（master_check + 併表）
4. 輸出報告 + 驗證結果

用法:
  python3 scripts/run_integration_test.py
"""
import sys, os, json, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import psycopg2
from framework.pipelines import PostgresPipeline
from spiders.stock_master_spider import StockMasterSpider
from spiders.cb_master_spider import CbMasterSpider
from spiders.stock_daily_spider import StockDailySpider
from spiders.tpex_cb_daily_spider import TpexCbDailySpider
from etl.run_cleaner import DataCleaner

DB = dict(host='localhost', port=5432, database='cbas', user='postgres', password='postgres')
START = "2026-01-01"
END = "2026-04-28"


def step_clear():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    for t in ['stock_master', 'cb_master', 'stock_daily', 'tpex_cb_daily']:
        cur.execute(f'TRUNCATE {t} CASCADE')
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS master_check TEXT')
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS name TEXT')
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS industry TEXT')
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS cb_name_enriched TEXT')
        cur.execute(f'ALTER TABLE {t} ADD COLUMN IF NOT EXISTS conversion_price_enriched TEXT')
    conn.commit()
    cur.close()
    conn.close()
    print("✅ DB 已清空\n")


def step_spiders():
    results = {}

    p = PostgresPipeline(table_name='stock_master', batch_size=500, **DB)
    s = StockMasterSpider(pipeline=p)
    r = s.fetch_twse()
    s.close()
    results['stock_master'] = r.data.get('count', 0)
    print(f'  ✅ StockMaster: {results["stock_master"]} 筆')
    time.sleep(1)

    cb_total = 0
    for date in ['20260115', '20260205', '20260305', '20260401', '20260428']:
        p = PostgresPipeline(table_name='cb_master', batch_size=500, **DB)
        s = CbMasterSpider(pipeline=p)
        r = s.fetch_cb_master(date)
        s.close()
        cnt = r.data.get('count', 0) if r.data else 0
        cb_total += cnt
        print(f'  ✅ CbMaster ({date}): {cnt} 筆')
        time.sleep(0.5)
    results['cb_master'] = cb_total

    p = PostgresPipeline(table_name='stock_daily', batch_size=500, **DB)
    s = StockDailySpider(pipeline=p)
    total_sd = 0
    for sym in ['2330', '2317', '2454']:
        r = s.fetch_date_range(sym, START, END)
        c = r.get('total_items', 0)
        total_sd += c
        print(f'  ✅ StockDaily {sym}: {c} 筆')
    s.close()
    results['stock_daily'] = total_sd
    time.sleep(1)

    p = PostgresPipeline(table_name='tpex_cb_daily', batch_size=500, **DB)
    s = TpexCbDailySpider(pipeline=p)
    r = s.fetch_date_range(START, END)
    results['tpex_cb_daily'] = r.get('total_items', 0)
    results['tpex_cb_daily_days'] = r.get('success_count', 0)
    print(f'  ✅ TpexCbDaily: {results["tpex_cb_daily"]} 筆 / {results["tpex_cb_daily_days"]} 天')

    return results


def step_clean():
    c = DataCleaner(DB)
    r = c.run_all()
    c.close()

    sd = r['stock_daily']
    cd = r['tpex_cb_daily']
    print(f'  ✅ stock_daily:   {sd["ok"]} OK / {sd["not_found"]} NOT_FOUND')
    print(f'  ✅ tpex_cb_daily: {cd["ok"]} OK / {cd["not_found"]} NOT_FOUND')
    return r


def step_verify(spider_result, clean_result):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    errors = []

    cur.execute('SELECT COUNT(*) FROM stock_master')
    sm = cur.fetchone()[0]
    if sm < 1000:
        errors.append(f'stock_master: {sm} 筆 (預期 > 1000)')

    cur.execute('SELECT COUNT(*) FROM cb_master')
    cm = cur.fetchone()[0]
    if cm < 100:
        errors.append(f'cb_master: {cm} 筆 (預期 > 100)')

    sd = clean_result['stock_daily']
    if sd['total'] == 0:
        errors.append('stock_daily: 0 筆 (爬蟲無資料)')
    if sd['not_found'] > 0:
        errors.append(f'stock_daily NOT_FOUND: {sd["not_found"]} 筆 (預期 0)')

    cd = clean_result['tpex_cb_daily']
    if cd['total'] == 0:
        errors.append('tpex_cb_daily: 0 筆 (爬蟲無資料)')
    cur.execute("SELECT cb_code FROM tpex_cb_daily WHERE cb_code IN ('合計','GLOSS') LIMIT 1")
    if cur.fetchone():
        errors.append('tpex_cb_daily 仍有「合計」或「GLOSS」行')

    cur.execute("SELECT cb_code FROM tpex_cb_daily WHERE master_check='OK' AND cb_name_enriched IS NULL LIMIT 1")
    if cur.fetchone():
        errors.append('tpex_cb_daily: OK 行但無 cb_name_enriched (併表失敗)')

    cur.execute("SELECT symbol FROM stock_daily WHERE master_check='OK' AND name IS NULL LIMIT 1")
    if cur.fetchone():
        errors.append('stock_daily: OK 行但無 name (併表失敗)')

    cur.close()
    conn.close()

    return errors


def main():
    print("=" * 55)
    print("  整合測試：爬蟲 + 清洗全流程")
    print(f"  範圍: {START} ~ {END}")
    print("=" * 55)
    print()

    print("Step 1/3: 清空 DB")
    step_clear()

    print("Step 2/3: 爬蟲")
    t0 = time.time()
    spider_result = step_spiders()
    t_spider = time.time() - t0

    print()
    print("Step 3/3: 清洗")
    t0 = time.time()
    clean_result = step_clean()
    t_clean = time.time() - t0

    print()
    print("=" * 55)
    print("  驗證")
    print("=" * 55)
    errors = step_verify(spider_result, clean_result)

    if errors:
        print(f"\n❌ 失敗 ({len(errors)} 項):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n✅ 全部通過")

    print(f"\n爬蟲耗時: {t_spider:.0f}s")
    print(f"清洗耗時: {t_clean:.1f}s")
    print(f"總耗時: {t_spider + t_clean:.0f}s")


if __name__ == "__main__":
    main()
