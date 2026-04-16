"""
Feapder Framework - Pipelines
实现资料写入管道
"""
from __future__ import annotations

import os
import csv
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, Union
from datetime import datetime
from pathlib import Path

from .base_item import BaseItem
from .exceptions import PipelineError, DatabaseError

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """
    Pipeline 基底类
    
    Attributes:
        error_count: 错误计数
        success_count: 成功计数
        table_name: 表名
    """
    
    def __init__(self, table_name: Optional[str] = None):
        self.error_count: int = 0
        self.success_count: int = 0
        self.table_name: Optional[str] = table_name
        self._item_class: Optional[Type[BaseItem]] = None
    
    @abstractmethod
    def save_items(self, item: BaseItem) -> None:
        """
        保存 Item - 子类必须实作
        
        Args:
            item: BaseItem 实例
        """
        pass
    
    def item_to_dict(self, item: BaseItem) -> Dict[str, Any]:
        """
        将 Item 转换为 Dict
        
        Args:
            item: BaseItem 实例
        
        Returns:
            字典
        """
        return item.to_dict()
    
    def get_statistics(self) -> Dict[str, int]:
        """
        取得处理统计
        
        Returns:
            统计字典
        """
        return {
            "success": self.success_count,
            "errors": self.error_count,
            "total": self.success_count + self.error_count,
        }
    
    def record_success(self) -> None:
        """记录成功"""
        self.success_count += 1
    
    def record_error(self, error: Exception) -> None:
        """记录错误"""
        self.error_count += 1
        logger.error(f"Pipeline error: {error}")
    
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"success={self.success_count} errors={self.error_count}>"
        )


class CsvPipeline(BasePipeline):
    """
    CSV Pipeline（除错用）
    
    支持缓冲区和批量写出
    
    Attributes:
        output_dir: 输出目录
        batch_size: 批次大小
    """
    
    def __init__(
        self,
        output_dir: str = "data/output",
        batch_size: int = 1000,
        table_name: Optional[str] = None,
    ):
        super().__init__(table_name=table_name)
        self.output_dir = output_dir
        self.batch_size = batch_size
        self._buffers: Dict[str, List[Dict[str, Any]]] = {}
        
        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"CsvPipeline initialized: output_dir={output_dir}, batch_size={batch_size}")
    
    def save_items(self, item: BaseItem) -> None:
        """
        保存 Item 到 CSV
        
        Args:
            item: BaseItem 实例
        """
        try:
            item_dict = self.item_to_dict(item)
            table_name = getattr(item, "__table_name__", "default")
            
            if table_name not in self._buffers:
                self._buffers[table_name] = []
            
            self._buffers[table_name].append(item_dict)
            
            # 检查是否需要 flush
            if len(self._buffers[table_name]) >= self.batch_size:
                self._flush_table(table_name)
            
            self.record_success()
            
        except Exception as e:
            self.record_error(e)
            raise PipelineError(f"Failed to save item: {e}") from e
    
    def _flush_table(self, table_name: str) -> None:
        """写出指定表的缓冲区"""
        if table_name not in self._buffers or not self._buffers[table_name]:
            return
        
        records = self._buffers[table_name]
        filepath = Path(self.output_dir) / f"{table_name}.csv"
        
        try:
            file_exists = filepath.exists()
            
            with open(filepath, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerows(records)
            
            logger.info(f"Flushed {len(records)} records to {filepath}")
            self._buffers[table_name] = []
            
        except Exception as e:
            logger.error(f"Failed to flush {table_name}: {e}")
            raise PipelineError(f"Failed to flush: {e}") from e
    
    def flush_all(self) -> None:
        """写出所有缓冲区"""
        for table_name in list(self._buffers.keys()):
            self._flush_table(table_name)
        logger.info("All buffers flushed")
    
    def close(self) -> None:
        """关闭 Pipeline"""
        self.flush_all()
    
    def __del__(self) -> None:
        """析构时确保数据写出"""
        try:
            self.close()
        except Exception:
            pass


class PostgresPipeline(BasePipeline):
    """
    PostgreSQL Pipeline
    
    支持资料去重与错误处理
    
    Attributes:
        host: 数据库主机
        port: 端口
        database: 数据库名
        user: 用户名
        password: 密码
        batch_size: 批次大小
        unique_key: 唯一键字段
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 5432,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        table_name: Optional[str] = None,
        batch_size: int = 100,
        unique_key: str = "unique_key",
    ):
        super().__init__(table_name=table_name)
        
        # 从环境变量或参数取得连线资讯
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = database or os.getenv("POSTGRES_DB")
        self.user = user or os.getenv("POSTGRES_USER")
        self.password = password or os.getenv("POSTGRES_PASSWORD")
        self.batch_size = batch_size
        self.unique_key = unique_key
        
        self._conn = None
        self._cursor = None
        self._batch_buffer: List[Dict[str, Any]] = []
        
        logger.info(
            f"PostgresPipeline initialized: host={self.host}, "
            f"database={self.database}, batch_size={batch_size}"
        )
    
    def _get_connection(self):
        """取得或建立资料库连线"""
        if self._conn is None or self._conn.closed:
            try:
                import psycopg2
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                )
                self._cursor = self._conn.cursor()
                logger.info(f"Connected to PostgreSQL: {self.host}/{self.database}")
            except ImportError:
                raise DatabaseError(
                    "psycopg2 not installed. Run: pip install psycopg2-binary"
                )
            except Exception as e:
                raise DatabaseError(f"Failed to connect to PostgreSQL: {e}") from e
        
        return self._conn
    
    def _ensure_table(self, table_name: str, columns: Dict[str, str]) -> None:
        """
        确保资料表存在
        
        Args:
            table_name: 表名
            columns: 栏位定义 {name: type}
        """
        if not self._cursor:
            return
        
        # 构建 CREATE TABLE 语句
        col_defs = ", ".join([f"{name} {col_type}" for name, col_type in columns.items()])
        
        sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {col_defs},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        try:
            self._cursor.execute(sql)
            self._conn.commit()
            logger.info(f"Ensured table exists: {table_name}")
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to create table {table_name}: {e}")
            raise DatabaseError(f"Failed to create table: {e}") from e
    
    def save_items(self, item: BaseItem) -> None:
        """
        保存单笔 Item
        
        Args:
            item: BaseItem 实例
        """
        try:
            item_dict = self.item_to_dict(item)
            table_name = getattr(item, "__table_name__", self.table_name or "default")
            
            self._batch_buffer.append({
                "table_name": table_name,
                "data": item_dict,
                "unique_key": item.get_unique_key(),
            })
            
            if len(self._batch_buffer) >= self.batch_size:
                self._flush_batch()
            
            self.record_success()
            
        except Exception as e:
            self.record_error(e)
            raise PipelineError(f"Failed to save item: {e}") from e
    
    def _flush_batch(self) -> None:
        """批次写入缓冲区"""
        if not self._batch_buffer:
            return
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for record in self._batch_buffer:
                table_name = record["table_name"]
                data = record["data"]
                unique_key = record["unique_key"]
                
                columns = list(data.keys())
                values = list(data.values())
                placeholders = ", ".join(["%s"] * len(columns))
                
                # ON CONFLICT DO UPDATE 实现去重
                update_cols = [f"{col} = EXCLUDED.{col}" for col in columns if col != self.unique_key]
                
                sql = f"""
                    INSERT INTO {table_name} ({",".join(columns)}, {self.unique_key}, updated_at)
                    VALUES ({placeholders}, %s, NOW())
                    ON CONFLICT ({self.unique_key})
                    DO UPDATE SET {", ".join(update_cols)}, updated_at = NOW()
                """
                
                # 添加 unique_key 到 values
                final_values = values + [unique_key]
                cursor.execute(sql, final_values)
            
            conn.commit()
            logger.info(f"Flushed {len(self._batch_buffer)} items to database")
            self._batch_buffer.clear()
            
        except Exception as e:
            if self._conn and not self._conn.closed:
                self._conn.rollback()
            logger.error(f"Batch flush failed: {e}")
            raise DatabaseError(f"Batch flush failed: {e}") from e
    
    def close(self) -> None:
        """关闭连线"""
        if self._batch_buffer:
            self._flush_batch()
        
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
        
        if self._conn:
            try:
                self._conn.close()
                logger.info("PostgreSQL connection closed")
            except Exception:
                pass
    
    def __del__(self) -> None:
        """析构时确保关闭连线"""
        try:
            self.close()
        except Exception:
            pass


class MemoryPipeline(BasePipeline):
    """
    记忆体 Pipeline（测试用）
    
    将所有数据存储在内存中
    """
    
    def __init__(self):
        super().__init__()
        self.items: List[BaseItem] = []
        self.errors: List[Exception] = []
    
    def save_items(self, item: BaseItem) -> None:
        """保存 Item 到内存"""
        try:
            self.items.append(item)
            self.record_success()
        except Exception as e:
            self.errors.append(e)
            self.record_error(e)
    
    def get_items(self) -> List[BaseItem]:
        """取得所有 Items"""
        return self.items
    
    def clear(self) -> None:
        """清空内存"""
        self.items.clear()
        self.errors.clear()
        self.success_count = 0
        self.error_count = 0
    
    def close(self) -> None:
        """关闭 Pipeline"""
        pass
