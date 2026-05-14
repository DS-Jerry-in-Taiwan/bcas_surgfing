# Developer Prompt: Phase 4 批次處理遷移

## 角色

你是 Developer Agent，負責實作 Phase 4 的批次處理遷移任務。

## 專案路徑

```
~/projects/bcas_quant/
```

## 參考檔案

### Phase 1-3 成果
- `src/spiders/stock_daily_spider.py` - 日行情爬蟲
- `src/spiders/tpex_cb_daily_spider.py` - CB 日行情爬蟲
- `src/framework/pipelines.py` - Pipeline

### 原有批次邏輯
- `src/crawlers/daily/tpex_csv_batch_fetcher.py` - 原有批次抓取

## 實作任務

### Task 1: 建立 CheckpointManager

**檔案**: `src/spiders/checkpoint_manager.py`

```python
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class CheckpointManager:
    """斷點管理器"""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.data = self._load()
    
    def _load(self) -> Dict[str, Any]:
        """載入斷點"""
    
    def is_completed(self, key: str) -> bool:
        """檢查是否已完成"""
    
    def mark_completed(self, key: str, metadata: dict = None):
        """標記完成"""
    
    def mark_failed(self, key: str, error: str):
        """標記失敗"""
    
    def get_pending(self, all_keys: List[str]) -> List[str]:
        """取得待處理清單"""
    
    def save(self):
        """保存斷點"""
    
    def reset(self):
        """重置斷點"""
```

### Task 2: 建立 BatchSpider

**檔案**: `src/spiders/batch_spider.py`

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Type
import time

from src.framework.base_spider import BaseSpider
from src.spiders.checkpoint_manager import CheckpointManager

class BatchSpider:
    """批次爬蟲"""
    
    def __init__(
        self,
        spider_class: Type[BaseSpider],
        pipeline=None,
        checkpoint_file: Optional[str] = None,
        max_workers: int = 4,
        request_interval: float = 1.0
    ):
        self.spider_class = spider_class
        self.pipeline = pipeline
        self.checkpoint = CheckpointManager(checkpoint_file) if checkpoint_file else None
        self.max_workers = max_workers
        self.request_interval = request_interval
        self.results = []
    
    def _generate_keys(self, symbols: List[str], start_date: str, end_date: str) -> List[str]:
        """生成所有需要處理的 key"""
    
    def _fetch_single(self, key: str) -> Dict[str, Any]:
        """抓取單一 key"""
    
    def backfill(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        resume: bool = False
    ) -> Dict[str, Any]:
        """批次補檔"""
    
    def get_progress(self) -> Dict[str, Any]:
        """取得進度"""
```

### Task 3: 更新 __init__.py

**檔案**: `src/spiders/__init__.py`

```python
from .batch_spider import BatchSpider
from .checkpoint_manager import CheckpointManager

__all__ = [
    # ... existing ...
    "BatchSpider",
    "CheckpointManager",
]
```

### Task 4: 建立測試

**檔案**: `tests/test_framework/test_batch_spider.py`

```python
import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.spiders.batch_spider import BatchSpider
from src.spiders.checkpoint_manager import CheckpointManager

class TestCheckpointManager:
    def setup_method(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.manager = CheckpointManager(self.temp_file.name)
    
    def teardown_method(self):
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_initialization(self):
        assert self.manager is not None
    
    def test_mark_completed(self):
        self.manager.mark_completed("2330_2024-01-15")
        assert self.manager.is_completed("2330_2024-01-15")
    
    def test_get_pending(self):
        all_keys = ["2330_2024-01-15", "2330_2024-01-16", "2317_2024-01-15"]
        self.manager.mark_completed("2330_2024-01-15")
        pending = self.manager.get_pending(all_keys)
        assert len(pending) == 2

class TestBatchSpider:
    def setup_method(self):
        self.spider = BatchSpider(
            spider_class=Mock,
            checkpoint_file=None
        )
    
    def test_initialization(self):
        assert self.spider is not None
```

## 驗收標準

- [ ] CheckpointManager 正確讀寫斷點
- [ ] BatchSpider 批次補檔成功
- [ ] 斷點續傳正確過濾已完成項目
- [ ] CLI 可正常執行
- [ ] 所有單元測試通過

## 執行驗證

```bash
cd ~/projects/bcas_quant
PYTHONPATH=. .venv/bin/python -m pytest tests/test_framework/test_batch_spider.py -v
```

---

*Developer Prompt for Phase 4 - 最後更新：2026-04-16*
