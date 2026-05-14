# Phase 4 實作計畫

## 1. BatchSpider 架構

```python
class BatchSpider:
    """
    批次抓取爬蟲
    
    功能：
    - 全市場歷史資料補檔
    - 斷點續傳
    - 並發控制
    """
    
    def __init__(self, spider_class, checkpoint_file=None):
        self.spider_class = spider_class
        self.checkpoint = CheckpointManager(checkpoint_file)
        self.results = []
    
    def backfill(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        max_workers: int = 4
    ):
        """批次補檔"""
        
    def resume(self):
        """從斷點續傳"""
    
    def save_checkpoint(self):
        """保存斷點"""
    
    def get_progress(self):
        """取得進度"""
```

## 2. Checkpoint 機制

### 2.1 斷點儲存格式

```json
{
  "task_id": "batch_20240115_001",
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T12:30:00",
  "status": "running",
  "progress": {
    "total": 1000,
    "completed": 450,
    "failed": 10
  },
  "completed_keys": [
    {"symbol": "2330", "date": "2024-01-15"},
    {"symbol": "2330", "date": "2024-01-16"}
  ],
  "failed_keys": [
    {"symbol": "2317", "date": "2024-01-15", "error": "timeout"}
  ],
  "last_processed": {
    "symbol": "2317",
    "date": "2024-01-16"
  }
}
```

### 2.2 CheckpointManager 類

```python
class CheckpointManager:
    """斷點管理器"""
    
    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.data = self._load()
    
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

## 3. 並發控制

### 3.1 策略

- 使用 `concurrent.futures.ThreadPoolExecutor`
- 控制並發數 (max_workers=4)
- 請求間隔 (1 秒)
- 失敗重試 (最多 3 次)

### 3.2 實現

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_fetch(self, symbols, start_date, end_date, max_workers=4):
    tasks = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for symbol in symbols:
            future = executor.submit(self._fetch_symbol, symbol, start_date, end_date)
            tasks.append(future)
        
        for future in as_completed(tasks):
            result = future.result()
            self._process_result(result)
```

## 4. 實作步驟

### Step 1: 建立 BatchSpider 框架 (2 小時)
- `src/spiders/batch_spider.py`
- 實現批次抓取邏輯

### Step 2: 實作 CheckpointManager (2 小時)
- `src/spiders/checkpoint_manager.py`
- 實現斷點讀寫

### Step 3: 整合 Phase 3 Spider (1 小時)
- 整合 StockDailySpider
- 整合 TpexCbDailySpider

### Step 4: CLI 介面 (1 小時)
- `--backfill` 批次模式
- `--resume` 斷點續傳
- `--workers` 並發數

### Step 5: 單元測試 (2 小時)
- `tests/test_framework/test_batch_spider.py`

---

## 5. 使用範例

```bash
# 批次補檔
python -m src.spiders.batch_spider --backfill \
    --symbols 2330,2317,2454 \
    --start 2023-01-01 \
    --end 2023-12-31 \
    --workers 4

# 從斷點續傳
python -m src.spiders.batch_spider --resume \
    --checkpoint data/checkpoints/batch_20240115.json

# 查看進度
python -m src.spiders.batch_spider --progress \
    --checkpoint data/checkpoints/batch_20240115.json
```

---

*最後更新：2026-04-16*
