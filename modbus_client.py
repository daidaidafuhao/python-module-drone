# -*- coding: utf-8 -*-
"""
Modbus通信客户端模块
用于与PLC设备进行通信
"""

import time
from typing import Optional, Union
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from loguru import logger
from config import PLC_CONFIG, REGISTER_MAP, OPERATION_CODES


class ModbusClient:
    """Modbus TCP客户端类"""
    
    def __init__(self, host=None, port=None, timeout=None, retry_count=None, unit_id=None):
        self.client = None
        self.is_connected = False
        self.host = host or PLC_CONFIG['host']
        self.port = port or PLC_CONFIG['port']
        self.timeout = timeout or PLC_CONFIG['timeout']
        self.retry_count = retry_count or PLC_CONFIG['retry_count']
        self.unit_id = unit_id or PLC_CONFIG['unit_id']
        
    def connect(self) -> bool:
        """连接到PLC设备"""
        try:
            self.client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )
            
            if self.client.connect():
                self.is_connected = True
                logger.info(f"成功连接到PLC设备 {self.host}:{self.port}")
                return True
            else:
                logger.error(f"无法连接到PLC设备 {self.host}:{self.port}")
                return False
                
        except Exception as e:
            logger.error(f"连接PLC设备时发生异常: {e}")
            return False
    
    def disconnect(self):
        """断开PLC连接"""
        if self.client and self.is_connected:
            self.client.close()
            self.is_connected = False
            logger.info("已断开PLC连接")
    
    def read_holding_register(self, address: int) -> Optional[int]:
        """读取保持寄存器"""
        if not self.is_connected:
            logger.error("PLC未连接")
            return None
            
        for attempt in range(self.retry_count):
            try:
                result = self.client.read_holding_registers(
                    address=address,
                    count=1,
                    device_id=self.unit_id
                )
                
                if not result.isError():
                    value = result.registers[0]
                    logger.debug(f"读取寄存器 0x{address:04X}: {value}")
                    return value
                else:
                    logger.warning(f"读取寄存器 0x{address:04X} 失败: {result}")
                    
            except ModbusException as e:
                logger.warning(f"读取寄存器 0x{address:04X} 异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(0.1)
                    
        logger.error(f"读取寄存器 0x{address:04X} 失败，已重试 {self.retry_count} 次")
        return None
    
    def read_holding_registers(self, address: int, count: int = 1, **kwargs) -> Optional[list]:
        """读取多个保持寄存器
        
        Args:
            address: 寄存器地址
            count: 读取数量
            **kwargs: 兼容其他参数（如unit, slave等），会被忽略
        """
        if not self.is_connected:
            logger.error("PLC未连接")
            return None
            
        # 忽略unit, slave等参数，使用实例的unit_id
        if 'unit' in kwargs or 'slave' in kwargs:
            logger.debug(f"忽略传入的unit/slave参数，使用配置的unit_id: {self.unit_id}")
            
        for attempt in range(self.retry_count):
            try:
                result = self.client.read_holding_registers(
                    address=address,
                    count=count,
                    device_id=self.unit_id
                )
                
                if not result.isError():
                    values = result.registers
                    logger.debug(f"读取寄存器 0x{address:04X}-0x{address+count-1:04X}: {values}")
                    return values
                else:
                    logger.warning(f"读取寄存器 0x{address:04X}-0x{address+count-1:04X} 失败: {result}")
                    
            except ModbusException as e:
                logger.warning(f"读取寄存器 0x{address:04X}-0x{address+count-1:04X} 异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(0.1)
                    
        logger.error(f"读取寄存器 0x{address:04X}-0x{address+count-1:04X} 失败，已重试 {self.retry_count} 次")
        return None
    
    def write_holding_register(self, address: int, value: int) -> bool:
        """写入保持寄存器"""
        if not self.is_connected:
            logger.error("PLC未连接")
            return False
            
        for attempt in range(self.retry_count):
            try:
                result = self.client.write_register(
                    address=address,
                    value=value,
                    device_id=self.unit_id
                )
                
                if not result.isError():
                    logger.debug(f"写入寄存器 0x{address:04X}: {value}")
                    return True
                else:
                    logger.warning(f"写入寄存器 0x{address:04X} 失败: {result}")
                    
            except ModbusException as e:
                logger.warning(f"写入寄存器 0x{address:04X} 异常 (尝试 {attempt + 1}/{self.retry_count}): {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(0.1)
                    
        logger.error(f"写入寄存器 0x{address:04X} 失败，已重试 {self.retry_count} 次")
        return False
    
    def read_register_by_name(self, register_name: str) -> Optional[int]:
        """通过寄存器名称读取数据"""
        if register_name not in REGISTER_MAP:
            logger.error(f"未知的寄存器名称: {register_name}")
            return None
            
        address = REGISTER_MAP[register_name]
        return self.read_holding_register(address)
    
    def write_register_by_name(self, register_name: str, value: int) -> bool:
        """通过寄存器名称写入数据"""
        if register_name not in REGISTER_MAP:
            logger.error(f"未知的寄存器名称: {register_name}")
            return False
            
        address = REGISTER_MAP[register_name]
        return self.write_holding_register(address, value)
    
    def wait_for_register_value(self, register_name: str, expected_value: int, timeout: int = 30) -> bool:
        """等待寄存器达到指定值"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_value = self.read_register_by_name(register_name)
            if current_value == expected_value:
                logger.info(f"寄存器 {register_name} 已达到期望值: {expected_value}")
                return True
            time.sleep(0.5)
            
        logger.error(f"等待寄存器 {register_name} 达到值 {expected_value} 超时")
        return False
    
    def check_connection(self) -> bool:
        """检查连接状态"""
        if not self.is_connected:
            return False
            
        try:
            # 尝试读取一个寄存器来测试连接
            result = self.client.read_holding_registers(
                address=REGISTER_MAP['SYSTEM_STATUS'],
                count=1,
                device_id=self.unit_id
            )
            return not result.isError()
        except:
            return False
    
    def reconnect(self) -> bool:
        """重新连接"""
        logger.info("尝试重新连接PLC...")
        self.disconnect()
        return self.connect()
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


# 全局Modbus客户端实例
modbus_client = ModbusClient()