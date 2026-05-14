#!/bin/bash

# 爬蟲系統遷移專案 - 環境設置腳本
# 版本: 1.0.0
# 創建日期: 2026-04-15

set -e  # 遇到錯誤時退出

echo "========================================="
echo "爬蟲系統遷移專案 - 環境設置腳本"
echo "========================================="

# 檢查 Python 版本
echo "檢查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "當前 Python 版本: $python_version"

# 檢查 Python 3.8+
if [[ "$python_version" =~ ^3\.[8-9]\. || "$python_version" =~ ^3\.[1-9][0-9]\. ]]; then
    echo "✓ Python 版本符合要求 (3.8+)"
else
    echo "✗ Python 版本不符合要求，需要 3.8+"
    exit 1
fi

# 檢查 pip
echo "檢查 pip..."
if command -v pip3 &> /dev/null; then
    pip_version=$(pip3 --version | awk '{print $2}')
    echo "✓ pip 已安裝，版本: $pip_version"
else
    echo "✗ pip 未安裝，請先安裝 pip"
    exit 1
fi

# 安裝 Feapder
echo "安裝 Feapder 框架..."
pip3 install feapder

# 驗證 Feapder 安裝
echo "驗證 Feapder 安裝..."
if python3 -c "import feapder; print(f'✓ Feapder 已安裝，版本: {feapder.__version__}')" 2>/dev/null; then
    echo "Feapder 安裝成功"
else
    echo "✗ Feapder 安裝失敗"
    exit 1
fi

# 安裝可選依賴
echo "安裝可選依賴..."
pip3 install feapder[all]

# 創建測試項目
echo "創建測試項目..."
test_project_dir="feapder_test_project"
if [ ! -d "$test_project_dir" ]; then
    feapder create -p "$test_project_dir"
    echo "✓ 測試項目創建成功: $test_project_dir"
else
    echo "✓ 測試項目已存在: $test_project_dir"
fi

# 進入測試項目並創建測試爬蟲
cd "$test_project_dir"
feapder create -s test_spider

# 運行測試爬蟲
echo "運行測試爬蟲..."
if python3 test_spider.py; then
    echo "✓ 測試爬蟲運行成功"
else
    echo "✗ 測試爬蟲運行失敗"
    exit 1
fi

cd ..

# 檢查 Git
echo "檢查 Git..."
if command -v git &> /dev/null; then
    git_version=$(git --version | awk '{print $3}')
    echo "✓ Git 已安裝，版本: $git_version"
else
    echo "⚠ Git 未安裝，建議安裝以進行版本控制"
fi

# 檢查虛擬環境
echo "檢查虛擬環境..."
if [ -d "venv" ] || [ -d ".venv" ]; then
    echo "✓ 虛擬環境已存在"
else
    echo "⚠ 未檢測到虛擬環境，建議創建:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
fi

# 輸出環境摘要
echo ""
echo "========================================="
echo "環境設置完成摘要"
echo "========================================="
echo "1. Python 版本: $python_version ✓"
echo "2. pip 版本: $pip_version ✓"
echo "3. Feapder 版本: $(python3 -c 'import feapder; print(feapder.__version__)' 2>/dev/null) ✓"
echo "4. 測試項目: $test_project_dir ✓"
echo "5. Git: $(command -v git &> /dev/null && echo '已安裝' || echo '未安裝')"
echo "6. 虛擬環境: $( [ -d "venv" ] || [ -d ".venv" ] && echo '已存在' || echo '未創建' )"
echo ""
echo "下一步:"
echo "1. 閱讀 docs/agent_context/spider_migration_plan/README.md"
echo "2. 參加 Feapder 培訓"
echo "3. 開始階段 0 的系統分析工作"
echo "========================================="