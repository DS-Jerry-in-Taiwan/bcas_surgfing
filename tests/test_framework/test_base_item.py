"""
BaseItem 單元測試
"""
import pytest
from datetime import datetime

import sys
sys.path.insert(0, "src")

from framework.base_item import (
    BaseItem,
    StockDailyItem,
    TpexCbDailyItem,
    StockMasterItem,
    CbMasterItem,
    get_item_class,
    ITEM_REGISTRY,
)


class TestBaseItem:
    """BaseItem 測試"""
    
    def test_stock_daily_unique_key(self):
        """測試 StockDailyItem 唯一鍵"""
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0
        )
        assert item.get_unique_key() == "2330_2026-01-01"
    
    def test_stock_daily_to_dict(self):
        """測試 StockDailyItem 轉換為字典"""
        item = StockDailyItem(
            symbol="2330",
            date="2026-01-01",
            open_price=100.0,
            close_price=105.0
        )
        item_dict = item.to_dict()
        
        assert "symbol" in item_dict
        assert item_dict["symbol"] == "2330"
        assert "date" in item_dict
        assert "created_at" in item_dict
    
    def test_stock_daily_validate(self):
        """測試 StockDailyItem 驗證"""
        item = StockDailyItem()
        assert item.validate() is False
        
        item.symbol = "2330"
        item.date = "2026-01-01"
        assert item.validate() is True
    
    def test_stock_daily_update_timestamp(self):
        """測試 StockDailyItem 時間戳更新"""
        item = StockDailyItem(symbol="2330", date="2026-01-01")
        original_updated_at = item.updated_at
        
        import time
        time.sleep(0.01)
        item.update_timestamp()
        
        assert item.updated_at > original_updated_at
    
    def test_tpex_cb_unique_key(self):
        """測試 TpexCbDailyItem 唯一鍵"""
        item = TpexCbDailyItem(
            cb_code="12345",
            trade_date="2026-01-01",
            closing_price=110.0
        )
        assert item.get_unique_key() == "12345_2026-01-01"
    
    def test_tpex_cb_to_dict(self):
        """測試 TpexCbDailyItem 轉換為字典"""
        item = TpexCbDailyItem(
            cb_code="12345",
            cb_name="測試轉債",
            trade_date="2026-01-01",
            closing_price=110.0
        )
        item_dict = item.to_dict()
        
        assert "cb_code" in item_dict
        assert item_dict["cb_code"] == "12345"
        assert "closing_price" in item_dict
        assert item_dict["closing_price"] == 110.0
    
    def test_tpex_cb_validate(self):
        """測試 TpexCbDailyItem 驗證"""
        item = TpexCbDailyItem()
        assert item.validate() is False
        
        item.cb_code = "12345"
        item.trade_date = "2026-01-01"
        assert item.validate() is True
    
    def test_stock_master_unique_key(self):
        """測試 StockMasterItem 唯一鍵"""
        item = StockMasterItem(
            symbol="2330",
            name="台積電",
            market_type="TWSE"
        )
        assert item.get_unique_key() == "2330_TWSE"
    
    def test_cb_master_unique_key(self):
        """測試 CbMasterItem 唯一鍵"""
        item = CbMasterItem(
            cb_code="12345",
            cb_name="測試轉債",
            underlying_stock="2330"
        )
        assert item.get_unique_key() == "12345_2330"
    
    def test_item_table_name(self):
        """測試 Item 表名"""
        assert StockDailyItem.__table_name__ == "stock_daily"
        assert TpexCbDailyItem.__table_name__ == "tpex_cb_daily"
        assert StockMasterItem.__table_name__ == "stock_master"
        assert CbMasterItem.__table_name__ == "cb_master"
    
    def test_item_add_metadata(self):
        """測試添加元數據"""
        item = StockDailyItem(symbol="2330", date="2026-01-01")
        item.add_metadata("source", "twse_api")
        item.add_metadata("batch_id", "2026-01-01")
        
        assert "source" in item.metadata
        assert item.metadata["source"] == "twse_api"
        assert item.metadata["batch_id"] == "2026-01-01"
    
    def test_item_repr(self):
        """測試 __repr__"""
        item = StockDailyItem(symbol="2330", date="2026-01-01")
        repr_str = repr(item)
        
        # 驗證包含類名和唯一鍵
        assert "StockDailyItem" in repr_str
        unique_key = item.get_unique_key()
        # 驗證 repr 包含 symbol 和 date（雖然格式可能因 dataclass 而異）
        assert "2330" in repr_str or unique_key in repr_str
    
    def test_item_registry(self):
        """測試 Item 註冊表"""
        assert get_item_class("stock_daily") == StockDailyItem
        assert get_item_class("tpex_cb_daily") == TpexCbDailyItem
        assert get_item_class("stock_master") == StockMasterItem
        assert get_item_class("cb_master") == CbMasterItem
        assert get_item_class("unknown") is None
    
    def test_item_from_dict(self):
        """測試從字典創建 Item"""
        data = {
            "symbol": "2330",
            "date": "2026-01-01",
            "open_price": 100.0,
            "close_price": 105.0,
            "high_price": 106.0,
            "low_price": 99.0,
            "volume": 1000000,
            "extra_field": "should be ignored"
        }
        
        item = StockDailyItem.from_dict(data)
        
        assert item.symbol == "2330"
        assert item.date == "2026-01-01"
        assert item.open_price == 100.0
        assert item.close_price == 105.0
        assert not hasattr(item, "extra_field") or getattr(item, "extra_field", None) is None
