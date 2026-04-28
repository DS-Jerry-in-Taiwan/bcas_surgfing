#!/bin/bash
# 驗證 CB Master CSV 可用性（真實連線測試）
# 用法: bash scripts/verify_cb_master.sh

set -e
cd "$(dirname "$0")/.."

echo "=== CB Master CSV 可用性檢查 ==="
echo ""

.venv/bin/python3 -c "
import requests
from datetime import datetime, timedelta

h = {'User-Agent': 'Mozilla/5.0'}
base = 'https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb'

today = datetime.now()
start = today - timedelta(days=30)  # 過去 30 天
d = start
avail, miss = 0, 0
while d <= today:
    ds = d.strftime('%Y%m%d')
    ym = d.strftime('%Y%m')
    url = f'{base}/{d.year}/{ym}/RSdrs001.{ds}-C.csv'
    resp = requests.get(url, headers=h, timeout=10)
    ok = resp.status_code == 200 and len(resp.content) > 20000
    if ok: avail += 1
    else: miss += 1
    d += timedelta(days=1)

print(f'過去 30 天: {avail} 天有資料 / {miss} 天無資料')
print(f'URL: {base}/.../RSdrs001.YYYYMMDD-C.csv')
print()
if avail > 0:
    print('✅ CB Master CSV 正常可用')
else:
    print('❌ 無可用資料，請檢查 URL 是否正確')
"
