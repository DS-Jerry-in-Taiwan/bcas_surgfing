import os
import csv
import glob

def validate_and_enrich(logger=None, daily_dir="data/clean/daily", stock_master_path="data/raw/master/stock_list.csv", cb_master_glob="data/raw/master/cb_list_*.csv"):
    def load_master_dict(master_path, key):
        d = {}
        if not os.path.exists(master_path):
            return d
        with open(master_path, encoding="utf-8") as fin:
            reader = csv.DictReader(fin)
            for row in reader:
                d[row.get(key)] = row
        return d

    def get_cb_master_path():
        cb_files = sorted(glob.glob(cb_master_glob), reverse=True)
        return cb_files[0] if cb_files else None

    for fname in os.listdir(daily_dir):
        if not fname.endswith(".csv"):
            continue
        daily_path = os.path.join(daily_dir, fname)
        # 判斷是否 CB daily
        is_cb = "cb" in fname.lower()
        if is_cb:
            master_path = get_cb_master_path()
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
                    msg = f"NOT_FOUND: {code} in {fname}"
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                else:
                    row["master_check"] = "OK"
                    # 補充主檔欄位
                    if master_row:
                        for field in enrich_fields:
                            row[f"master_{field}"] = master_row.get(field, "")
                all_fields.update(row.keys())
                rows.append(row)
        # 覆寫 enriched csv
        fieldnames = list(all_fields)
        with open(daily_path, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        if logger:
            logger.info(f"Validated & enriched: {fname}")
        else:
            print(f"Validated & enriched: {fname}")

if __name__ == "__main__":
    validate_and_enrich()