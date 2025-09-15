# -*- coding: utf-8 -*-
"""
用户寄件流程控制模块
实现用户寄件的完整流程控制
"""

import time
from typing import Optional, Tuple
from loguru import logger
from base_controller import BaseController
from config import OPERATION_CODES, POSITION_CODES


class UserSendController(BaseController):
    """用户寄件控制器类"""
    
    def __init__(self):
        super().__init__()
        self.send_storage_status_register = 'SEND_STORAGE_STATUS'
        self.send_code_front_register = 'SEND_CODE_FRONT'
        self.send_code_rear_register = 'SEND_CODE_REAR'
        self.send_op_register = 'USER_SEND_OP'
        self.send_empty_box_pos_register = 'SEND_EMPTY_BOX_POS'
        self.send_box_pos_register = 'SEND_BOX_POS'
        self.send_box_weight_register = 'SEND_BOX_WEIGHT'
        
    def check_send_capacity(self) -> Optional[bool]:
        """检查寄件容量
        
        Returns:
            bool: True表示有空箱可寄件，False表示无空箱，None表示检查失败
        """
        try:
            status = self.read_register_with_retry(self.send_storage_status_register)
            
            if status is None:
                return None
            
            if status == 10:  # 0x0A - 有空寄件箱可寄件
                logger.info("有空寄件箱，可以执行寄件操作")
                return True
            elif status == 11:  # 0x0B - 无空寄件箱不可寄件
                logger.warning("无空寄件箱，无法执行寄件操作")
                return False
            else:
                logger.warning(f"未知的寄件存储状态: {status}")
                return None
                
        except Exception as e:
            logger.error(f"检查寄件容量异常: {e}")
            return None
    
    def set_send_code(self, send_code: str) -> bool:
        """设置寄件码
        
        Args:
            send_code: 6位寄件码
            
        Returns:
            bool: 操作是否成功
        """
        if len(send_code) != 6 or not send_code.isdigit():
            logger.error(f"寄件码格式错误: {send_code}，应为6位数字")
            return False
        
        try:
            front_three = int(send_code[:3])
            rear_three = int(send_code[3:])
            
            # 写入前三位
            if not modbus_client.write_register_by_name(
                self.send_code_front_register,
                front_three
            ):
                logger.error("写入寄件码前三位失败")
                return False
            
            # 写入后三位
            if not modbus_client.write_register_by_name(
                self.send_code_rear_register,
                rear_three
            ):
                logger.error("写入寄件码后三位失败")
                return False
            
            logger.info(f"寄件码设置成功: {send_code}")
            return True
            
        except Exception as e:
            logger.error(f"设置寄件码异常: {e}")
            return False
    
    def start_empty_box_pickup(self, send_code: str, timeout: int = 120) -> Tuple[bool, Optional[int]]:
        """开始取空箱流程
        
        Args:
            send_code: 6位寄件码
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[bool, Optional[int]]: (操作是否成功, 取空箱位置)
        """
        logger.info(f"开始取空箱流程，寄件码: {send_code}")
        
        try:
            # 模拟用户在界面输入寄件码后的自动流程
            
            # 1. 等待取空箱操作开始
            logger.info("等待取空箱操作开始...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                send_status = modbus_client.read_register_by_name(self.send_op_register)
                
                if send_status == OPERATION_CODES['USER_SEND_EMPTY_BOX']:
                    logger.info("用户正在取空箱")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待取空箱操作开始超时")
                return False, None
            
            # 2. 获取取空箱位置
            empty_box_position = self.get_empty_box_position()
            if empty_box_position is None:
                logger.error("无法获取取空箱位置")
                return False, None
            
            logger.info(f"取空箱位置: {empty_box_position}")
            
            # 3. 等待取空箱完成
            if modbus_client.wait_for_register_value(
                self.send_op_register,
                OPERATION_CODES['USER_SEND_COMPLETE'],
                timeout
            ):
                logger.info("用户取空箱完成")
                return True, empty_box_position
            else:
                logger.error("用户取空箱超时")
                return False, empty_box_position
                
        except Exception as e:
            logger.error(f"取空箱流程异常: {e}")
            return False, None
    
    def start_send_box_storage(self, timeout: int = 300) -> Tuple[bool, Optional[int], Optional[float]]:
        """开始存寄件箱流程
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[bool, Optional[int], Optional[float]]: (操作是否成功, 存储位置, 包裹重量)
        """
        logger.info("开始存寄件箱流程")
        
        try:
            # 1. 等待用户存寄件箱操作开始（门已打开）
            logger.info("等待用户存寄件箱...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                send_status = modbus_client.read_register_by_name(self.send_op_register)
                
                if send_status == OPERATION_CODES['USER_SEND_BOX_OPEN']:
                    logger.info("寄件箱门已打开，等待用户放入物品")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待存寄件箱操作开始超时")
                return False, None, None
            
            # 2. 等待用户放入物品并确认
            logger.info("等待用户放入物品并点击确认...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                send_status = modbus_client.read_register_by_name(self.send_op_register)
                
                if send_status == OPERATION_CODES['USER_SEND_EMPTY_BOX']:
                    logger.info("用户正在存寄件箱")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待用户确认寄件超时")
                return False, None, None
            
            # 3. 等待存寄件箱完成
            if modbus_client.wait_for_register_value(
                self.send_op_register,
                OPERATION_CODES['USER_SEND_COMPLETE'],
                60
            ):
                logger.info("用户存寄件箱完成")
                
                # 4. 获取存储位置和重量
                storage_position = self.get_send_box_position()
                package_weight = self.get_package_weight()
                
                return True, storage_position, package_weight
            else:
                logger.error("存寄件箱完成确认超时")
                return False, None, None
                
        except Exception as e:
            logger.error(f"存寄件箱流程异常: {e}")
            return False, None, None
    
    def get_empty_box_position(self) -> Optional[int]:
        """获取取空箱位置
        
        Returns:
            int: 取空箱位置编号，None表示获取失败
        """
        try:
            position_code = modbus_client.read_register_by_name(self.send_empty_box_pos_register)
            
            if position_code is None:
                return None
            
            # 将位置码转换为位置编号
            position_map = {
                POSITION_CODES['POSITION_4']: 4,
                POSITION_CODES['POSITION_5']: 5,
                POSITION_CODES['POSITION_6']: 6,
            }
            
            return position_map.get(position_code)
            
        except Exception as e:
            logger.error(f"获取取空箱位置异常: {e}")
            return None
    
    def get_send_box_position(self) -> Optional[int]:
        """获取存寄件箱位置
        
        Returns:
            int: 存寄件箱位置编号，None表示获取失败
        """
        try:
            position_code = modbus_client.read_register_by_name(self.send_box_pos_register)
            
            if position_code is None:
                return None
            
            # 将位置码转换为位置编号
            position_map = {
                POSITION_CODES['POSITION_4']: 4,
                POSITION_CODES['POSITION_5']: 5,
                POSITION_CODES['POSITION_6']: 6,
            }
            
            return position_map.get(position_code)
            
        except Exception as e:
            logger.error(f"获取存寄件箱位置异常: {e}")
            return None
    
    def get_package_weight(self) -> Optional[float]:
        """获取包裹重量
        
        Returns:
            float: 包裹重量（公斤），None表示获取失败
        """
        try:
            weight = modbus_client.read_register_by_name(self.send_box_weight_register)
            
            if weight is None:
                return None
            
            # 假设重量以克为单位存储，转换为公斤
            return float(weight) / 1000.0 if weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"获取包裹重量异常: {e}")
            return None
    
    def execute_complete_send_process(self, send_code: str) -> Tuple[bool, dict]:
        """执行完整的寄件流程
        
        Args:
            send_code: 6位寄件码
            
        Returns:
            Tuple[bool, dict]: (操作是否成功, 寄件信息)
        """
        logger.info(f"开始执行完整寄件流程，寄件码: {send_code}")
        
        send_info = {
            'send_code': send_code,
            'empty_box_position': None,
            'storage_position': None,
            'package_weight': None,
            'timestamp': time.time()
        }
        
        try:
            # 1. 检查寄件容量
            if not self.check_send_capacity():
                logger.error("无空寄件箱，无法执行寄件操作")
                return False, send_info
            
            # 2. 设置寄件码
            if not self.set_send_code(send_code):
                logger.error("设置寄件码失败")
                return False, send_info
            
            # 3. 执行取空箱流程
            empty_box_success, empty_box_position = self.start_empty_box_pickup(send_code)
            
            if not empty_box_success:
                logger.error("取空箱流程失败")
                return False, send_info
            
            send_info['empty_box_position'] = empty_box_position
            logger.info(f"取空箱成功，位置: {empty_box_position}")
            
            # 4. 执行存寄件箱流程
            storage_success, storage_position, package_weight = self.start_send_box_storage()
            
            if not storage_success:
                logger.error("存寄件箱流程失败")
                return False, send_info
            
            send_info['storage_position'] = storage_position
            send_info['package_weight'] = package_weight
            
            logger.info(f"寄件流程完成 - 存储位置: {storage_position}, 重量: {package_weight}kg")
            return True, send_info
            
        except Exception as e:
            logger.error(f"执行完整寄件流程异常: {e}")
            return False, send_info
    
    def get_send_status(self) -> Optional[str]:
        """获取当前寄件状态
        
        Returns:
            str: 寄件状态描述
        """
        try:
            send_status = modbus_client.read_register_by_name(self.send_op_register)
            
            if send_status is None:
                return None
            
            status_map = {
                0: "等待寄件操作",
                OPERATION_CODES['USER_SEND_EMPTY_BOX']: "正在取空箱/存寄件箱",
                OPERATION_CODES['USER_SEND_COMPLETE']: "操作完成",
                OPERATION_CODES['USER_SEND_BOX_OPEN']: "寄件箱门已打开，等待放入物品"
            }
            
            return status_map.get(send_status, f"未知状态: {send_status}")
            
        except Exception as e:
            logger.error(f"获取寄件状态异常: {e}")
            return None
    
    def cancel_send_process(self) -> bool:
        """取消寄件流程
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 重置相关寄存器状态
            success = True
            
            if not modbus_client.write_register_by_name(self.send_op_register, 0):
                success = False
                
            if not modbus_client.write_register_by_name(self.send_code_front_register, 0):
                success = False
                
            if not modbus_client.write_register_by_name(self.send_code_rear_register, 0):
                success = False
            
            if success:
                logger.info("寄件流程已取消")
            else:
                logger.error("取消寄件流程失败")
                
            return success
            
        except Exception as e:
            logger.error(f"取消寄件流程异常: {e}")
            return False


# 全局用户寄件控制器实例
user_send_controller = UserSendController()