#!/bin/bash
# 手動驗證腳本：真實連線到 TWSE/TPEx，確認爬蟲能正常抓取資料
# 用法: bash scripts/verify_real_spiders.sh
# 不納入自動測試，僅供手動驗證

set -e

cd "$(dirname "$0")/.."
PYTHON=".venv/bin/python3"
OUTPUT_DIR="data/verify_output"
mkdir -p "$OUTPUT_DIR"

echo "=============================================="
echo "  爬蟲真實連線驗證"
echo "  日期: $(date '+%Y-%m-%d %H:%M')"
echo "=============================================="
echo ""

# ─── 股票主檔（TWSE） ────────────────────────────
echo "▸ 測試: StockMasterSpider.fetch_twse()"
echo "  URL: https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
$PYTHON -c "
import sys; sys.path.insert(0, 'src')
from spiders.stock_master_spider import StockMasterSpider
from framework.pipelines import CsvPipeline
import os

pipeline = CsvPipeline(output_dir='$OUTPUT_DIR/twse_master', batch_size=1000)
spider = StockMasterSpider(pipeline=pipeline)
result = spider.fetch_twse()
spider.close()

print(f'    狀態: {\"✅ 成功\" if result.success else \"❌ 失敗\"} ')
print(f'    資料筆數: {result.data.get(\"count\", 0)}')
if result.success:
    items = spider.get_items()
    sample = items[:3]
    for item in sample:
        print(f'    - {item.symbol} {item.name}')
" 2>&1 | grep -v "^INFO\|^WARNING\|^$"
echo ""

# ─── 股票日行情（TWSE） ──────────────────────────
echo "▸ 測試: StockDailySpider.fetch_daily(2330)"
echo "  URL: https://www.twse.com.tw/exchangeReport/STOCK_DAY"
$PYTHON -c "
import sys; sys.path.insert(0, 'src')
from spiders.stock_daily_spider import StockDailySpider
from framework.pipelines import CsvPipeline

pipeline = CsvPipeline(output_dir='$OUTPUT_DIR/twse_daily', batch_size=1000)
spider = StockDailySpider(pipeline=pipeline)
result = spider.fetch_daily('2330', 2025, 12)
spider.close()

print(f'    狀態: {\"✅ 成功\" if result.success else \"❌ 失敗\"} ')
print(f'    資料筆數: {result.data.get(\"count\", 0)}')
if result.success:
    for item in spider.get_items()[:3]:
        print(f'    - {item.date} 開:{item.open_price} 收:{item.close_price}')
" 2>&1 | grep -v "^INFO\|^WARNING\|^$"
echo ""

# ─── 可轉債主檔（TPEx） ─────────────────────────
echo "▸ 測試: CbMasterSpider.fetch_cb_master()"
echo "  URL: https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/..."
$PYTHON -c "
import sys; sys.path.insert(0, 'src')
from spiders.cb_master_spider import CbMasterSpider
from framework.pipelines import CsvPipeline
from datetime import datetime

pipeline = CsvPipeline(output_dir='$OUTPUT_DIR/cb_master', batch_size=1000)
spider = CbMasterSpider(pipeline=pipeline)
result = spider.fetch_cb_master()
spider.close()

print(f'    狀態: {\"✅ 成功\" if result.success else \"❌ 失敗\"} ')
print(f'    資料筆數: {result.data.get(\"count\", 0) if result.data else 0}')
if result.success and spider.get_items():
    for item in spider.get_items()[:3]:
        print(f'    - {item.cb_code} {item.cb_name} ({item.underlying_stock})')
" 2>&1 | grep -v "^INFO\|^WARNING\|^$"
echo ""

# ─── 可轉債日行情（TPEx） ───────────────────────
echo "▸ 測試: TpexCbDailySpider.fetch_daily()"
echo "  URL: https://www.tpex.org.tw/web/bond/bond_info/cb_daily_result/download.php"
$PYTHON -c "
import sys; sys.path.insert(0, 'src')
from spiders.tpex_cb_daily_spider import TpexCbDailySpider
from framework.pipelines import CsvPipeline

pipeline = CsvPipeline(output_dir='$OUTPUT_DIR/tpex_cb_daily', batch_size=1000)
spider = TpexCbDailySpider(pipeline=pipeline)
result = spider.fetch_daily('2025-12-15')
spider.close()

print(f'    狀態: {\"✅ 成功\" if result.success else \"❌ 失敗\"} ')
print(f'    資料筆數: {result.data.get(\"count\", 0) if result.data else 0}')
if result.success and spider.get_items():
    for item in spider.get_items()[:3]:
        print(f'    - {item.cb_code} {item.cb_name} 收盤:{item.closing_price}')
" 2>&1 | grep -v "^INFO\|^WARNING\|^$"
echo ""

# ─── 摘要 ───────────────────────────────────────
echo "=============================================="
echo "  驗證完成"
echo "  輸出目錄: $OUTPUT_DIR/"
ls -la "$OUTPUT_DIR"/*/ 2>/dev/null || echo "  (部分可能無資料)"
echo "=============================================="
