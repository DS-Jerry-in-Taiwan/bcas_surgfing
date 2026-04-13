import os
import re
import csv
import glob
from datetime import datetime

def load_master_dict(master_path, key):
    d = {}
    if not master_path or not os.path.exists(master_path):
        return d
    with open(master_path, encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            d[row.get(key)] = row
    return d

def find_master_for_daily(daily_date, master_files):
    """
    find the most appropreate date for daily and master file
    """
    master_dates = []
    for f in master_files:
        m = re.search(f'(\d{8})', f)
        if m:
            master_dates.append((datetime.strptime(m.group(1), '%Y%m%d'), f))
    master_dates.sort()
    for d, f in reversed(master_dates):
        if d <= daily_date:
            return f
    return None

def validate_and_enrich(
    logger=None,
    daily_dir="data/clean/daily_cb",
    out_dir="data/enriched/daily_cb",
    stock_master_path="data/raw/master_stock/stock_list.csv",
    cb_master_glob="data/raw/master/cb_list_*.csv"
):
    os.makedirs(out_dir, exist_ok=True)
    master_files = glob.glob(cb_master_glob)
    for fname in os.listdir(daily_dir):
        if not fname.endswith(".csv"):
            continue
        daily_path = os.path.join(daily_dir, fname)
        out_path = os.path.join(out_dir, fname)
        is_cb = "cb" in fname.lower()
        if is_cb:
            # 從檔名取日期
            m = re.search(r'(\d{8})', fname)
            if m:
                daily_date = datetime.strptime(m.group(1), "%Y%m%d")
                master_path = find_master_for_daily(daily_date, master_files)
            else:
                master_path = None
            master_key = "債券代碼"
            enrich_fields = ["債券簡稱", "轉換價格"]
        else:
            master_path = stock_master_path
            master_key = "symbol"
            enrich_fields = []
        master_dict = load_master_dict(master_path, master_key) if master_path else {}
        rows = []
        all_fields = set()
        with open(daily_path, encoding="utf-8") as fin:
            reader = csv.DictReader(fin)
            for row in reader:
                code = row.get("代號") or row.get("ID") or row.get("Code")
                master_row = master_dict.get(code)
                if code and not master_row:
                    row["master_check"] = "NOT_FOUND"
                    # 取得 daily 檔案日期（優先欄位，其次檔名）
                    daily_date = row.get("日期")
                    if not daily_date:
                        m = re.search(r'(\d{8})', fname)
                        daily_date = m.group(1) if m else ""
                    msg = f"NOT_FOUND: {code} on {daily_date} in {fname}"
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                else:
                    row["master_check"] = "OK"
                    # 補充主檔欄位
                    if master_row:
                        for field in enrich_fields:
                            row[field] = master_row.get(field, "")
                all_fields.update(row.keys())
                rows.append(row)
        # 強制欄位順序，NOT_FOUND 統一標記
        base_fields = ["日期", "代號", "master_check"]
        extra_fields = [f for f in all_fields if f not in base_fields]
        fieldnames = base_fields + sorted(extra_fields)
        # 若全為 NOT_FOUND，於檔案開頭加註說明
        all_not_found = all(row.get("master_check") == "NOT_FOUND" for row in rows)
        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            if all_not_found:
                fout.write("# 所有資料皆無法對應 master，請檢查主檔與 daily 日期是否正確\n")
            writer.writerows(rows)
        if logger:
            logger.info(f"Validated & enriched: {fname} -> {out_path} (all NOT_FOUND: {all_not_found})")
        else:
            print(f"Validated & enriched: {fname} -> {out_path} (all NOT_FOUND: {all_not_found})")

if __name__ == "__main__":
    validate_and_enrich()