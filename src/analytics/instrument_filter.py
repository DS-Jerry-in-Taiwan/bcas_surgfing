"""
InstrumentFilter - 標的過濾器

在 PremiumCalculator 完成溢價率計算後執行，
根據到期日與停止轉換期資訊標記應剔除的標的。

過濾條件 (D 評級):
  1. 剩餘到期日 < 30 天 (maturity_date - 參考日期 < 30)
  2. 處於停止轉換期 (在 stop_conversion_schedule.json 設定範圍內)

注意事項:
  - maturity_date 為空時回傳 None，不觸發 D 評級
  - 錯誤不阻斷 PremiumCalculator 主流程
"""
from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime, date
import json
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """單一標的過濾結果"""
    symbol: str
    days_to_expiry: Optional[int] = None
    is_stopped: bool = False

    @property
    def is_filtered(self) -> bool:
        """是否應被過濾 (D 評級)

        Returns:
            True 表示該標的應被剔除
        """
        if self.days_to_expiry is not None and self.days_to_expiry < 30:
            return True
        if self.is_stopped:
            return True
        return False


class InstrumentFilter:
    """標的過濾器

    從 cb_master 表讀取 maturity_date，從設定檔讀取停止轉換期，
    對所有標的計算過濾結果。

    Attributes:
        EXPIRY_THRESHOLD_DAYS: 到期天數門檻 (小於此值視為到期)
    """

    EXPIRY_THRESHOLD_DAYS: int = 30

    def __init__(self, stop_config_path: Optional[str] = None):
        """初始化過濾器

        Args:
            stop_config_path: 停止轉換期設定檔路徑，預設為
                src/configs/stop_conversion_schedule.json
        """
        if stop_config_path is None:
            stop_config_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "configs",
                "stop_conversion_schedule.json"
            )
        self.config_path = stop_config_path
        self._stop_config: List[dict] = []
        self._load_stop_config()

    def _load_stop_config(self) -> int:
        """載入停止轉換期設定檔

        Returns:
            載入的設定筆數 (檔案不存在時回傳 0)
        """
        path = os.path.abspath(self.config_path)
        if not os.path.exists(path):
            logger.info("Stop conversion config not found: %s", path)
            self._stop_config = []
            return 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._stop_config = json.load(f)
            logger.info("Loaded %d stop conversion entries", len(self._stop_config))
            return len(self._stop_config)
        except json.JSONDecodeError as e:
            logger.error("Invalid stop conversion config JSON: %s", e)
            raise

    @staticmethod
    def compute_days_to_expiry(
        maturity_date_str: Optional[str],
        reference_date_str: Optional[str] = None
    ) -> Optional[int]:
        """計算距到期日的天數

        Args:
            maturity_date_str: 到期日期字串 (YYYY-MM-DD)
            reference_date_str: 參考日期 (預設今天)

        Returns:
            剩餘天數; maturity_date 為空或解析失敗時回傳 None
        """
        if not maturity_date_str:
            return None
        try:
            maturity = datetime.strptime(
                str(maturity_date_str)[:10], "%Y-%m-%d"
            ).date()
            if reference_date_str:
                ref = datetime.strptime(
                    str(reference_date_str)[:10], "%Y-%m-%d"
                ).date()
            else:
                ref = date.today()
            delta = (maturity - ref).days
            return delta
        except (ValueError, TypeError) as e:
            logger.warning(
                "Cannot parse maturity_date: '%s' - %s",
                maturity_date_str, e
            )
            return None

    def lookup_stop_conversion(self, symbol: str, date_str: str) -> bool:
        """查詢指定標的與日期是否在停止轉換期內

        Args:
            symbol: 標的股代號
            date_str: 查詢日期 (YYYY-MM-DD)

        Returns:
            是否在停止轉換期內
        """
        for entry in self._stop_config:
            if entry.get("symbol") == symbol:
                if entry["stop_start"] <= date_str <= entry["stop_end"]:
                    return True
        return False

    def filter(self, date_str: str) -> Dict[str, FilterResult]:
        """執行過濾，對所有標的計算過濾結果

        從 cb_master 讀取所有標的的 maturity_date，
        並與設定檔比對停止轉換期。

        Args:
            date_str: 參考日期 (YYYY-MM-DD)

        Returns:
            Dict[symbol, FilterResult]
        """
        import psycopg2
        from src.run_daily import DB_CONFIG

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT cb_code, underlying_stock, maturity_date
                FROM cb_master
                WHERE underlying_stock IS NOT NULL
                  AND underlying_stock != ''
            """)
            rows = cursor.fetchall()

            results = {}
            for cb_code, symbol, mat_date in rows:
                days = self.compute_days_to_expiry(mat_date, date_str)
                stopped = self.lookup_stop_conversion(symbol, date_str)
                results[symbol] = FilterResult(
                    symbol=symbol,
                    days_to_expiry=days,
                    is_stopped=stopped,
                )

            filtered_count = sum(1 for r in results.values() if r.is_filtered)
            logger.info(
                "InstrumentFilter: %d total, %d filtered",
                len(results),
                filtered_count,
            )
            return results

        finally:
            cursor.close()
            conn.close()
