import csv

f = "data/raw/daily_samples/RSta0113.20250102-C.csv"
with open(f, encoding="cp950", errors="ignore") as fh:
    r = list(csv.reader(fh))
    print("HEADER:", r[3])
    print("DATA:", r[4])
    print("HEADER len:", len(r[3]), "DATA len:", len(r[4]))