# -*- coding: utf-8 -*-
"""
机器管理器
支持多机器连接管理和操作
"""

import threading
import time
from typing import Dict, Optional, Any
import logging
from modbus_client import ModbusClient
from services.config_manager import config_manager
from models.drone_cabinet import DroneCabinetDAO, DroneCabinetLogDAO, DroneCabinetLog
from datetime import datetime

logger = logging.getLogger(__name__)

class MachineConnection:
    """机器连接封装"""
    
    def __init__(self, machine_name: str, config: Dict[str, Any]):
        self.machine_name = machine_name
        self.config = config
        self.client = None
        self.last_used = time.time()
        self.connection_count = 0
        self.error_count = 0
        self.last_error = None
        self._lock = threading.Lock()
    
    def get_client(self) -> Optional[ModbusClient]:
        """获取Modbus客户端"""
        with self._lock:
            try:
                if self.client is None:
                    self.client = ModbusClient(
                        host=self.config['host'],
                        port=self.config['port'],
                        unit_id=self.config.get('unit_id', 1),
                        timeout=self.config.get('timeout', 3),
                        retry_count=self.config.get('retry_count', 3)
                    )
                    logger.info(f"为机器 {self.machine_name} 创建Modbus客户端")
                
                # 测试连接
                if self.client.connect():
                    self.last_used = time.time()
                    self.connection_count += 1
                    self.error_count = 0
                    return self.client
                else:
                    self.error_count += 1
                    self.last_error = "连接失败"
                    logger.error(f"机器 {self.machine_name} 连接失败")
                    return None
                    
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                logger.error(f"机器 {self.machine_name} 获取客户端失败: {e}")
                return None
    
    def disconnect(self):
        """断开连接"""
        with self._lock:
            if self.client:
                try:
                    self.client.disconnect()
                    logger.info(f"机器 {self.machine_name} 连接已断开")
                except Exception as e:
                    logger.error(f"机器 {self.machine_name} 断开连接失败: {e}")
                finally:
                    self.client = None
    
    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        # 错误率过高认为不健康
        if self.connection_count > 0:
            error_rate = self.error_count / (self.connection_count + self.error_count)
            return error_rate < 0.5
        return self.error_count < 5
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            'machine_name': self.machine_name,
            'config': self.config,
            'last_used': self.last_used,
            'connection_count': self.connection_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'is_healthy': self.is_healthy(),
            'connected': self.client is not None and self.client.is_connected
        }

class MachineManager:
    """机器管理器"""
    
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
            self._connections: Dict[str, MachineConnection] = {}
            self._connection_lock = threading.Lock()
            self._cleanup_interval = 300  # 5分钟清理一次
            self._last_cleanup = time.time()
            
            # 初始化连接
            self._initialize_connections()
            
            self.initialized = True
    
    def _initialize_connections(self):
        """初始化所有机器连接"""
        try:
            all_configs = config_manager.get_all_configs()
            
            with self._connection_lock:
                for machine_name, machine_config in all_configs.items():
                    if machine_config['available']:
                        plc_config = machine_config['plc_config']
                        self._connections[machine_name] = MachineConnection(machine_name, plc_config)
                        logger.info(f"初始化机器连接: {machine_name}")
            
            logger.info(f"机器管理器初始化完成，共管理 {len(self._connections)} 台机器")
            
        except Exception as e:
            logger.error(f"初始化机器连接失败: {e}")
    
    def get_machine_client(self, machine_name: str = 'default') -> Optional[ModbusClient]:
        """获取指定机器的Modbus客户端"""
        self._cleanup_idle_connections()
        
        with self._connection_lock:
            # 如果连接不存在，尝试创建
            if machine_name not in self._connections:
                if not self._create_connection(machine_name):
                    return None
            
            connection = self._connections.get(machine_name)
            if connection:
                client = connection.get_client()
                if client:
                    # 记录操作日志
                    self._log_operation(machine_name, "get_client", 1 if client else 0)
                return client
            
            return None
    
    def _create_connection(self, machine_name: str) -> bool:
        """创建新的机器连接"""
        try:
            if not config_manager.is_machine_available(machine_name):
                logger.warning(f"机器 {machine_name} 不可用")
                return False
            
            plc_config = config_manager.get_plc_config(machine_name)
            self._connections[machine_name] = MachineConnection(machine_name, plc_config)
            logger.info(f"创建机器连接: {machine_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建机器连接失败 {machine_name}: {e}")
            return False
    
    def disconnect_machine(self, machine_name: str):
        """断开指定机器连接"""
        with self._connection_lock:
            if machine_name in self._connections:
                self._connections[machine_name].disconnect()
                logger.info(f"机器 {machine_name} 连接已断开")
    
    def disconnect_all(self):
        """断开所有机器连接"""
        with self._connection_lock:
            for connection in self._connections.values():
                connection.disconnect()
            logger.info("所有机器连接已断开")
    
    def refresh_connections(self):
        """刷新所有连接"""
        logger.info("开始刷新机器连接")
        
        # 刷新配置
        config_manager.refresh_config()
        
        # 断开现有连接
        self.disconnect_all()
        
        # 清空连接池
        with self._connection_lock:
            self._connections.clear()
        
        # 重新初始化
        self._initialize_connections()
        
        logger.info("机器连接刷新完成")
    
    def _cleanup_idle_connections(self):
        """清理空闲连接"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._connection_lock:
            idle_machines = []
            for machine_name, connection in self._connections.items():
                # 超过10分钟未使用的连接视为空闲
                if current_time - connection.last_used > 600:
                    idle_machines.append(machine_name)
            
            for machine_name in idle_machines:
                self._connections[machine_name].disconnect()
                logger.info(f"清理空闲连接: {machine_name}")
            
            self._last_cleanup = current_time
    
    def get_machine_list(self) -> list:
        """获取所有可用机器列表"""
        return config_manager.get_machine_list()
    
    def get_machine_status(self, machine_name: str) -> Dict[str, Any]:
        """获取机器状态"""
        status = {
            'machine_name': machine_name,
            'available': config_manager.is_machine_available(machine_name),
            'config_status': config_manager.get_machine_status(machine_name),
            'connection_stats': None
        }
        
        with self._connection_lock:
            if machine_name in self._connections:
                status['connection_stats'] = self._connections[machine_name].get_stats()
        
        return status
    
    def get_all_machine_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有机器状态"""
        all_status = {}
        machine_list = self.get_machine_list()
        
        for machine_name in machine_list:
            all_status[machine_name] = self.get_machine_status(machine_name)
        
        return all_status
    
    def _log_operation(self, machine_name: str, operation_type: str, result: int, error_msg: str = None):
        """记录操作日志"""
        try:
            # 只为数据库中的机器记录日志
            if machine_name == 'default':
                return
            
            # 获取机器ID
            cabinet = DroneCabinetDAO.get_by_code(machine_name)
            if not cabinet:
                return
            
            log = DroneCabinetLog(
                cabinet_id=cabinet.id,
                operation_type=operation_type,
                operation_result=result,
                error_message=error_msg,
                operator='system',
                remark=f"机器管理器操作: {operation_type}"
            )
            
            DroneCabinetLogDAO.create_log(log)
            
        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
    
    def test_machine_connection(self, machine_name: str) -> Dict[str, Any]:
        """测试机器连接"""
        result = {
            'machine_name': machine_name,
            'success': False,
            'message': '',
            'response_time': 0,
            'error': None
        }
        
        start_time = time.time()
        
        try:
            client = self.get_machine_client(machine_name)
            if client:
                # 尝试读取一个寄存器来测试连接
                test_result = client.read_holding_registers(0, 1)
                if test_result:
                    result['success'] = True
                    result['message'] = '连接测试成功'
                else:
                    result['message'] = '连接测试失败：无法读取寄存器'
            else:
                result['message'] = '无法获取客户端连接'
                
        except Exception as e:
            result['error'] = str(e)
            result['message'] = f'连接测试异常: {e}'
        
        result['response_time'] = round((time.time() - start_time) * 1000, 2)  # 毫秒
        
        # 记录测试日志
        self._log_operation(
            machine_name, 
            'connection_test', 
            1 if result['success'] else 0,
            result.get('error') or result['message']
        )
        
        return result
    
    def get_connection(self, machine_name: str) -> Optional['MachineConnection']:
        """获取指定机器的连接对象"""
        self._cleanup_idle_connections()
        
        with self._connection_lock:
            # 如果连接不存在，尝试创建
            if machine_name not in self._connections:
                if not self._create_connection(machine_name):
                    return None
            
            connection = self._connections.get(machine_name)
            if connection:
                # 记录操作日志
                self._log_operation(machine_name, "get_connection", 1 if connection else 0)
            return connection
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        with self._connection_lock:
            total_connections = len(self._connections)
            healthy_connections = sum(1 for conn in self._connections.values() if conn.is_healthy())
            active_connections = sum(1 for conn in self._connections.values() 
                                   if conn.client and conn.client.is_connected())
        
        return {
            'total_machines': len(self.get_machine_list()),
            'total_connections': total_connections,
            'healthy_connections': healthy_connections,
            'active_connections': active_connections,
            'last_cleanup': self._last_cleanup,
            'cleanup_interval': self._cleanup_interval
        }

# 全局机器管理器实例
machine_manager = MachineManager()