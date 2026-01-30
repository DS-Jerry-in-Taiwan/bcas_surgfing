import os
import glob
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASS = os.getenv("PG_PASS", "postgres")
DB_NAME = os.getenv("PG_DB", "cbas")

def upsert_cb_master(conn, df):
    with conn.cursor() as cur:
        records = df.to_dict("records")
        sql = """
        INSERT INTO cb_master (symbol, name, issue_date, maturity_date)
        VALUES %s
        ON CONFLICT (symbol) DO UPDATE
        SET name=EXCLUDED.name, issue_date=EXCLUDED.issue_date, maturity_date=EXCLUDED.maturity_date;
        """
        values = [
            (
                r.get("symbol"),
                r.get("name"),
                r.get("issue_date", None),
                r.get("maturity_date", None)
            )
            for r in records
        ]
        execute_values(cur, sql, values)
    conn.commit()

def upsert_cb_daily(conn, df):
    # 過濾掉代號為空或 NaN 的資料
    df = df[df["代號"].notnull() & (df["代號"].astype(str).str.strip() != "")]
    with conn.cursor() as cur:
        records = df.to_dict("records")
        # 根據清洗後表頭調整欄位
        sql = """
        INSERT INTO cb_daily (symbol, date, close, volume)
        VALUES %s
        ON CONFLICT (symbol, date) DO UPDATE
        SET close=EXCLUDED.close, volume=EXCLUDED.volume;
        """
        def safe_int(val):
            try:
                v = int(str(val).strip())
                if abs(v) > 9223372036854775807:
                    return None
                return v
            except Exception:
                return None

        values = [
            (
                r["代號"],
                r["日期"],
                r.get("收市", None),   # 若有「收盤」欄位請改為 r.get("收盤", None)
                safe_int(r.get("筆數", None))    # robust 處理
            )
            for r in records
        ]
        execute_values(cur, sql, values)
    conn.commit()

def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    # 匯入主檔
    master_path = "data/raw/master/cb_list_master.csv"
    if os.path.exists(master_path):
        df_master = pd.read_csv(master_path, encoding="utf-8")
        # 將日期欄位轉為字串或 None，避免 NaN/float 傳入資料庫
        for col in ["issue_date", "maturity_date"]:
            if col in df_master.columns:
                df_master[col] = pd.to_datetime(df_master[col], errors="coerce")
                df_master[col] = df_master[col].apply(lambda x: x.date() if not pd.isnull(x) and x != pd.NaT else None)
        upsert_cb_master(conn, df_master)
        print(f"Imported {len(df_master)} records to cb_master")
    # 匯入日行情
    for csv_path in glob.glob("data/clean/daily/tpex_cb_daily_*.csv"):
        try:
            df_daily = pd.read_csv(csv_path, encoding="utf-8")
            if "代號" in df_daily.columns and "日期" in df_daily.columns:
                upsert_cb_daily(conn, df_daily)
                print(f"Imported {len(df_daily)} records from {csv_path}")
            else:
                print(f"[SKIP] {csv_path} 欄位不符: {df_daily.columns.tolist()}")
        except Exception as e:
            print(f"[ERROR] {csv_path} 讀取失敗: {e}")
    conn.close()

if __name__ == "__main__":
    main()