def convert_minguo_date(minguo_date: str) -> str:
    """
    將民國年(YYY/MM/DD)轉換為西元年(YYYY-MM-DD)
    例如：'113/01/01' -> '2024-01-01'
    """
    parts = minguo_date.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid minguo date: {minguo_date}")
    year = int(parts[0]) + 1911
    month = int(parts[1])
    day = int(parts[2])
    return f"{year:04d}-{month:02d}-{day:02d}"