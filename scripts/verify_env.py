#!/usr/bin/env python3
"""環境驗證腳本"""
import sys
import os
from pathlib import Path

def verify_environment():
    """驗證環境配置"""
    errors = []
    
    print("驗證 Python 版本...")
    if sys.version_info < (3, 8):
        errors.append("需要 Python 3.8+")
    
    print("檢查虛擬環境...")
    venv_path = Path(".venv")
    if not venv_path.exists():
        errors.append("虛擬環境不存在，請先執行 setup_env.sh")
    
    print("檢查依賴套件...")
    required_packages = ["pydantic", "requests"]
    for pkg in required_packages:
        try:
            __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            errors.append(f"缺少套件: {pkg}")
    
    print("檢查 .env 文件...")
    if not Path(".env").exists():
        errors.append(".env 文件不存在")
    
    if errors:
        print("\n驗證失敗:")
        for err in errors:
            print(f"  ✗ {err}")
        return False
    
    print("\n驗證通過！")
    return True

if __name__ == "__main__":
    success = verify_environment()
    sys.exit(0 if success else 1)
