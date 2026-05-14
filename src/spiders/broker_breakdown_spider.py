"""
BSR 券商分點買賣超爬蟲
透過 BsrClient（BSR 網站 + ddddocr OCR）查詢券商分點明細

Source: https://bsr.twse.com.tw/bshtm/

Usage:
    spider = BrokerBreakdownSpider()
    spider.collect_only = True
    result = spider.fetch_broker_breakdown("20260509", "2330")
    for item in spider.get_items():
        print(item.to_dict())
"""
from typing import Optional, List, Dict, Any
from src.framework.base_spider import BaseSpider, SpiderResponse
from src.framework.base_item import BrokerBreakdownItem
from src.spiders.bsr_client import (
    BsrClient,
    BsrConnectionError,
    BsrCaptchaError,
    BsrParseError,
    BsrCircuitBreakerOpen,
)


class BrokerBreakdownSpider(BaseSpider):
    """
    券商分點買賣超爬蟲

    Source: BSR (Basic Securities Report) 網站
    透過 BsrClient 封裝的 session / captcha / submit 流程取得資料

    Attributes:
        pipeline: 資料寫入管道
        items: BrokerBreakdownItem 列表
    """

    def __init__(self, pipeline=None, thread_count=1, redis_key=None, **kwargs):
        super().__init__(thread_count=thread_count, redis_key=redis_key, **kwargs)
        self.pipeline = pipeline
        self.items: List[BrokerBreakdownItem] = []
        self.collect_only = True
        self._bsr_client: Optional[BsrClient] = None

    @property
    def bsr_client(self) -> BsrClient:
        """Lazy-init BsrClient"""
        if self._bsr_client is None:
            self._bsr_client = BsrClient()
        return self._bsr_client

    def fetch_broker_breakdown(self, date: str, symbol: str) -> SpiderResponse:
        """
        抓取指定日期/股票的分點買賣超

        Args:
            date: 日期 YYYYMMDD 格式 (傳入 item，不影響查詢)
            symbol: 股票代號 (如 "2330")

        Returns:
            SpiderResponse
        """
        self.items.clear()

        try:
            records = self.bsr_client.fetch_broker_data(symbol)

            for record in records:
                item = BrokerBreakdownItem(
                    date=date,
                    symbol=symbol,
                    broker_id=str(record.get("broker_id", "")),
                    broker_name=record.get("broker_name", ""),
                    buy_volume=int(record.get("buy_volume", 0) or 0),
                    sell_volume=int(record.get("sell_volume", 0) or 0),
                    net_volume=int(record.get("net_volume", 0) or 0),
                    rank=int(record.get("seq", 0)),
                    source_type="bsr",
                    source_url="https://bsr.twse.com.tw/bshtm/",
                )
                self.items.append(item)
                self.add_item(item)

            return SpiderResponse(
                success=True,
                data={"count": len(self.items)},
                url="https://bsr.twse.com.tw/bshtm/",
            )

        except BsrConnectionError as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
                url="https://bsr.twse.com.tw/bshtm/",
            )
        except BsrCaptchaError as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
                url="https://bsr.twse.com.tw/bshtm/",
            )
        except BsrParseError as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
                url="https://bsr.twse.com.tw/bshtm/",
            )
        except BsrCircuitBreakerOpen as e:
            return SpiderResponse(
                success=False,
                error=f"BSR 查詢失敗: {e}",
                url="https://bsr.twse.com.tw/bshtm/",
            )

    def get_items(self) -> List[BrokerBreakdownItem]:
        """取得本次抓取的分點資料"""
        return self.items

    def get_statistics(self) -> Dict[str, Any]:
        """取得爬蟲統計"""
        stats = super().get_statistics()
        stats.update({"total_items": len(self.items)})
        return stats

    def close(self) -> None:
        """清理 BsrClient"""
        if self._bsr_client is not None:
            self._bsr_client.close()
            self._bsr_client = None


# CLI 支援
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="券商分點買賣超爬蟲")
    parser.add_argument("--date", required=True, help="日期 (YYYYMMDD)")
    parser.add_argument("--symbol", required=True, help="股票代號")
    args = parser.parse_args()

    spider = BrokerBreakdownSpider()
    try:
        result = spider.fetch_broker_breakdown(args.date, args.symbol)
        print(f"Success: {result.success}")
        print(f"Items: {len(spider.get_items())}")
        for item in spider.get_items():
            print(f"  {item.rank}. {item.broker_name}({item.broker_id}): "
                  f"買 {item.buy_volume} / 賣 {item.sell_volume} / 淨 {item.net_volume}")
    finally:
        spider.close()
