import os
import sys
import csv
import shutil
import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from etl import validate_and_enrich

TEST_DAILY_DIR = "data/test_clean/daily"
TEST_CB_MASTER_DIR = "data/test_raw/master"
TEST_DAILY = os.path.join(TEST_DAILY_DIR, "test_cb.csv")
TEST_CB_MASTER = os.path.join(TEST_CB_MASTER_DIR, "cb_list_test.csv")

def setup_env(cb_rows, daily_rows):
    os.makedirs(TEST_DAILY_DIR, exist_ok=True)
    os.makedirs(TEST_CB_MASTER_DIR, exist_ok=True)
    with open(TEST_CB_MASTER, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["債券代碼", "債券簡稱", "轉換價格"])
        writer.writeheader()
        for row in cb_rows:
            writer.writerow(row)
    with open(TEST_DAILY, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["代號", "數值"])
        writer.writeheader()
        for row in daily_rows:
            writer.writerow(row)

def cleanup():
    if os.path.exists(TEST_DAILY):
        os.remove(TEST_DAILY)
    if os.path.exists(TEST_CB_MASTER):
        os.remove(TEST_CB_MASTER)
    cb_glob = os.path.join(TEST_CB_MASTER_DIR, "cb_list_*.csv")
    for f in glob.glob(cb_glob):
        os.remove(f)

def test_enrich_cb_fields():
    cleanup()
    setup_env(
        cb_rows=[
            {"債券代碼": "CB123", "債券簡稱": "可轉債A", "轉換價格": "100.5"},
            {"債券代碼": "CB999", "債券簡稱": "可轉債B", "轉換價格": "200.0"},
        ],
        daily_rows=[
            {"代號": "CB123", "數值": "10"},
            {"代號": "CB999", "數值": "20"},
            {"代號": "X999", "數值": "30"},
        ]
    )
    # 模擬 cb_list_*.csv 命名
    cb_master_real = os.path.join(TEST_CB_MASTER_DIR, "cb_list_20240101.csv")
    os.rename(TEST_CB_MASTER, cb_master_real)
    validate_and_enrich.validate_and_enrich(
        daily_dir=TEST_DAILY_DIR,
        cb_master_glob=os.path.join(TEST_CB_MASTER_DIR, "cb_list_*.csv"),
        stock_master_path="data/test_raw/master/stock_list.csv"  # dummy, not used in this test
    )
    with open(TEST_DAILY, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert rows[0]["master_check"] == "OK"
        assert rows[0]["master_債券簡稱"] == "可轉債A"
        assert rows[0]["master_轉換價格"] == "100.5"
        assert rows[1]["master_check"] == "OK"
        assert rows[1]["master_債券簡稱"] == "可轉債B"
        assert rows[1]["master_轉換價格"] == "200.0"
        assert rows[2]["master_check"] == "NOT_FOUND"
    print("test_enrich_cb_fields: PASS")
    # 清理
    os.remove(cb_master_real)
    cleanup()

if __name__ == "__main__":
    test_enrich_cb_fields()