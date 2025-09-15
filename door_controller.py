# -*- coding: utf-8 -*-
"""
舱门控制模块
实现舱门的开启和关闭功能
"""

import time
from typing import Optional
from loguru import logger
from modbus_client import modbus_client
from config import OPERATION_CODES


class DoorController:
    """舱门控制器类"""
    
    def __init__(self):
        self.register_name = 'DOOR_CONTROL'
        
    def open_door(self, position: int = None, timeout: int = 30, client=None) -> bool:
        """开启舱门
        
        Args:
            position: 舱门位置（可选）
            timeout: 超时时间（秒）
            client: ModbusClient实例，如果不提供则使用全局client
            
        Returns:
            bool: 操作是否成功
        """
        # 使用传入的client或全局client
        active_client = client if client is not None else modbus_client
        
        position_str = f"舱门{position}" if position else "舱门"
        logger.info(f"开始执行{position_str}开启操作")
        
        # 检查连接
        if not active_client.check_connection():
            logger.error("PLC连接异常，无法执行开门操作")
            return False
        
        try:
            # 1. 写入开门指令
            if not active_client.write_register_by_name(
                self.register_name, 
                OPERATION_CODES['DOOR_OPEN']
            ):
                logger.error("写入开门指令失败")
                return False
            
            logger.info(f"已发送{position_str}开启指令，等待开启完成...")
            
            # 2. 等待开门完成确认
            if active_client.wait_for_register_value(
                self.register_name,
                OPERATION_CODES['DOOR_OPEN_COMPLETE'],
                timeout
            ):
                logger.info(f"{position_str}开启完成")
                return True
            else:
                logger.error(f"{position_str}开启超时")
                return False
                
        except Exception as e:
            logger.error(f"开门操作异常: {e}")
            return False
    
    def close_door(self, position: int = None, timeout: int = 30, client=None) -> bool:
        """关闭舱门
        
        Args:
            position: 舱门位置（1-6）
            timeout: 超时时间（秒）
            client: ModbusClient实例，如果不提供则使用全局client
            
        Returns:
            bool: 操作是否成功
        """
        # 使用传入的client或全局client
        active_client = client if client is not None else modbus_client
        
        position_str = f"舱门{position}" if position else "舱门"
        logger.info(f"开始执行{position_str}关闭操作")
        
        # 检查连接
        if not active_client.check_connection():
            logger.error("PLC连接异常，无法执行关门操作")
            return False
        
        try:
            # 1. 写入关门指令
            if not active_client.write_register_by_name(
                self.register_name,
                OPERATION_CODES['DOOR_CLOSE']
            ):
                logger.error("写入关门指令失败")
                return False
            
            logger.info(f"已发送{position_str}关闭指令，等待关闭完成...")
            
            # 2. 等待关门完成确认
            if active_client.wait_for_register_value(
                self.register_name,
                OPERATION_CODES['DOOR_CLOSE_COMPLETE'],
                timeout
            ):
                logger.info(f"{position_str}关闭完成")
                return True
            else:
                logger.error(f"{position_str}关闭超时")
                return False
                
        except Exception as e:
            logger.error(f"关门操作异常: {e}")
            return False
    
    def get_door_status(self, position: int = None, client=None) -> Optional[str]:
        """获取舱门当前状态
        
        Args:
            position: 舱门位置（可选，用于兼容性）
            client: ModbusClient实例，如果不提供则使用全局client
            
        Returns:
            str: 舱门状态描述
        """
        # 使用传入的client或全局client
        active_client = client if client is not None else modbus_client
        
        try:
            status_value = active_client.read_register_by_name(self.register_name)
            
            if status_value is None:
                return None
            
            status_map = {
                0: "空闲状态",
                OPERATION_CODES['DOOR_OPEN']: "正在开门",
                OPERATION_CODES['DOOR_CLOSE']: "正在关门",
                OPERATION_CODES['DOOR_OPEN_COMPLETE']: "门已打开",
                OPERATION_CODES['DOOR_CLOSE_COMPLETE']: "门已关闭"
            }
            
            return status_map.get(status_value, f"未知状态: {status_value}")
            
        except Exception as e:
            logger.error(f"获取舱门状态异常: {e}")
            return None
    
    def is_door_open(self) -> Optional[bool]:
        """检查舱门是否已打开
        
        Returns:
            bool: True表示门已打开，False表示门已关闭，None表示状态未知
        """
        try:
            status_value = modbus_client.read_register_by_name(self.register_name)
            
            if status_value is None:
                return None
            
            return status_value == OPERATION_CODES['DOOR_OPEN_COMPLETE']
            
        except Exception as e:
            logger.error(f"检查舱门状态异常: {e}")
            return None
    
    def is_door_closed(self) -> Optional[bool]:
        """检查舱门是否已关闭
        
        Returns:
            bool: True表示门已关闭，False表示门已打开，None表示状态未知
        """
        try:
            status_value = modbus_client.read_register_by_name(self.register_name)
            
            if status_value is None:
                return None
            
            return status_value == OPERATION_CODES['DOOR_CLOSE_COMPLETE']
            
        except Exception as e:
            logger.error(f"检查舱门状态异常: {e}")
            return None
    
    def reset_door_status(self) -> bool:
        """重置舱门状态为空闲
        
        Returns:
            bool: 操作是否成功
        """
        try:
            return modbus_client.write_register_by_name(self.register_name, 0)
        except Exception as e:
            logger.error(f"重置舱门状态异常: {e}")
            return False


# 全局舱门控制器实例
door_controller = DoorController()