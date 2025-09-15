# -*- coding: utf-8 -*-
"""
配置管理器
支持数据库和文件混合配置管理
"""

import threading
import time
from typing import Dict, Any, Optional
import logging
from models.drone_cabinet import DroneCabinetDAO
from config import PLC_CONFIG, REGISTER_MAP

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器 - 混合数据库和文件配置"""
    
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
            self._db_configs = {}  # 数据库配置缓存
            self._file_configs = {}  # 文件配置缓存
            self._last_refresh = 0
            self._refresh_interval = 60  # 60秒刷新一次
            self._refresh_lock = threading.Lock()
            
            # 初始化配置
            self._load_file_configs()
            self._refresh_db_configs()
            
            self.initialized = True
    
    def _load_file_configs(self):
        """加载文件配置"""
        try:
            self._file_configs = {
                'PLC_CONFIG': PLC_CONFIG.copy(),
                'MODBUS_REGISTERS': REGISTER_MAP.copy()
            }
            logger.info("文件配置加载成功")
        except Exception as e:
            logger.error(f"加载文件配置失败: {e}")
            self._file_configs = {
                'PLC_CONFIG': {
                    'host': '127.0.0.1',
                    'port': 502,
                    'unit_id': 1,
                    'timeout': 3,
                    'retry_count': 3
                },
                'MODBUS_REGISTERS': {}
            }
    
    def _refresh_db_configs(self):
        """刷新数据库配置"""
        try:
            self._db_configs = DroneCabinetDAO.get_connection_configs()
            self._last_refresh = time.time()
            logger.info(f"数据库配置刷新成功，共加载 {len(self._db_configs)} 个机器配置")
        except Exception as e:
            logger.error(f"刷新数据库配置失败: {e}")
    
    def _ensure_fresh_config(self):
        """确保配置是最新的"""
        current_time = time.time()
        if current_time - self._last_refresh > self._refresh_interval:
            with self._refresh_lock:
                # 双重检查
                if current_time - self._last_refresh > self._refresh_interval:
                    self._refresh_db_configs()
    
    def get_machine_list(self) -> list:
        """获取所有可用机器列表"""
        self._ensure_fresh_config()
        machines = list(self._db_configs.keys())
        if not machines:
            machines = ['default']  # 默认机器
        return machines
    
    def get_plc_config(self, machine_name: str = 'default') -> Dict[str, Any]:
        """获取PLC配置（混合数据库和文件配置）"""
        self._ensure_fresh_config()
        
        # 从文件配置开始
        config = self._file_configs['PLC_CONFIG'].copy()
        
        # 如果是默认机器且没有数据库配置，直接返回文件配置
        if machine_name == 'default' and not self._db_configs:
            return config
        
        # 尝试从数据库获取连接配置
        if machine_name in self._db_configs:
            db_config = self._db_configs[machine_name]
            # 数据库配置覆盖文件配置中的连接信息
            config.update({
                'host': db_config['host'],
                'port': db_config['port'],
                'unit_id': db_config['unit_id']
            })
            logger.debug(f"使用机器 {machine_name} 的数据库配置: {db_config}")
        elif machine_name != 'default':
            logger.warning(f"未找到机器 {machine_name} 的配置，使用默认配置")
        
        return config
    
    def get_modbus_registers(self) -> Dict[str, Any]:
        """获取Modbus寄存器配置（来自文件）"""
        return self._file_configs['MODBUS_REGISTERS'].copy()
    
    def is_machine_available(self, machine_name: str) -> bool:
        """检查机器是否可用"""
        self._ensure_fresh_config()
        
        if machine_name == 'default':
            return True
        
        if machine_name in self._db_configs:
            status = self._db_configs[machine_name].get('status', 0)
            return status in [1, 2]  # 在线或故障状态都认为可用
        
        return False
    
    def get_machine_status(self, machine_name: str) -> int:
        """获取机器状态"""
        self._ensure_fresh_config()
        
        if machine_name == 'default':
            return 1  # 默认机器始终在线
        
        if machine_name in self._db_configs:
            return self._db_configs[machine_name].get('status', 0)
        
        return 0  # 未知机器视为离线
    
    def refresh_config(self):
        """手动刷新配置"""
        with self._refresh_lock:
            self._refresh_db_configs()
            logger.info("配置已手动刷新")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有机器的完整配置"""
        self._ensure_fresh_config()
        
        all_configs = {}
        
        # 添加默认配置
        all_configs['default'] = {
            'plc_config': self.get_plc_config('default'),
            'modbus_registers': self.get_modbus_registers(),
            'status': 1,
            'available': True
        }
        
        # 添加数据库中的机器配置
        for machine_name in self._db_configs.keys():
            all_configs[machine_name] = {
                'plc_config': self.get_plc_config(machine_name),
                'modbus_registers': self.get_modbus_registers(),
                'status': self.get_machine_status(machine_name),
                'available': self.is_machine_available(machine_name)
            }
        
        return all_configs
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息"""
        self._ensure_fresh_config()
        
        return {
            'total_machines': len(self._db_configs) + 1,  # +1 for default
            'db_machines': len(self._db_configs),
            'available_machines': len([m for m in self._db_configs.keys() if self.is_machine_available(m)]) + 1,
            'last_refresh': self._last_refresh,
            'refresh_interval': self._refresh_interval,
            'machine_list': self.get_machine_list()
        }

# 全局配置管理器实例
config_manager = ConfigManager()