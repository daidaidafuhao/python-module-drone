# -*- coding: utf-8 -*-
"""
系统状态监控模块
实现对PLC设备状态、气象站数据、系统报警等的监控功能
"""

import time
from typing import Dict, Optional, List, Any
from datetime import datetime
from loguru import logger
from modbus_client import modbus_client
from config import OPERATION_CODES, POSITION_CODES


class SystemMonitor:
    """系统状态监控器类"""
    
    def __init__(self):
        # 系统状态寄存器
        self.system_status_register = 'SYSTEM_STATUS'
        self.system_alarm_register = 'SYSTEM_ALARM'
        
        # 停机坪状态寄存器
        self.landing_pad_status_register = 'LANDING_PAD_STATUS'
        
        # 舵机状态寄存器
        self.servo_status_register = 'SERVO_STATUS'
        
        # 气象站数据寄存器
        self.weather_wind_speed_register = 'WEATHER_WIND_SPEED'
        self.weather_wind_direction_register = 'WEATHER_WIND_DIRECTION'
        self.weather_temperature_register = 'WEATHER_TEMPERATURE'
        self.weather_humidity_register = 'WEATHER_HUMIDITY'
        self.weather_pressure_register = 'WEATHER_PRESSURE'
        self.weather_rainfall_register = 'WEATHER_RAINFALL'
        
        # 存储容量状态寄存器
        self.storage_status_register = 'STORAGE_STATUS'
        self.pickup_storage_status_register = 'PICKUP_STORAGE_STATUS'
        self.send_storage_status_register = 'SEND_STORAGE_STATUS'
        
        # 监控历史数据
        self.status_history = []
        self.alarm_history = []
        self.weather_history = []
        
    def get_system_status(self) -> Optional[Dict[str, Any]]:
        """获取系统状态
        
        Returns:
            Dict: 系统状态信息，None表示获取失败
        """
        try:
            system_status = modbus_client.read_register_by_name(self.system_status_register)
            
            if system_status is None:
                return None
            
            status_info = {
                'timestamp': datetime.now().isoformat(),
                'raw_status': system_status,
                'status_description': self._parse_system_status(system_status),
                'is_normal': system_status == OPERATION_CODES.get('SYSTEM_NORMAL', 0)
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"获取系统状态异常: {e}")
            return None
    
    def get_system_alarms(self) -> Optional[Dict[str, Any]]:
        """获取系统报警信息
        
        Returns:
            Dict: 系统报警信息，None表示获取失败
        """
        try:
            alarm_status = modbus_client.read_register_by_name(self.system_alarm_register)
            
            if alarm_status is None:
                return None
            
            alarm_info = {
                'timestamp': datetime.now().isoformat(),
                'raw_alarm': alarm_status,
                'alarm_list': self._parse_system_alarms(alarm_status),
                'has_alarm': alarm_status != 0
            }
            
            return alarm_info
            
        except Exception as e:
            logger.error(f"获取系统报警异常: {e}")
            return None
    
    def get_landing_pad_status(self) -> Optional[Dict[str, Any]]:
        """获取停机坪状态
        
        Returns:
            Dict: 停机坪状态信息，None表示获取失败
        """
        try:
            pad_status = modbus_client.read_register_by_name(self.landing_pad_status_register)
            
            if pad_status is None:
                return None
            
            status_info = {
                'timestamp': datetime.now().isoformat(),
                'raw_status': pad_status,
                'status_description': self._parse_landing_pad_status(pad_status),
                'is_available': pad_status == OPERATION_CODES.get('LANDING_PAD_AVAILABLE', 10)
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"获取停机坪状态异常: {e}")
            return None
    
    def get_servo_status(self) -> Optional[Dict[str, Any]]:
        """获取舵机状态
        
        Returns:
            Dict: 舵机状态信息，None表示获取失败
        """
        try:
            servo_status = modbus_client.read_register_by_name(self.servo_status_register)
            
            if servo_status is None:
                return None
            
            status_info = {
                'timestamp': datetime.now().isoformat(),
                'raw_status': servo_status,
                'status_description': self._parse_servo_status(servo_status),
                'is_normal': servo_status == OPERATION_CODES.get('SERVO_NORMAL', 0)
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"获取舵机状态异常: {e}")
            return None
    
    def get_weather_data(self) -> Optional[Dict[str, Any]]:
        """获取气象站数据
        
        Returns:
            Dict: 气象数据，None表示获取失败
        """
        try:
            weather_data = {
                'timestamp': datetime.now().isoformat(),
                'wind_speed': None,
                'wind_direction': None,
                'temperature': None,
                'humidity': None,
                'pressure': None,
                'rainfall': None
            }
            
            # 读取风速（m/s）
            wind_speed = modbus_client.read_register_by_name(self.weather_wind_speed_register)
            if wind_speed is not None:
                weather_data['wind_speed'] = float(wind_speed) / 10.0  # 假设以0.1m/s为单位
            
            # 读取风向（度）
            wind_direction = modbus_client.read_register_by_name(self.weather_wind_direction_register)
            if wind_direction is not None:
                weather_data['wind_direction'] = float(wind_direction)
            
            # 读取温度（℃）
            temperature = modbus_client.read_register_by_name(self.weather_temperature_register)
            if temperature is not None:
                weather_data['temperature'] = float(temperature) / 10.0  # 假设以0.1℃为单位
            
            # 读取湿度（%）
            humidity = modbus_client.read_register_by_name(self.weather_humidity_register)
            if humidity is not None:
                weather_data['humidity'] = float(humidity) / 10.0  # 假设以0.1%为单位
            
            # 读取气压（hPa）
            pressure = modbus_client.read_register_by_name(self.weather_pressure_register)
            if pressure is not None:
                weather_data['pressure'] = float(pressure) / 10.0  # 假设以0.1hPa为单位
            
            # 读取降雨量（mm）
            rainfall = modbus_client.read_register_by_name(self.weather_rainfall_register)
            if rainfall is not None:
                weather_data['rainfall'] = float(rainfall) / 10.0  # 假设以0.1mm为单位
            
            return weather_data
            
        except Exception as e:
            logger.error(f"获取气象数据异常: {e}")
            return None
    
    def get_storage_capacity(self) -> Optional[Dict[str, Any]]:
        """获取存储容量状态
        
        Returns:
            Dict: 存储容量信息，None表示获取失败
        """
        try:
            capacity_info = {
                'timestamp': datetime.now().isoformat(),
                'general_storage': None,
                'pickup_storage': None,
                'send_storage': None
            }
            
            # 读取一般存储状态
            general_status = modbus_client.read_register_by_name(self.storage_status_register)
            if general_status is not None:
                capacity_info['general_storage'] = {
                    'raw_status': general_status,
                    'description': self._parse_storage_status(general_status),
                    'is_available': general_status == OPERATION_CODES.get('STORAGE_AVAILABLE', 10)
                }
            
            # 读取取件存储状态
            pickup_status = modbus_client.read_register_by_name(self.pickup_storage_status_register)
            if pickup_status is not None:
                capacity_info['pickup_storage'] = {
                    'raw_status': pickup_status,
                    'description': self._parse_storage_status(pickup_status),
                    'is_available': pickup_status == OPERATION_CODES.get('STORAGE_AVAILABLE', 10)
                }
            
            # 读取寄件存储状态
            send_status = modbus_client.read_register_by_name(self.send_storage_status_register)
            if send_status is not None:
                capacity_info['send_storage'] = {
                    'raw_status': send_status,
                    'description': self._parse_send_storage_status(send_status),
                    'is_available': send_status == 10  # 0x0A - 有空寄件箱可寄件
                }
            
            return capacity_info
            
        except Exception as e:
            logger.error(f"获取存储容量异常: {e}")
            return None
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合系统状态
        
        Returns:
            Dict: 综合状态信息
        """
        comprehensive_status = {
            'timestamp': datetime.now().isoformat(),
            'system_status': self.get_system_status(),
            'system_alarms': self.get_system_alarms(),
            'landing_pad_status': self.get_landing_pad_status(),
            'servo_status': self.get_servo_status(),
            'weather_data': self.get_weather_data(),
            'storage_capacity': self.get_storage_capacity(),
            'plc_connection': modbus_client.is_connected
        }
        
        return comprehensive_status
    
    def start_monitoring(self, interval: int = 30, max_history: int = 1000) -> None:
        """开始系统监控
        
        Args:
            interval: 监控间隔（秒）
            max_history: 最大历史记录数
        """
        logger.info(f"开始系统监控，间隔: {interval}秒")
        
        try:
            while True:
                # 获取综合状态
                status = self.get_comprehensive_status()
                
                # 记录状态历史
                self.status_history.append(status)
                if len(self.status_history) > max_history:
                    self.status_history.pop(0)
                
                # 检查报警
                if status['system_alarms'] and status['system_alarms']['has_alarm']:
                    self.alarm_history.append(status['system_alarms'])
                    if len(self.alarm_history) > max_history:
                        self.alarm_history.pop(0)
                    
                    logger.warning(f"系统报警: {status['system_alarms']['alarm_list']}")
                
                # 记录气象数据历史
                if status['weather_data']:
                    self.weather_history.append(status['weather_data'])
                    if len(self.weather_history) > max_history:
                        self.weather_history.pop(0)
                
                # 检查PLC连接状态
                if not status['plc_connection']:
                    logger.error("PLC连接断开，尝试重新连接...")
                    modbus_client.reconnect()
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("监控已停止")
        except Exception as e:
            logger.error(f"监控异常: {e}")
    
    def _parse_system_status(self, status_code: int) -> str:
        """解析系统状态码"""
        status_map = {
            0: "系统正常",
            1: "系统初始化中",
            2: "系统维护模式",
            3: "系统故障",
            4: "系统离线"
        }
        return status_map.get(status_code, f"未知状态: {status_code}")
    
    def _parse_system_alarms(self, alarm_code: int) -> List[str]:
        """解析系统报警码"""
        alarms = []
        
        # 使用位操作解析报警
        if alarm_code & 0x01:
            alarms.append("舱门故障")
        if alarm_code & 0x02:
            alarms.append("舵机故障")
        if alarm_code & 0x04:
            alarms.append("停机坪异常")
        if alarm_code & 0x08:
            alarms.append("气象站故障")
        if alarm_code & 0x10:
            alarms.append("存储系统异常")
        if alarm_code & 0x20:
            alarms.append("通信异常")
        if alarm_code & 0x40:
            alarms.append("电源异常")
        if alarm_code & 0x80:
            alarms.append("安全系统报警")
        
        return alarms if alarms else ["无报警"]
    
    def _parse_landing_pad_status(self, status_code: int) -> str:
        """解析停机坪状态码"""
        status_map = {
            OPERATION_CODES.get('LANDING_PAD_AVAILABLE', 10): "停机坪可用",
            OPERATION_CODES.get('LANDING_PAD_OCCUPIED', 20): "停机坪被占用",
            30: "停机坪维护中",
            40: "停机坪故障"
        }
        return status_map.get(status_code, f"未知状态: {status_code}")
    
    def _parse_servo_status(self, status_code: int) -> str:
        """解析舵机状态码"""
        status_map = {
            0: "舵机正常",
            1: "舵机运行中",
            2: "舵机故障",
            3: "舵机离线",
            4: "舵机过载"
        }
        return status_map.get(status_code, f"未知状态: {status_code}")
    
    def _parse_storage_status(self, status_code: int) -> str:
        """解析存储状态码"""
        status_map = {
            OPERATION_CODES.get('STORAGE_AVAILABLE', 10): "有空位可用",
            OPERATION_CODES.get('STORAGE_FULL', 20): "存储已满",
            30: "存储系统维护中",
            40: "存储系统故障"
        }
        return status_map.get(status_code, f"未知状态: {status_code}")
    
    def _parse_send_storage_status(self, status_code: int) -> str:
        """解析寄件存储状态码"""
        status_map = {
            10: "有空寄件箱可寄件",  # 0x0A
            11: "无空寄件箱不可寄件",  # 0x0B
            30: "寄件系统维护中",
            40: "寄件系统故障"
        }
        return status_map.get(status_code, f"未知寄件状态: {status_code}")
    
    def get_status_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取状态历史记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List: 状态历史记录
        """
        return self.status_history[-limit:] if self.status_history else []
    
    def get_alarm_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取报警历史记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List: 报警历史记录
        """
        return self.alarm_history[-limit:] if self.alarm_history else []
    
    def get_weather_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取气象数据历史记录
        
        Args:
            limit: 返回记录数限制
            
        Returns:
            List: 气象数据历史记录
        """
        return self.weather_history[-limit:] if self.weather_history else []
    
    def check_weather_conditions(self) -> Dict[str, Any]:
        """检查气象条件是否适合无人机操作
        
        Returns:
            Dict: 气象条件检查结果
        """
        weather_data = self.get_weather_data()
        
        if not weather_data:
            return {
                'suitable': False,
                'reason': '无法获取气象数据',
                'weather_data': None
            }
        
        # 定义安全阈值
        max_wind_speed = 10.0  # m/s
        min_temperature = -10.0  # ℃
        max_temperature = 50.0  # ℃
        max_rainfall = 5.0  # mm
        
        unsuitable_reasons = []
        
        if weather_data['wind_speed'] and weather_data['wind_speed'] > max_wind_speed:
            unsuitable_reasons.append(f"风速过大: {weather_data['wind_speed']}m/s")
        
        if weather_data['temperature']:
            if weather_data['temperature'] < min_temperature:
                unsuitable_reasons.append(f"温度过低: {weather_data['temperature']}℃")
            elif weather_data['temperature'] > max_temperature:
                unsuitable_reasons.append(f"温度过高: {weather_data['temperature']}℃")
        
        if weather_data['rainfall'] and weather_data['rainfall'] > max_rainfall:
            unsuitable_reasons.append(f"降雨量过大: {weather_data['rainfall']}mm")
        
        return {
            'suitable': len(unsuitable_reasons) == 0,
            'reason': '; '.join(unsuitable_reasons) if unsuitable_reasons else '气象条件良好',
            'weather_data': weather_data
        }


# 全局系统监控器实例
system_monitor = SystemMonitor()