#!/bin/bash
# BCAS 每日流程啟動腳本
# 用法: bash scripts/start_daily.sh

set -e

cd "$(dirname "$0")/.."
VENV=".venv/bin/python3"

echo "=== BCAS 每日流程 ==="
echo "Step 0: 啟動 PostgreSQL"
docker compose up -d postgres
sleep 2

echo ""
echo "Step 1: 爬蟲 + 清洗 + 報告"
$VENV src/run_daily.py

echo ""
echo "=== 完成 ==="
