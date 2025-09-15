# -*- coding: utf-8 -*-
"""
无人机存件流程控制模块
实现无人机存件的完整流程控制
"""

import time
from typing import Optional, Tuple
from loguru import logger
from base_controller import BaseController
from door_controller import door_controller
from config import OPERATION_CODES, POSITION_CODES


class DroneStorageController(BaseController):
    """无人机存件控制器类"""
    
    def __init__(self):
        super().__init__()
        self.landing_pad_register = 'LANDING_PAD_STATUS'
        self.package_op_register = 'DRONE_PACKAGE_OP'
        self.servo_register = 'DRONE_SERVO'
        self.storage_status_register = 'STORAGE_STATUS'
        self.store_pos_register = 'DRONE_STORE_POS'
        self.pickup_code_front_register = 'PICKUP_CODE_FRONT'
        self.pickup_code_rear_register = 'PICKUP_CODE_REAR'
        
    def check_storage_capacity(self) -> Optional[bool]:
        """检查存储容量
        
        Returns:
            bool: True表示有空间，False表示已满，None表示检查失败
        """
        try:
            status = self.read_register_with_retry(self.storage_status_register)
            
            if status is None:
                return None
            
            if status == OPERATION_CODES['STORAGE_FULL']:
                logger.warning("机柜已存满，无法执行存件操作")
                return False
            elif status == OPERATION_CODES['STORAGE_AVAILABLE']:
                logger.info("机柜有空间，可以执行存件操作")
                return True
            else:
                logger.warning(f"未知的存储状态: {status}")
                return None
                
        except Exception as e:
            logger.error(f"检查存储容量异常: {e}")
            return None
    
    def confirm_drone_landing(self, timeout: int = 60) -> bool:
        """确认无人机降落
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        logger.info("等待无人机降落...")
        
        try:
            # 写入有飞机状态
            if not modbus_client.write_register_by_name(
                self.landing_pad_register,
                OPERATION_CODES['DRONE_PRESENT']
            ):
                logger.error("写入无人机降落状态失败")
                return False
            
            # 等待下位确认
            if modbus_client.wait_for_register_value(
                self.landing_pad_register,
                OPERATION_CODES['DRONE_PRESENT_CONFIRM'],
                timeout
            ):
                logger.info("无人机降落确认完成")
                return True
            else:
                logger.error("无人机降落确认超时")
                return False
                
        except Exception as e:
            logger.error(f"确认无人机降落异常: {e}")
            return False
    
    def confirm_drone_takeoff(self, timeout: int = 60) -> bool:
        """确认无人机起飞
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        logger.info("确认无人机起飞...")
        
        try:
            # 写入无飞机状态
            if not modbus_client.write_register_by_name(
                self.landing_pad_register,
                OPERATION_CODES['DRONE_ABSENT']
            ):
                logger.error("写入无人机起飞状态失败")
                return False
            
            # 等待下位确认
            if modbus_client.wait_for_register_value(
                self.landing_pad_register,
                OPERATION_CODES['DRONE_ABSENT_CONFIRM'],
                timeout
            ):
                logger.info("无人机起飞确认完成")
                return True
            else:
                logger.error("无人机起飞确认超时")
                return False
                
        except Exception as e:
            logger.error(f"确认无人机起飞异常: {e}")
            return False
    
    def set_pickup_code(self, pickup_code: str) -> bool:
        """设置取件码
        
        Args:
            pickup_code: 6位取件码
            
        Returns:
            bool: 操作是否成功
        """
        if len(pickup_code) != 6 or not pickup_code.isdigit():
            logger.error(f"取件码格式错误: {pickup_code}，应为6位数字")
            return False
        
        try:
            front_three = int(pickup_code[:3])
            rear_three = int(pickup_code[3:])
            
            # 写入前三位
            if not modbus_client.write_register_by_name(
                self.pickup_code_front_register,
                front_three
            ):
                logger.error("写入取件码前三位失败")
                return False
            
            # 写入后三位
            if not modbus_client.write_register_by_name(
                self.pickup_code_rear_register,
                rear_three
            ):
                logger.error("写入取件码后三位失败")
                return False
            
            logger.info(f"取件码设置成功: {pickup_code}")
            return True
            
        except Exception as e:
            logger.error(f"设置取件码异常: {e}")
            return False
    
    def start_storage_operation(self, timeout: int = 30) -> bool:
        """开始存件操作
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        logger.info("开始执行存件操作")
        
        try:
            # 写入存包裹指令
            if not modbus_client.write_register_by_name(
                self.package_op_register,
                OPERATION_CODES['STORE_PACKAGE']
            ):
                logger.error("写入存包裹指令失败")
                return False
            
            logger.info("已发送存包裹指令")
            return True
            
        except Exception as e:
            logger.error(f"开始存件操作异常: {e}")
            return False
    
    def control_servo(self, action: str, timeout: int = 30) -> bool:
        """控制舵机
        
        Args:
            action: 'open' 或 'close'
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        if action not in ['open', 'close']:
            logger.error(f"无效的舵机操作: {action}")
            return False
        
        try:
            if action == 'open':
                # 等待可以开舵机的信号
                logger.info("等待舵机开启信号...")
                if not modbus_client.wait_for_register_value(
                    self.servo_register,
                    OPERATION_CODES['SERVO_CAN_OPEN'],
                    timeout
                ):
                    logger.error("等待舵机开启信号超时")
                    return False
                
                # 发送开舵机指令
                if not modbus_client.write_register_by_name(
                    self.servo_register,
                    OPERATION_CODES['SERVO_OPEN']
                ):
                    logger.error("写入开舵机指令失败")
                    return False
                
                # 等待开舵机确认
                if modbus_client.wait_for_register_value(
                    self.servo_register,
                    OPERATION_CODES['SERVO_OPEN_CONFIRM'],
                    timeout
                ):
                    logger.info("舵机开启完成")
                    return True
                else:
                    logger.error("舵机开启确认超时")
                    return False
                    
            else:  # close
                # 等待可以关舵机的信号
                logger.info("等待舵机关闭信号...")
                if not modbus_client.wait_for_register_value(
                    self.servo_register,
                    OPERATION_CODES['SERVO_CAN_CLOSE'],
                    timeout
                ):
                    logger.error("等待舵机关闭信号超时")
                    return False
                
                # 发送关舵机指令
                if not modbus_client.write_register_by_name(
                    self.servo_register,
                    OPERATION_CODES['SERVO_CLOSE']
                ):
                    logger.error("写入关舵机指令失败")
                    return False
                
                # 等待关舵机确认
                if modbus_client.wait_for_register_value(
                    self.servo_register,
                    OPERATION_CODES['SERVO_CLOSE_CONFIRM'],
                    timeout
                ):
                    logger.info("舵机关闭完成")
                    return True
                else:
                    logger.error("舵机关闭确认超时")
                    return False
                    
        except Exception as e:
            logger.error(f"控制舵机异常: {e}")
            return False
    
    def get_storage_position(self) -> Optional[int]:
        """获取存储位置
        
        Returns:
            int: 存储位置编号，None表示获取失败
        """
        try:
            position_code = modbus_client.read_register_by_name(self.store_pos_register)
            
            if position_code is None:
                return None
            
            # 将位置码转换为位置编号
            position_map = {
                POSITION_CODES['POSITION_1']: 1,
                POSITION_CODES['POSITION_2']: 2,
                POSITION_CODES['POSITION_3']: 3,
            }
            
            return position_map.get(position_code)
            
        except Exception as e:
            logger.error(f"获取存储位置异常: {e}")
            return None
    
    def execute_storage_process(self, pickup_code: str) -> Tuple[bool, Optional[int]]:
        """执行完整的存件流程
        
        Args:
            pickup_code: 6位取件码
            
        Returns:
            Tuple[bool, Optional[int]]: (操作是否成功, 存储位置)
        """
        logger.info(f"开始执行无人机存件流程，取件码: {pickup_code}")
        
        try:
            # 1. 检查存储容量
            if not self.check_storage_capacity():
                return False, None
            
            # 2. 打开舱门
            if not door_controller.open_door():
                logger.error("打开舱门失败")
                return False, None
            
            # 3. 等待无人机降落
            if not self.confirm_drone_landing():
                logger.error("无人机降落确认失败")
                door_controller.close_door()  # 关闭舱门
                return False, None
            
            # 4. 开始存件操作
            if not self.start_storage_operation():
                logger.error("开始存件操作失败")
                self.confirm_drone_takeoff()
                door_controller.close_door()
                return False, None
            
            # 5. 设置取件码
            if not self.set_pickup_code(pickup_code):
                logger.error("设置取件码失败")
                self.confirm_drone_takeoff()
                door_controller.close_door()
                return False, None
            
            # 6. 控制舵机开启
            if not self.control_servo('open'):
                logger.error("舵机开启失败")
                self.confirm_drone_takeoff()
                door_controller.close_door()
                return False, None
            
            # 7. 检查无人机是否取空包裹
            logger.info("检查无人机操作状态...")
            time.sleep(2)  # 等待状态更新
            
            package_status = modbus_client.read_register_by_name(self.package_op_register)
            
            if package_status == OPERATION_CODES['PICKUP_IN_PROGRESS']:
                logger.info("无人机正在取空包裹")
                
                # 等待取件完成信号，然后关闭舵机
                if not self.control_servo('close'):
                    logger.error("舵机关闭失败")
                    return False, None
                
                # 等待无人机可以起飞
                if not modbus_client.wait_for_register_value(
                    self.package_op_register,
                    OPERATION_CODES['PICKUP_COMPLETE'],
                    60
                ):
                    logger.error("等待无人机取件完成超时")
                    return False, None
                    
            elif package_status == OPERATION_CODES['NO_PICKUP_COMPLETE']:
                logger.info("无人机不取空包裹，直接起飞")
                
                # 关闭舵机
                if not self.control_servo('close'):
                    logger.error("舵机关闭失败")
                    return False, None
            
            else:
                logger.warning(f"未知的包裹操作状态: {package_status}")
            
            # 8. 确认无人机起飞
            if not self.confirm_drone_takeoff():
                logger.error("无人机起飞确认失败")
                return False, None
            
            # 9. 关闭舱门
            if not door_controller.close_door():
                logger.error("关闭舱门失败")
                return False, None
            
            # 10. 获取存储位置
            storage_position = self.get_storage_position()
            
            logger.info(f"无人机存件流程完成，存储位置: {storage_position}")
            return True, storage_position
            
        except Exception as e:
            logger.error(f"执行存件流程异常: {e}")
            # 尝试恢复状态
            try:
                self.confirm_drone_takeoff()
                door_controller.close_door()
            except:
                pass
            return False, None


# 全局无人机存件控制器实例
drone_storage_controller = DroneStorageController()