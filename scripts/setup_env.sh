#!/bin/bash
# 環境初始化腳本
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}開始初始化環境...${NC}"

# 創建虛擬環境
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "虛擬環境已創建"
fi

# 啟用虛擬環境
source .venv/bin/activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt

# 複製 .env.example 為 .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env 文件已創建，請編輯填入 API Keys"
fi

echo -e "${GREEN}環境初始化完成！${NC}"
echo "使用 'source .venv/bin/activate' 啟用虛擬環境"
