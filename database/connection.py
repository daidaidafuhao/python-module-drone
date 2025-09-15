# -*- coding: utf-8 -*-
"""
数据库连接管理模块
提供MySQL数据库连接池和连接管理功能
"""

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
from typing import Optional, Dict, Any
import threading
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        self.host = 'localhost'
        self.port = 3306
        self.user = 'root'
        self.password = '123456'
        self.database = 'ruoyi-vue-pro'
        self.charset = 'utf8mb4'
        self.autocommit = True
        
        # 连接池配置
        self.pool_size = 10
        self.max_overflow = 20
        self.pool_timeout = 30
        self.pool_recycle = 3600

class ConnectionPool:
    """数据库连接池"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool = Queue(maxsize=config.pool_size + config.max_overflow)
        self._created_connections = 0
        self._lock = threading.Lock()
        
        # 预创建核心连接
        for _ in range(config.pool_size):
            conn = self._create_connection()
            if conn:
                self._pool.put(conn)
    
    def _create_connection(self) -> Optional[pymysql.Connection]:
        """创建数据库连接"""
        try:
            connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                autocommit=self.config.autocommit,
                cursorclass=DictCursor
            )
            
            with self._lock:
                self._created_connections += 1
            
            logger.info(f"创建数据库连接成功，当前连接数: {self._created_connections}")
            return connection
            
        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            return None
    
    def get_connection(self) -> Optional[pymysql.Connection]:
        """从连接池获取连接"""
        try:
            # 尝试从池中获取连接
            connection = self._pool.get(timeout=self.config.pool_timeout)
            
            # 检查连接是否有效
            if self._is_connection_valid(connection):
                return connection
            else:
                # 连接无效，创建新连接
                logger.warning("连接无效，创建新连接")
                return self._create_connection()
                
        except Empty:
            # 池中无可用连接，尝试创建新连接
            with self._lock:
                if self._created_connections < (self.config.pool_size + self.config.max_overflow):
                    return self._create_connection()
            
            logger.error("连接池已满，无法获取连接")
            return None
    
    def return_connection(self, connection: pymysql.Connection):
        """归还连接到连接池"""
        if connection and self._is_connection_valid(connection):
            try:
                self._pool.put_nowait(connection)
            except:
                # 池已满，关闭连接
                self._close_connection(connection)
        else:
            self._close_connection(connection)
    
    def _is_connection_valid(self, connection: pymysql.Connection) -> bool:
        """检查连接是否有效"""
        try:
            connection.ping(reconnect=False)
            return True
        except:
            return False
    
    def _close_connection(self, connection: pymysql.Connection):
        """关闭连接"""
        try:
            connection.close()
            with self._lock:
                self._created_connections -= 1
            logger.info(f"关闭数据库连接，当前连接数: {self._created_connections}")
        except Exception as e:
            logger.error(f"关闭连接失败: {e}")
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                connection = self._pool.get_nowait()
                self._close_connection(connection)
            except Empty:
                break

class DatabaseManager:
    """数据库管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.config = DatabaseConfig()
            self.pool = ConnectionPool(self.config)
            self.initialized = True
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        connection = None
        try:
            connection = self.pool.get_connection()
            if connection is None:
                raise Exception("无法获取数据库连接")
            yield connection
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise e
        finally:
            if connection:
                self.pool.return_connection(connection)
    
    def execute_query(self, sql: str, params: tuple = None) -> list:
        """执行查询SQL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return cursor.fetchall()
            finally:
                cursor.close()
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """执行更新SQL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                result = cursor.execute(sql, params)
                conn.commit()
                return result
            finally:
                cursor.close()
    
    def execute_batch(self, sql: str, params_list: list) -> int:
        """批量执行SQL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                result = cursor.executemany(sql, params_list)
                conn.commit()
                return result
            finally:
                cursor.close()
    
    def close(self):
        """关闭数据库管理器"""
        if hasattr(self, 'pool'):
            self.pool.close_all()

# 全局数据库管理器实例
db_manager = DatabaseManager()