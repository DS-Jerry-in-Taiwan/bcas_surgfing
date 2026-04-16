"""
Feapder Framework - 自定義例外
"""


class FrameworkError(Exception):
    """框架基礎例外"""
    pass


class SpiderError(FrameworkError):
    """爬蟲相關例外"""
    pass


class PipelineError(FrameworkError):
    """Pipeline 相關例外"""
    pass


class ProxyError(SpiderError):
    """Proxy 相關例外"""
    pass


class RateLimitError(SpiderError):
    """速率限制例外"""
    pass


class ItemValidationError(FrameworkError):
    """Item 驗證例外"""
    pass


class DatabaseError(PipelineError):
    """資料庫相關例外"""
    pass
