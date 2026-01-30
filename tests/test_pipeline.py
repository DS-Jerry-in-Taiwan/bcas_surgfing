import os
import subprocess
import shutil

def setup_test_env():
    # 清理 logs 與 clean 資料夾
    if os.path.exists("logs/crawler.log"):
        os.remove("logs/crawler.log")
    if os.path.exists("data/clean/daily"):
        shutil.rmtree("data/clean/daily")
    os.makedirs("data/clean/daily", exist_ok=True)

def test_pipeline_normal():
    setup_test_env()
    result = subprocess.run(
        ["python", "src/main_crawler.py", "--task", "all", "--date", "2025-01-02"],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    assert os.path.exists("logs/crawler.log")
    print("Normal pipeline run: PASS")

def test_pipeline_idempotency():
    setup_test_env()
    for _ in range(2):
        result = subprocess.run(
            ["python", "src/main_crawler.py", "--task", "all", "--date", "2025-01-02"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
    print("Idempotency test: PASS")

def test_pipeline_missing_master():
    setup_test_env()
    # 刻意移除 master.csv
    if os.path.exists("data/clean/master.csv"):
        os.remove("data/clean/master.csv")
    result = subprocess.run(
        ["python", "src/main_crawler.py", "--task", "all", "--date", "2025-01-02"],
        capture_output=True, text=True
    )
    assert "NOT_FOUND" in result.stdout or "NOT_FOUND" in open("logs/crawler.log").read()
    print("Missing master.csv test: PASS")

if __name__ == "__main__":
    test_pipeline_normal()
    test_pipeline_idempotency()
    test_pipeline_missing_master()