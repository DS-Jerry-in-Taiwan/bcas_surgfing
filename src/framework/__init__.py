"""
Feapder Framework - 核心框架模組
"""
from .base_spider import BaseSpider, SpiderResponse
from .base_item import BaseItem, StockDailyItem, TpexCbDailyItem
from .pipelines import BasePipeline, PostgresPipeline, CsvPipeline
from .exceptions import FrameworkError, PipelineError, SpiderError

__all__ = [
    "BaseSpider",
    "SpiderResponse",
    "BaseItem",
    "StockDailyItem",
    "TpexCbDailyItem",
    "BasePipeline",
    "PostgresPipeline",
    "CsvPipeline",
    "FrameworkError",
    "PipelineError",
    "SpiderError",
]

__version__ = "1.0.0"
