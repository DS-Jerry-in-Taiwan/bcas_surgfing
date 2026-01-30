import os
import glob
import csv
import re
from datetime import datetime

RAW_DIR = "data/raw/daily"
CLEAN_DIR = "data/clean/daily"
os.makedirs(CLEAN_DIR, exist_ok=True)

def minguo_to_ad(minguo_str):
    # 114年01月02日 -> 2025-01-02
    m = re.match(r"(\d+)年(\d+)月(\d+)日", minguo_str)
    if not m:
        return None
    year = int(m.group(1)) + 1911
    month = int(m.group(2))
    day = int(m.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"

def clean_csv(raw_path, clean_path):
    with open(raw_path, encoding="utf-8") as fin, open(clean_path, "w", encoding="utf-8", newline="") as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        header_found = False
        date_str = None
        for row in reader:
            # 解析 DATADATE 行
            if row and row[0].strip() == "DATADATE":
                # e.g. DATADATE,日期:114年01月02日
                m = re.search(r"日期[:：](\d+年\d+月\d+日)", row[1])
                if m:
                    date_str = minguo_to_ad(m.group(1))
            # 找到 HEADER 行
            if not header_found and row and row[0].strip() == "HEADER":
                header = [col.strip() for col in row[1:]]
                if date_str:
                    header = ["日期"] + header
                writer.writerow(header)
                header_found = True
                continue
            # 寫入 BODY 行
            if header_found and row and row[0].strip() == "BODY":
                body = [col.replace(",", "") for col in row[1:]]
                if date_str:
                    body = [date_str] + body
                writer.writerow(body)
    # 若無 HEADER/BODY 則產生空檔

def batch_clean():
    for raw_path in glob.glob(os.path.join(RAW_DIR, "*.csv")):
        fname = os.path.basename(raw_path)
        clean_path = os.path.join(CLEAN_DIR, fname)
        clean_csv(raw_path, clean_path)
        print(f"Cleaned: {fname}")

if __name__ == "__main__":
    batch_clean()