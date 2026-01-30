import os
import sys
import csv
import shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
from etl import validate_and_enrich

TEST_DAILY = "data/clean/daily/test.csv"
TEST_MASTER = "data/clean/master.csv"

def setup_env(master_ids, daily_rows):
    os.makedirs("data/clean/daily", exist_ok=True)
    with open(TEST_MASTER, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["代號", "名稱"])
        writer.writeheader()
        for mid in master_ids:
            writer.writerow({"代號": mid, "名稱": f"Name{mid}"})
    with open(TEST_DAILY, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["代號", "數值"])
        writer.writeheader()
        for row in daily_rows:
            writer.writerow(row)

def cleanup():
    if os.path.exists(TEST_DAILY):
        os.remove(TEST_DAILY)
    if os.path.exists(TEST_MASTER):
        os.remove(TEST_MASTER)

def test_enrich_ok_and_notfound():
    cleanup()
    setup_env(master_ids=["A123", "B456"], daily_rows=[
        {"代號": "A123", "數值": "10"},
        {"代號": "X999", "數值": "20"},
    ])
    validate_and_enrich.validate_and_enrich()
    with open(TEST_DAILY, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert rows[0]["master_check"] == "OK"
        assert rows[1]["master_check"] == "NOT_FOUND"
    print("test_enrich_ok_and_notfound: PASS")
    cleanup()

if __name__ == "__main__":
    test_enrich_ok_and_notfound()