#!/bin/bash
# ============================================================
# BCAS Quant - EOD 盤後分析啟動腳本
# ============================================================
# 用法:
#   ./scripts/start_eod.sh                    # 執行全部 4 階段
#   ./scripts/start_eod.sh --stage 1          # 只跑爬蟲
#   ./scripts/start_eod.sh --stage 4          # 只跑報表
#   ./scripts/start_eod.sh --date 2026-05-11  # 指定日期
# ============================================================

cd "$(dirname "$0")/.."

echo "=========================================="
echo " BCAS Quant - EOD 盤後分析系統"
echo " Version: $(cat VERSION 2>/dev/null || echo '3.0.0')"
echo " 時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 確保 PostgreSQL 已啟動 (Docker)
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL 未啟動，嘗試 docker-compose..."
    docker-compose up -d postgres
    sleep 3
fi

# 執行 EOD Pipeline
python3 src/run_eod_analysis.py "$@"

# 結束
EXIT_CODE=$?
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo " ✅ EOD 分析完成"
else
    echo " ❌ EOD 分析失敗 (exit code: $EXIT_CODE)"
fi
echo "=========================================="
exit $EXIT_CODE
