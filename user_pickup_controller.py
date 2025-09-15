# -*- coding: utf-8 -*-
"""
用户取件流程控制模块
实现用户取件的完整流程控制
"""

import time
from typing import Optional, Tuple
from loguru import logger
from base_controller import BaseController
from config import OPERATION_CODES, POSITION_CODES


class UserPickupController(BaseController):
    """用户取件控制器类"""
    
    def __init__(self):
        super().__init__()
        self.pickup_op_register = 'USER_PICKUP_OP'
        self.pickup_position_register = 'PICKUP_POSITION'
        self.recycle_op_register = 'USER_RECYCLE_OP'
        self.confirm_recycle_register = 'USER_CONFIRM_RECYCLE'
        
    def start_pickup_process(self, pickup_code: str) -> Tuple[bool, Optional[int]]:
        """开始取件流程
        
        Args:
            pickup_code: 6位取件码
            
        Returns:
            Tuple[bool, Optional[int]]: (操作是否成功, 取件位置)
        """
        if len(pickup_code) != 6 or not pickup_code.isdigit():
            logger.error(f"取件码格式错误: {pickup_code}，应为6位数字")
            return False, None
        
        logger.info(f"开始用户取件流程，取件码: {pickup_code}")
        
        try:
            # 模拟用户在界面输入取件码后的自动流程
            # 实际实现中，这里应该是PLC根据取件码自动执行
            
            # 1. 等待取件操作开始
            logger.info("等待取件操作开始...")
            
            # 检查取件状态
            start_time = time.time()
            timeout = 60
            
            while time.time() - start_time < timeout:
                pickup_status = modbus_client.read_register_by_name(self.pickup_op_register)
                
                if pickup_status == OPERATION_CODES['USER_PICKUP']:
                    logger.info("用户正在取件")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待取件操作开始超时")
                return False, None
            
            # 2. 获取取件位置
            pickup_position = self.get_pickup_position()
            if pickup_position is None:
                logger.error("无法获取取件位置")
                return False, None
            
            logger.info(f"取件位置: {pickup_position}")
            
            # 3. 等待取件完成
            if modbus_client.wait_for_register_value(
                self.pickup_op_register,
                OPERATION_CODES['USER_PICKUP_COMPLETE'],
                120  # 给用户足够时间取件
            ):
                logger.info("用户取件完成")
                return True, pickup_position
            else:
                logger.error("用户取件超时")
                return False, pickup_position
                
        except Exception as e:
            logger.error(f"取件流程异常: {e}")
            return False, None
    
    def get_pickup_position(self) -> Optional[int]:
        """获取取件位置
        
        Returns:
            int: 取件位置编号，None表示获取失败
        """
        try:
            position_code = modbus_client.read_register_by_name(self.pickup_position_register)
            
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
            logger.error(f"获取取件位置异常: {e}")
            return None
    
    def start_recycle_process(self, timeout: int = 120) -> bool:
        """开始回收空箱流程
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        logger.info("开始空箱回收流程")
        
        try:
            # 1. 等待用户点击"我要回收"按钮
            logger.info("等待用户点击回收按钮...")
            
            # 检查回收操作状态
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                recycle_status = modbus_client.read_register_by_name(self.recycle_op_register)
                
                if recycle_status == OPERATION_CODES['USER_RECYCLE']:
                    logger.info("用户已点击回收按钮，机柜门正在打开")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待用户回收操作超时")
                return False
            
            # 2. 等待机柜门打开完成
            if modbus_client.wait_for_register_value(
                self.recycle_op_register,
                OPERATION_CODES['USER_RECYCLE_COMPLETE'],
                30
            ):
                logger.info("机柜门已打开，等待用户放入空箱")
            else:
                logger.error("机柜门打开超时")
                return False
            
            # 3. 等待用户放入空箱并确认
            logger.info("等待用户放入空箱并确认...")
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                confirm_status = modbus_client.read_register_by_name(self.confirm_recycle_register)
                
                if confirm_status == OPERATION_CODES['USER_RECYCLE']:
                    logger.info("用户正在存放空箱")
                    break
                    
                time.sleep(1)
            else:
                logger.error("等待用户确认回收超时")
                return False
            
            # 4. 等待回收完成
            if modbus_client.wait_for_register_value(
                self.confirm_recycle_register,
                OPERATION_CODES['USER_RECYCLE_COMPLETE'],
                60
            ):
                logger.info("空箱回收完成")
                return True
            else:
                logger.error("空箱回收完成确认超时")
                return False
                
        except Exception as e:
            logger.error(f"回收流程异常: {e}")
            return False
    
    def execute_complete_pickup_process(self, pickup_code: str) -> bool:
        """执行完整的取件流程（包括回收）
        
        Args:
            pickup_code: 6位取件码
            
        Returns:
            bool: 操作是否成功
        """
        logger.info(f"开始执行完整取件流程，取件码: {pickup_code}")
        
        try:
            # 1. 执行取件流程
            pickup_success, pickup_position = self.start_pickup_process(pickup_code)
            
            if not pickup_success:
                logger.error("取件流程失败")
                return False
            
            logger.info(f"取件成功，位置: {pickup_position}")
            
            # 2. 执行回收流程
            if not self.start_recycle_process():
                logger.error("回收流程失败")
                return False
            
            logger.info("完整取件流程执行成功")
            return True
            
        except Exception as e:
            logger.error(f"执行完整取件流程异常: {e}")
            return False
    
    def get_pickup_status(self) -> Optional[str]:
        """获取当前取件状态
        
        Returns:
            str: 取件状态描述
        """
        try:
            pickup_status = modbus_client.read_register_by_name(self.pickup_op_register)
            recycle_status = modbus_client.read_register_by_name(self.recycle_op_register)
            confirm_status = modbus_client.read_register_by_name(self.confirm_recycle_register)
            
            if pickup_status == OPERATION_CODES['USER_PICKUP']:
                return "用户正在取件"
            elif pickup_status == OPERATION_CODES['USER_PICKUP_COMPLETE']:
                if recycle_status == OPERATION_CODES['USER_RECYCLE']:
                    return "取件完成，等待回收空箱"
                elif recycle_status == OPERATION_CODES['USER_RECYCLE_COMPLETE']:
                    if confirm_status == OPERATION_CODES['USER_RECYCLE']:
                        return "正在存放空箱"
                    elif confirm_status == OPERATION_CODES['USER_RECYCLE_COMPLETE']:
                        return "取件和回收流程全部完成"
                    else:
                        return "机柜门已打开，等待放入空箱"
                else:
                    return "取件完成，等待回收操作"
            else:
                return "等待取件操作"
                
        except Exception as e:
            logger.error(f"获取取件状态异常: {e}")
            return None
    
    def cancel_pickup_process(self) -> bool:
        """取消取件流程
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 重置相关寄存器状态
            success = True
            
            if not modbus_client.write_register_by_name(self.pickup_op_register, 0):
                success = False
                
            if not modbus_client.write_register_by_name(self.recycle_op_register, 0):
                success = False
                
            if not modbus_client.write_register_by_name(self.confirm_recycle_register, 0):
                success = False
            
            if success:
                logger.info("取件流程已取消")
            else:
                logger.error("取消取件流程失败")
                
            return success
            
        except Exception as e:
            logger.error(f"取消取件流程异常: {e}")
            return False


# 全局用户取件控制器实例
user_pickup_controller = UserPickupController()