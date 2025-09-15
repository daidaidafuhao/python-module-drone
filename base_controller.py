# -*- coding: utf-8 -*-
"""
基础控制器模块
提供公共的状态检查和错误处理功能
"""

import time
from typing import Optional, Any
from loguru import logger
from modbus_client import modbus_client
from config import OPERATION_CODES


class BaseController:
    """基础控制器类，提供公共功能"""
    
    def __init__(self):
        pass
    
    def check_plc_connection(self) -> bool:
        """检查PLC连接状态
        
        Returns:
            bool: 连接状态
        """
        if not modbus_client.check_connection():
            logger.error("PLC连接异常")
            return False
        return True
    
    def read_register_with_retry(self, register_name: str, max_retries: int = 3) -> Optional[int]:
        """带重试的寄存器读取
        
        Args:
            register_name: 寄存器名称
            max_retries: 最大重试次数
            
        Returns:
            Optional[int]: 读取的值，失败返回None
        """
        for attempt in range(max_retries):
            try:
                value = modbus_client.read_register_by_name(register_name)
                if value is not None:
                    return value
                logger.warning(f"读取寄存器 {register_name} 失败，尝试 {attempt + 1}/{max_retries}")
            except Exception as e:
                logger.error(f"读取寄存器 {register_name} 异常: {e}，尝试 {attempt + 1}/{max_retries}")
            
            if attempt < max_retries - 1:
                time.sleep(0.5)  # 重试间隔
        
        logger.error(f"读取寄存器 {register_name} 最终失败")
        return None
    
    def write_register_with_retry(self, register_name: str, value: int, max_retries: int = 3) -> bool:
        """带重试的寄存器写入
        
        Args:
            register_name: 寄存器名称
            value: 要写入的值
            max_retries: 最大重试次数
            
        Returns:
            bool: 写入是否成功
        """
        for attempt in range(max_retries):
            try:
                if modbus_client.write_register_by_name(register_name, value):
                    return True
                logger.warning(f"写入寄存器 {register_name} 失败，尝试 {attempt + 1}/{max_retries}")
            except Exception as e:
                logger.error(f"写入寄存器 {register_name} 异常: {e}，尝试 {attempt + 1}/{max_retries}")
            
            if attempt < max_retries - 1:
                time.sleep(0.5)  # 重试间隔
        
        logger.error(f"写入寄存器 {register_name} 最终失败")
        return False
    
    def wait_for_status_change(self, register_name: str, expected_values: list, 
                              timeout: int = 30, check_interval: float = 0.5) -> Optional[int]:
        """等待状态变化
        
        Args:
            register_name: 寄存器名称
            expected_values: 期望的值列表
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）
            
        Returns:
            Optional[int]: 匹配的值，超时返回None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_value = self.read_register_with_retry(register_name, max_retries=1)
            
            if current_value is not None and current_value in expected_values:
                return current_value
            
            time.sleep(check_interval)
        
        logger.warning(f"等待寄存器 {register_name} 状态变化超时")
        return None
    
    def validate_operation_code(self, code: Any, valid_codes: list) -> bool:
        """验证操作码
        
        Args:
            code: 要验证的代码
            valid_codes: 有效代码列表
            
        Returns:
            bool: 验证结果
        """
        if code not in valid_codes:
            logger.error(f"无效的操作码: {code}，有效值: {valid_codes}")
            return False
        return True
    
    def log_operation_start(self, operation_name: str, **kwargs):
        """记录操作开始
        
        Args:
            operation_name: 操作名称
            **kwargs: 额外参数
        """
        params_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        logger.info(f"开始执行{operation_name}操作" + (f"，参数: {params_str}" if params_str else ""))
    
    def log_operation_result(self, operation_name: str, success: bool, message: str = ""):
        """记录操作结果
        
        Args:
            operation_name: 操作名称
            success: 是否成功
            message: 附加消息
        """
        status = "成功" if success else "失败"
        log_message = f"{operation_name}操作{status}"
        if message:
            log_message += f": {message}"
        
        if success:
            logger.info(log_message)
        else:
            logger.error(log_message)