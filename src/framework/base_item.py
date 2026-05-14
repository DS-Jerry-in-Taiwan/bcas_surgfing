"""
Feapder Framework - BaseItem
定義統一的資料傳輸結構
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from typing import Dict, Any, Optional, Type
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseItem(ABC):
    """
    Feapder Item 擴展基底類
    
    所有爬蟲 Item 應繼承此類
    
    Attributes:
        created_at: 創建時間
        updated_at: 更新時間
        source_url: 來源 URL
        source_type: 來源類型 (twse, tpex, etc.)
        metadata: 額外元數據
    """
    
    created_at: datetime
    updated_at: datetime
    source_url: str
    source_type: str
    metadata: Dict[str, Any]
    
    @abstractmethod
    def get_unique_key(self) -> str:
        """
        回傳唯一識別鍵，供去重使用
        
        Returns:
            唯一鍵字符串，格式: {field1}_{field2}
        """
        pass
    
    def update_timestamp(self) -> None:
        """更新 timestamp"""
        self.updated_at = datetime.now()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元數據"""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典
        
        Returns:
            包含所有非私有字段的字典
        """
        skip = {"metadata", "created_at", "updated_at"}
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if key in skip:
                continue
            if value is None:
                continue
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls: Type["BaseItem"], data: Dict[str, Any]) -> "BaseItem":
        """
        從字典創建 Item
        
        Args:
            data: 字典數據
        
        Returns:
            Item 實例
        """
        valid_fields = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def validate(self) -> bool:
        """
        驗證必要字段
        
        Returns:
            驗證是否通過
        """
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} unique_key={self.get_unique_key()}>"


def _default_datetime() -> datetime:
    return datetime.now()


@dataclass
class StockDailyItem(BaseItem):
    """
    股票日成交資料 Item
    
    Attributes:
        symbol: 股票代號
        date: 交易日期 (YYYY-MM-DD)
        open_price: 開盤價
        high_price: 最高價
        low_price: 最低價
        close_price: 收盤價
        volume: 成交量
        turnover_rate: 週轉率 (%)
        price_change: 價格變動
        transaction_count: 成交筆數
    """
    __table_name__: str = "stock_daily"
    
    symbol: str = ""
    date: str = ""
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0
    volume: int = 0
    turnover_rate: float = 0.0
    price_change: float = 0.0
    transaction_count: int = 0
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_key(self) -> str:
        return f"{self.symbol}_{self.date}"
    
    def validate(self) -> bool:
        """驗證必要字段"""
        return bool(self.symbol and self.date)


@dataclass
class TpexCbDailyItem(BaseItem):
    """
    TPEx 可轉債日成交資料 Item
    
    Attributes:
        cb_code: 可轉債代號
        cb_name: 可轉債名稱
        underlying_stock: 標的股票代號
        trade_date: 交易日期 (YYYY-MM-DD)
        closing_price: 收盤價
        volume: 成交量
        turnover_rate: 週轉率 (%)
        premium_rate: 溢價率 (%)
        conversion_price: 轉換價格
        remaining_balance: 餘額
    """
    __table_name__: str = "tpex_cb_daily"
    
    cb_code: str = ""
    cb_name: str = ""
    underlying_stock: str = ""
    trade_date: str = ""
    closing_price: float = 0.0
    volume: int = 0
    turnover_rate: float = 0.0
    premium_rate: float = 0.0
    conversion_price: float = 0.0
    remaining_balance: float = 0.0
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_key(self) -> str:
        return f"{self.cb_code}_{self.trade_date}"
    
    def validate(self) -> bool:
        """驗證必要字段"""
        return bool(self.cb_code and self.trade_date)


@dataclass
class StockMasterItem(BaseItem):
    """
    股票主檔資料 Item
    
    Attributes:
        symbol: 股票代號
        name: 股票名稱
        market_type: 市場類型 (TWSE/TPEx)
        industry: 產業類別
        listing_date: 上市日期
        cfi_code: CFI 代碼
    """
    __table_name__: str = "stock_master"
    
    symbol: str = ""
    name: str = ""
    market_type: str = ""
    industry: str = ""
    listing_date: str = ""
    cfi_code: str = ""
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_key(self) -> str:
        return f"{self.symbol}_{self.market_type}"
    
    def validate(self) -> bool:
        return bool(self.symbol and self.name)


@dataclass
class CbMasterItem(BaseItem):
    """
    可轉債主檔資料 Item
    
    Attributes:
        cb_code: 可轉債代號
        cb_name: 可轉債名稱
        underlying_stock: 標的股票代號
        market_type: 市場類型
        issue_date: 發行日期
        maturity_date: 到期日期
        conversion_price: 轉換價格
        coupon_rate: 票面利率
    """
    __table_name__: str = "cb_master"
    
    cb_code: str = ""
    cb_name: str = ""
    underlying_stock: str = ""
    market_type: str = ""
    issue_date: str = ""
    maturity_date: str = ""
    conversion_price: float = 0.0
    coupon_rate: float = 0.0
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_unique_key(self) -> str:
        return f"{self.cb_code}_{self.underlying_stock}"
    
    def validate(self) -> bool:
        return bool(self.cb_code and self.underlying_stock)


@dataclass
class BrokerBreakdownItem(BaseItem):
    """
    券商分點買賣超明細 Item

    Attributes:
        date: 交易日期 (YYYYMMDD)
        symbol: 股票代號
        broker_id: 券商代號
        broker_name: 券商名稱
        buy_volume: 買進股數
        sell_volume: 賣出股數
        net_volume: 淨買超股數
        rank: 排名 (1-10)
    """
    __table_name__: str = "broker_breakdown"

    date: str = ""
    symbol: str = ""
    broker_id: str = ""
    broker_name: str = ""
    buy_volume: int = 0
    sell_volume: int = 0
    net_volume: int = 0
    rank: int = 0
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}_{self.broker_id}"

    def validate(self) -> bool:
        return bool(self.date and self.symbol and self.broker_id)


@dataclass
class DailyAnalysisResultItem(BaseItem):
    """
    盤後分析結果 Item

    Attributes:
        date: 分析日期 (YYYY-MM-DD)
        symbol: 證券代號
        close_price: 收盤價
        conversion_value: 轉換價值
        premium_ratio: 溢價率
        technical_signal: 技術指標訊號
        risk_score: 風險評分
        risk_level: 風險等級
        broker_risk_pct: 券商風險佔比
        final_rating: 最終評級
        is_junk: 是否為垃圾債
        notes: 備註
    """
    __table_name__: str = "daily_analysis_results"

    date: str = ""
    symbol: str = ""
    close_price: float = 0.0
    conversion_value: float = 0.0
    premium_ratio: float = 0.0
    technical_signal: str = ""
    risk_score: float = 0.0
    risk_level: str = ""
    broker_risk_pct: float = 0.0
    final_rating: str = ""
    is_junk: bool = False
    notes: str = ""
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}"

    def validate(self) -> bool:
        return bool(self.date and self.symbol)


@dataclass
class TradingSignalItem(BaseItem):
    """
    交易信號 Item

    Attributes:
        date: 信號日期 (YYYY-MM-DD)
        symbol: 證券代號
        signal_type: 信號類型 (BUY / HOLD / AVOID)
        confidence: 信心度
        entry_range: 進場區間
        stop_loss: 停損價
        target_price: 目標價
        notes: 備註
    """
    __table_name__: str = "trading_signals"

    date: str = ""
    symbol: str = ""
    signal_type: str = ""  # BUY / HOLD / AVOID
    confidence: float = 0.0
    entry_range: str = ""
    stop_loss: float = 0.0
    target_price: float = 0.0
    notes: str = ""
    created_at: datetime = field(default_factory=_default_datetime)
    updated_at: datetime = field(default_factory=_default_datetime)
    source_url: str = ""
    source_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_unique_key(self) -> str:
        return f"{self.date}_{self.symbol}_{self.signal_type}"

    def validate(self) -> bool:
        return bool(self.date and self.symbol and self.signal_type)


ITEM_REGISTRY: Dict[str, Type[BaseItem]] = {
    "stock_daily": StockDailyItem,
    "tpex_cb_daily": TpexCbDailyItem,
    "stock_master": StockMasterItem,
    "cb_master": CbMasterItem,
    # ↓ Phase 3.0 新增
    "broker_breakdown": BrokerBreakdownItem,
    "daily_analysis_results": DailyAnalysisResultItem,
    "trading_signals": TradingSignalItem,
}


def get_item_class(table_name: str) -> Type[BaseItem]:
    """根據表名獲取 Item 類，不存在時拋 KeyError"""
    return ITEM_REGISTRY[table_name]
