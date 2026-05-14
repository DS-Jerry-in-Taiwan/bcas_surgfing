"""Phase 3.0 Item 類別與 ITEM_REGISTRY 測試"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.framework.base_item import (
    BrokerBreakdownItem,
    DailyAnalysisResultItem,
    TradingSignalItem,
    ITEM_REGISTRY,
    get_item_class,
)


class TestBrokerBreakdownItem:
    """BrokerBreakdownItem 測試"""

    def test_instantiation(self):
        item = BrokerBreakdownItem(
            date="20260509", symbol="2330", broker_id="9200",
            broker_name="凱基-台北", buy_volume=100, sell_volume=10,
            net_volume=90
        )
        assert item.date == "20260509"
        assert item.symbol == "2330"
        assert item.net_volume == 90
        assert item.buy_volume == 100
        assert item.sell_volume == 10
        assert item.broker_name == "凱基-台北"

    def test_unique_key(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        assert item.get_unique_key() == "20260509_2330_9200"

    def test_to_dict(self):
        item = BrokerBreakdownItem(
            date="20260509", symbol="2330", broker_id="9200",
            broker_name="凱基-台北"
        )
        d = item.to_dict()
        assert d["date"] == "20260509"
        assert d["symbol"] == "2330"
        assert d["broker_id"] == "9200"
        assert d["broker_name"] == "凱基-台北"

    def test_to_dict_skips_metadata_timestamps(self):
        """to_dict() 不包含 metadata, created_at, updated_at"""
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        d = item.to_dict()
        assert "metadata" not in d
        assert "created_at" not in d
        assert "updated_at" not in d

    def test_validate_valid(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        assert item.validate() is True

    def test_validate_missing_date(self):
        item = BrokerBreakdownItem(date="", symbol="2330", broker_id="9200")
        assert item.validate() is False

    def test_validate_missing_symbol(self):
        item = BrokerBreakdownItem(date="20260509", symbol="", broker_id="9200")
        assert item.validate() is False

    def test_validate_missing_broker_id(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="")
        assert item.validate() is False

    def test_repr(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        r = repr(item)
        assert "BrokerBreakdownItem" in r
        assert "date='20260509'" in r
        assert "symbol='2330'" in r
        assert "broker_id='9200'" in r

    def test_default_rank(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        assert item.rank == 0

    def test_default_volumes_zero(self):
        item = BrokerBreakdownItem(date="20260509", symbol="2330", broker_id="9200")
        assert item.buy_volume == 0
        assert item.sell_volume == 0
        assert item.net_volume == 0


class TestDailyAnalysisResultItem:
    """DailyAnalysisResultItem 測試"""

    def test_instantiation(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="2330")
        assert item.date == "2026-05-11"
        assert item.symbol == "2330"
        assert item.premium_ratio == 0.0
        assert item.is_junk is False

    def test_unique_key(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="2330")
        assert item.get_unique_key() == "2026-05-11_2330"

    def test_to_dict(self):
        item = DailyAnalysisResultItem(
            date="2026-05-11", symbol="2330",
            close_price=150.0, premium_ratio=0.05,
            risk_score=3.5, risk_level="MEDIUM"
        )
        d = item.to_dict()
        assert d["date"] == "2026-05-11"
        assert d["symbol"] == "2330"
        assert d["close_price"] == 150.0
        assert d["premium_ratio"] == 0.05
        assert d["risk_score"] == 3.5
        assert d["risk_level"] == "MEDIUM"

    def test_validate_valid(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="2330")
        assert item.validate() is True

    def test_validate_missing_date(self):
        item = DailyAnalysisResultItem(date="", symbol="2330")
        assert item.validate() is False

    def test_validate_missing_symbol(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="")
        assert item.validate() is False

    def test_is_junk_default_false(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="2330")
        assert item.is_junk is False

    def test_is_junk_set_true(self):
        item = DailyAnalysisResultItem(date="2026-05-11", symbol="2330", is_junk=True)
        assert item.is_junk is True


class TestTradingSignalItem:
    """TradingSignalItem 測試"""

    def test_instantiation(self):
        item = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="BUY")
        assert item.signal_type == "BUY"
        assert item.date == "2026-05-11"
        assert item.symbol == "3680"

    def test_unique_key(self):
        item = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="BUY")
        assert item.get_unique_key() == "2026-05-11_3680_BUY"

    def test_to_dict(self):
        item = TradingSignalItem(
            date="2026-05-11", symbol="3680", signal_type="BUY",
            confidence=0.85, entry_range="105-110",
            stop_loss=98.5, target_price=125.0
        )
        d = item.to_dict()
        assert d["signal_type"] == "BUY"
        assert d["confidence"] == 0.85
        assert d["entry_range"] == "105-110"
        assert d["stop_loss"] == 98.5
        assert d["target_price"] == 125.0

    def test_validate_valid(self):
        item = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="BUY")
        assert item.validate() is True

    def test_validate_missing_date(self):
        item = TradingSignalItem(date="", symbol="3680", signal_type="BUY")
        assert item.validate() is False

    def test_validate_missing_symbol(self):
        item = TradingSignalItem(date="2026-05-11", symbol="", signal_type="BUY")
        assert item.validate() is False

    def test_validate_missing_signal_type(self):
        item = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="")
        assert item.validate() is False

    def test_default_confidence_zero(self):
        item = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="BUY")
        assert item.confidence == 0.0

    def test_unique_key_with_different_symbols(self):
        """不同 symbol 產生不同 unique key"""
        item1 = TradingSignalItem(date="2026-05-11", symbol="2330", signal_type="BUY")
        item2 = TradingSignalItem(date="2026-05-11", symbol="3680", signal_type="BUY")
        assert item1.get_unique_key() != item2.get_unique_key()

    def test_unique_key_with_different_types(self):
        """不同 signal_type 產生不同 unique key"""
        item1 = TradingSignalItem(date="2026-05-11", symbol="2330", signal_type="BUY")
        item2 = TradingSignalItem(date="2026-05-11", symbol="2330", signal_type="HOLD")
        assert item1.get_unique_key() != item2.get_unique_key()


class TestBrokerBreakdownItemFromDict:
    """BrokerBreakdownItem.from_dict() 測試"""

    def test_from_dict_basic(self):
        data = {
            "date": "20260509",
            "symbol": "2330",
            "broker_id": "9200",
            "broker_name": "凱基-台北",
            "buy_volume": 100,
            "sell_volume": 10,
            "net_volume": 90,
            "rank": 1,
        }
        item = BrokerBreakdownItem.from_dict(data)
        assert item.date == "20260509"
        assert item.broker_name == "凱基-台北"
        assert item.buy_volume == 100

    def test_from_dict_ignores_unknown_fields(self):
        data = {
            "date": "20260509",
            "symbol": "2330",
            "broker_id": "9200",
            "unknown_field": "should_be_ignored",
        }
        item = BrokerBreakdownItem.from_dict(data)
        assert item.date == "20260509"
        # unknown_field is filtered out by from_dict


class TestITEMREGISTRY:
    """ITEM_REGISTRY 測試"""

    def test_registry_has_7_items(self):
        assert len(ITEM_REGISTRY) == 7

    def test_has_new_items(self):
        assert "broker_breakdown" in ITEM_REGISTRY
        assert "daily_analysis_results" in ITEM_REGISTRY
        assert "trading_signals" in ITEM_REGISTRY

    def test_no_security_profile(self):
        assert "security_profile" not in ITEM_REGISTRY

    def test_get_item_class_success(self):
        cls = get_item_class("broker_breakdown")
        assert cls == BrokerBreakdownItem

        cls = get_item_class("daily_analysis_results")
        assert cls == DailyAnalysisResultItem

        cls = get_item_class("trading_signals")
        assert cls == TradingSignalItem

    def test_get_item_class_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_item_class("security_profile")

    def test_get_item_class_raises_keyerror_unknown(self):
        with pytest.raises(KeyError):
            get_item_class("nonexistent_table")

    def test_registry_has_existing_items(self):
        assert "stock_daily" in ITEM_REGISTRY
        assert "cb_master" in ITEM_REGISTRY
        assert "stock_master" in ITEM_REGISTRY
        assert "tpex_cb_daily" in ITEM_REGISTRY
