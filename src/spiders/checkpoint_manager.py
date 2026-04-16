"""
CheckpointManager - 斷點管理器

功能：
- 記錄已完成的任務
- 支援斷點續傳
- 追蹤進度
"""
from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    斷點管理器
    
    用於批次任務的斷點續傳，記錄已完成和失敗的項目。
    
    Attributes:
        checkpoint_file: 斷點檔案路徑
        data: 斷點資料
        completed_keys: 已完成的 key 集合
        failed_keys: 失敗的 key 集合
    """
    
    DEFAULT_DATA = {
        "task_id": "",
        "created_at": "",
        "updated_at": "",
        "status": "pending",
        "progress": {
            "total": 0,
            "completed": 0,
            "failed": 0
        },
        "completed_keys": [],
        "failed_keys": [],
        "last_processed": None
    }
    
    def __init__(self, checkpoint_file: str):
        """
        初始化 CheckpointManager
        
        Args:
            checkpoint_file: 斷點檔案路徑
        """
        self.checkpoint_file = checkpoint_file
        self.data = self._load()
        self._completed_set: Set[str] = set(self.data.get("completed_keys", []))
        self._failed_dict: Dict[str, str] = {
            item["key"]: item["error"] 
            for item in self.data.get("failed_keys", [])
            if "key" in item
        }
        
        logger.info(f"CheckpointManager initialized: {checkpoint_file}")
    
    def _load(self) -> Dict[str, Any]:
        """
        載入斷點檔案
        
        Returns:
            斷點資料字典
        """
        if Path(self.checkpoint_file).exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded checkpoint: {len(data.get('completed_keys', []))} completed")
                return data
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load checkpoint: {e}, using default")
        
        return self._create_default()
    
    def _create_default(self) -> Dict[str, Any]:
        """建立預設斷點"""
        return {
            **self.DEFAULT_DATA,
            "task_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    def is_completed(self, key: str) -> bool:
        """
        檢查 key 是否已完成
        
        Args:
            key: 任務 key
        
        Returns:
            True if completed
        """
        return key in self._completed_set
    
    def is_failed(self, key: str) -> bool:
        """
        檢查 key 是否已失敗
        
        Args:
            key: 任務 key
        
        Returns:
            True if failed
        """
        return key in self._failed_dict
    
    def mark_completed(self, key: str, metadata: Dict[str, Any] = None) -> None:
        """
        標記 key 為已完成
        
        Args:
            key: 任務 key
            metadata: 額外元資料
        """
        if key not in self._completed_set:
            self._completed_set.add(key)
            self.data["completed_keys"].append(key)
            self.data["progress"]["completed"] = len(self._completed_set)
            self.data["updated_at"] = datetime.now().isoformat()
            
            if metadata:
                self.data["last_processed"] = {
                    "key": key,
                    "metadata": metadata
                }
            
            logger.debug(f"Marked completed: {key}")
    
    def mark_failed(self, key: str, error: str) -> None:
        """
        標記 key 為失敗
        
        Args:
            key: 任務 key
            error: 錯誤訊息
        """
        if key not in self._failed_dict:
            self._failed_dict[key] = error
            self.data["failed_keys"].append({
                "key": key,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            self.data["progress"]["failed"] = len(self._failed_dict)
            self.data["updated_at"] = datetime.now().isoformat()
            
            logger.warning(f"Marked failed: {key} - {error}")
    
    def get_pending(self, all_keys: List[str]) -> List[str]:
        """
        取得待處理的 keys（排除已完成和失敗的）
        
        Args:
            all_keys: 所有 key 清單
        
        Returns:
            待處理的 key 清單
        """
        pending = [
            key for key in all_keys
            if not self.is_completed(key) and not self.is_failed(key)
        ]
        logger.info(f"Pending: {len(pending)} of {len(all_keys)} keys")
        return pending
    
    def get_progress(self) -> Dict[str, Any]:
        """
        取得進度資訊
        
        Returns:
            進度字典
        """
        total = self.data["progress"]["total"]
        completed = self.data["progress"]["completed"]
        failed = self.data["progress"]["failed"]
        pending = total - completed - failed if total > 0 else 0
        
        return {
            "status": self.data["status"],
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_pct": (completed / total * 100) if total > 0 else 0
        }
    
    def set_status(self, status: str) -> None:
        """
        設定任務狀態
        
        Args:
            status: 狀態 (pending/running/completed/failed)
        """
        self.data["status"] = status
        self.data["updated_at"] = datetime.now().isoformat()
    
    def set_total(self, total: int) -> None:
        """設定總任務數"""
        self.data["progress"]["total"] = total
        self.data["updated_at"] = datetime.now().isoformat()
    
    def save(self) -> None:
        """保存斷點到檔案"""
        try:
            Path(self.checkpoint_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Checkpoint saved: {self.checkpoint_file}")
        except IOError as e:
            logger.error(f"Failed to save checkpoint: {e}")
            raise
    
    def reset(self) -> None:
        """重置斷點"""
        self.data = self._create_default()
        self._completed_set.clear()
        self._failed_dict.clear()
        logger.info("Checkpoint reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """取得摘要"""
        return {
            "task_id": self.data["task_id"],
            "status": self.data["status"],
            "created_at": self.data["created_at"],
            "updated_at": self.data["updated_at"],
            "total": self.data["progress"]["total"],
            "completed": self.data["progress"]["completed"],
            "failed": self.data["progress"]["failed"],
            "success_rate": (
                self.data["progress"]["completed"] / 
                max(1, self.data["progress"]["completed"] + self.data["progress"]["failed"]) * 100
            )
        }
    
    def __repr__(self) -> str:
        return f"<CheckpointManager completed={len(self._completed_set)} failed={len(self._failed_dict)}>"
