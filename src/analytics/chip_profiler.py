"""
ChipProfiler - 籌碼分析

功能:
  - 載入券商黑名單 JSON
  - 比對 broker_breakdown 分點資料
  - 計算隔日沖風險佔比

用法:
    python -m src.analytics.chip_profiler --date 2026-05-11
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Any

import psycopg2

from src.run_daily import DB_CONFIG


class ChipProfiler:
    """籌碼分析：比對分點與黑名單，計算風險"""

    def __init__(self, blacklist_path: Optional[str] = None):
        if blacklist_path is None:
            blacklist_path = os.path.join(
                os.path.dirname(__file__), "..", "configs", "broker_blacklist.json"
            )
        self.blacklist_path = blacklist_path
        self.blacklist: Dict[str, dict] = {}
        self.load_blacklist()

    def load_blacklist(self) -> int:
        """載入券商黑名單 JSON，回傳筆數

        若檔案不存在，不拋錯，回傳 0。
        """
        path = os.path.abspath(self.blacklist_path)
        if not os.path.exists(path):
            self.blacklist = {}
            return 0
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        self.blacklist = {
            r["broker_id"]: r for r in records
        }
        return len(self.blacklist)

    def get_risk_level(self, broker_id: str) -> Optional[str]:
        """查詢券商風險等級

        Args:
            broker_id: 券商代號

        Returns:
            風險等級字串 (HIGH/MEDIUM/LOW)，不在黑名單中回傳 None
        """
        broker = self.blacklist.get(broker_id)
        return broker.get("risk_level") if broker else None

    def is_suspicious(self, broker_id: str) -> bool:
        """是否為可疑券商

        Args:
            broker_id: 券商代號

        Returns:
            True 表示在黑名單中
        """
        return broker_id in self.blacklist

    def analyze(self, date: str) -> Dict[str, dict]:
        """執行籌碼分析

        從 broker_breakdown 讀取當日資料，
        比對黑名單，計算每檔股票的隔日沖風險佔比。

        Args:
            date: 分析日期 (YYYY-MM-DD)

        Returns:
            {symbol: {"risk_ratio": float, "matched_brokers": List[str],
                       "total_volume": int, "suspect_volume": int}}
        """
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
            # 取得當日所有分點資料
            cursor.execute("""
                SELECT symbol, broker_id, broker_name, buy_volume, sell_volume, net_volume
                FROM broker_breakdown
                WHERE date = %s
                ORDER BY symbol, rank
            """, (date,))
            rows = cursor.fetchall()

            # 依 symbol 分組
            by_symbol: Dict[str, list] = defaultdict(list)
            for row in rows:
                by_symbol[row[0]].append({
                    "broker_id": row[1],
                    "broker_name": row[2],
                    "buy_volume": row[3] or 0,
                    "sell_volume": row[4] or 0,
                    "net_volume": row[5] or 0,
                })

            # 每檔股票計算
            results: Dict[str, dict] = {}
            for symbol, brokers in by_symbol.items():
                # 取前 5 大買超
                top_buyers = sorted(
                    brokers, key=lambda x: x["buy_volume"], reverse=True
                )[:5]

                # 比對黑名單
                matched = [
                    b for b in top_buyers if self.is_suspicious(b["broker_id"])
                ]
                suspect_volume = sum(b["buy_volume"] for b in matched)
                total_volume = sum(b["buy_volume"] for b in brokers)

                risk_ratio = (
                    suspect_volume / total_volume if total_volume > 0 else 0.0
                )

                results[symbol] = {
                    "risk_ratio": round(risk_ratio, 4),
                    "matched_brokers": [b["broker_name"] for b in matched],
                    "total_volume": total_volume,
                    "suspect_volume": suspect_volume,
                }

            return results

        finally:
            cursor.close()
            conn.close()


# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="籌碼分析工具")
    parser.add_argument("--date", required=True, help="日期 (YYYY-MM-DD)")
    args = parser.parse_args()

    profiler = ChipProfiler()
    print(f"黑名單載入: {len(profiler.blacklist)} 筆")
    results = profiler.analyze(args.date)
    for symbol, info in results.items():
        print(
            f"{symbol}: 風險佔比={info['risk_ratio']:.1%}, "
            f"匹配={info['matched_brokers']}"
        )
