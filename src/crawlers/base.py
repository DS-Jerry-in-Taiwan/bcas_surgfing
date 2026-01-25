from abc import ABC, abstractmethod
import time
import threading
from functools import wraps

class RateLimiter:
    def __init__(self, calls_per_sec=1):
        self.lock = threading.Lock()
        self.calls_per_sec = calls_per_sec
        self.last_call = 0

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.lock:
                elapsed = time.time() - self.last_call
                wait = max(0, 1.0 / self.calls_per_sec - elapsed)
                if wait > 0:
                    time.sleep(wait)
                result = func(*args, **kwargs)
                self.last_call = time.time()
                return result
        return wrapper

class BaseCrawler(ABC):
    @abstractmethod
    def fetch(self, url, params=None):
        pass

    @abstractmethod
    def parse(self, response):
        pass

    @abstractmethod
    def save(self, data, filename):
        pass