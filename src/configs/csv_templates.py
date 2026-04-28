"""
CSV 格式模板

定義各爬蟲來源的 CSV 格式設定，
Parser 根據對應的 CsvTemplate 解析資料。
當來源端變更格式時，只需修改此檔，不需改動爬蟲程式碼。
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CsvTemplate:
    """CSV 格式模板"""
    encoding: str = "utf-8"
    skip_prefixes: List[str] = field(default_factory=list)
    header_prefixes: List[str] = field(default_factory=list)
    body_prefixes: List[str] = field(default_factory=list)
    column_mapping: Dict[str, str] = field(default_factory=dict)
    defaults: Dict[str, str] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    delimiter: str = ","
    quote_char: str = '"'


# ─── TPEx 可轉債主檔 CSV ─────────────────────────
CB_MASTER_TPEX = CsvTemplate(
    encoding="big5",
    skip_prefixes=["TITLE", "DATADATE", "ALIGN"],
    header_prefixes=["HEADER,", "GLOSS,"],
    body_prefixes=["BODY,", "DATA,"],
    column_mapping={
        "債券代碼": "cb_code",
        "債券簡稱": "cb_name",
        "轉換起日": "issue_date",
        "轉換迄日": "maturity_date",
        "轉換價格": "conversion_price",
    },
    defaults={
        "market_type": "TPEx",
        "source_type": "tpex_cb",
    },
    required_fields=["cb_code"],
)


# ─── TPEx 可轉債日行情 CSV ────────────────────────
CB_DAILY_TPEX = CsvTemplate(
    encoding="big5",
    skip_prefixes=["TITLE", "DATADATE", "ALIGN"],
    header_prefixes=["HEADER,"],
    body_prefixes=["BODY,"],
    column_mapping={
        "代號": "cb_code",
        "名稱": "cb_name",
        "收市": "closing_price",
        "單位": "volume",
    },
    defaults={
        "underlying_stock": "",
        "turnover_rate": "0",
        "premium_rate": "0",
        "conversion_price": "0",
        "remaining_balance": "0",
    },
    required_fields=["cb_code"],
)
