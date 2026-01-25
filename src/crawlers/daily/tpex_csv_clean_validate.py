import pandas as pd
import glob

def clean_tpex_csv(path):
    # 讀取原始 CSV，header=3, skiprows=[0,1,2]
    df = pd.read_csv(path, encoding="cp950", header=3, skiprows=[0,1,2])
    # 僅保留 BODY 行
    df = df[df["BODY"] == "BODY"]
    # 去除全為 NaN 的行
    df = df.dropna(how="all", axis=0)
    # 重設 index
    df = df.reset_index(drop=True)
    # 欄位對應（依 HEADER 行內容手動命名）
    columns = [
        "MARK", "symbol", "name", "trade_type", "close", "change", "open", "high", "low",
        "trades", "volume", "amount", "avg", "ref", "high_52w", "low_52w"
    ]
    if len(df.columns) == len(columns):
        df.columns = columns
    else:
        # 若欄位數不符，保留原欄位
        pass
    return df

if __name__ == "__main__":
    # 驗證 2025/01/02
    path = "data/raw/daily_samples/RSta0113.20250102-C.csv"
    df = clean_tpex_csv(path)
    print("Cleaned columns:", df.columns.tolist())
    print(df.head(3))
    # 驗證關鍵欄位與資料
    print("欄位包含 symbol, name, close, volume:", all(x in df.columns for x in ["symbol", "name", "close", "volume"]))
    print("資料筆數:", len(df))
    print("52694 in symbol:", (df["symbol"].astype(str) == "52694").any())