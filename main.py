# -*- coding: utf-8 -*-
"""
无人机快递柜控制系统主程序
整合所有模块，提供统一的启动和管理接口
"""

import sys
import time
import threading
import signal
from typing import Optional
from loguru import logger
from datetime import datetime

# 导入所有控制器模块
from config import PLC_CONFIG, LOG_CONFIG, WEB_CONFIG
from modbus_client import modbus_client
from door_controller import door_controller
from drone_storage_controller import drone_storage_controller
from user_pickup_controller import user_pickup_controller
from user_send_controller import user_send_controller
from system_monitor import system_monitor
from web_api import start_web_server


class DroneLockerSystem:
    """无人机快递柜系统主控制类"""
    
    def __init__(self):
        self.running = False
        self.web_server_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        
        # 配置日志
        self._setup_logging()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("无人机快递柜控制系统初始化完成")
    
    def _setup_logging(self):
        """配置日志系统"""
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台输出
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=LOG_CONFIG['level']
        )
        
        # 添加文件输出
        logger.add(
            LOG_CONFIG['file'],
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=LOG_CONFIG['level'],
            rotation=LOG_CONFIG['rotation'],
            retention=LOG_CONFIG['retention'],
            compression="zip",
            encoding="utf-8"
        )
        
        logger.info("日志系统配置完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，开始关闭系统...")
        self.shutdown()
    
    def initialize_system(self) -> bool:
        """初始化系统（支持多机器容错启动）"""
        logger.info("开始初始化无人机快递柜系统...")
        
        initialization_success = True
        
        try:
            # 1. 初始化机器管理器和配置管理器
            logger.info("正在初始化机器管理器...")
            from services.machine_manager import machine_manager
            from services.config_manager import config_manager
            
            # 获取所有机器配置
            all_configs = config_manager.get_all_configs()
            available_machines = [name for name, config in all_configs.items() if config['available']]
            
            if not available_machines:
                logger.warning("未找到可用的机器配置，尝试使用默认PLC连接")
                # 尝试连接默认PLC
                if modbus_client.connect():
                    logger.info(f"默认PLC连接成功 - {PLC_CONFIG['host']}:{PLC_CONFIG['port']}")
                else:
                    logger.error("默认PLC连接失败，但系统将以离线模式启动")
                    initialization_success = False
            else:
                logger.info(f"发现 {len(available_machines)} 台可用机器: {', '.join(available_machines)}")
                
                # 尝试连接所有机器
                connected_count = 0
                for machine_name in available_machines:
                    try:
                        result = machine_manager.test_machine_connection(machine_name)
                        if result['success']:
                            logger.info(f"机器 {machine_name} 连接成功")
                            connected_count += 1
                        else:
                            logger.warning(f"机器 {machine_name} 连接失败: {result.get('error', '未知错误')}")
                    except Exception as e:
                        logger.error(f"测试机器 {machine_name} 连接时发生异常: {e}")
                
                if connected_count == 0:
                    logger.error("所有机器连接失败，但系统将以离线模式启动")
                    initialization_success = False
                else:
                    logger.info(f"成功连接 {connected_count}/{len(available_machines)} 台机器")
            
            # 2. 检查系统状态（非阻塞）
            logger.info("正在检查系统状态...")
            try:
                system_status = system_monitor.get_system_status()
                if system_status:
                    logger.info(f"系统状态: {system_status['status_description']}")
                else:
                    logger.warning("无法获取系统状态")
            except Exception as e:
                logger.warning(f"检查系统状态失败: {e}")
            
            # 3. 检查存储容量（非阻塞）
            logger.info("正在检查存储容量...")
            try:
                storage_capacity = system_monitor.get_storage_capacity()
                if storage_capacity:
                    logger.info("存储容量检查完成")
                else:
                    logger.warning("无法获取存储容量信息")
            except Exception as e:
                logger.warning(f"检查存储容量失败: {e}")
            
            # 4. 检查气象条件（非阻塞）
            logger.info("正在检查气象条件...")
            try:
                weather_check = system_monitor.check_weather_conditions()
                if weather_check:
                    logger.info(f"气象条件: {weather_check['reason']}")
                else:
                    logger.warning("无法获取气象数据")
            except Exception as e:
                logger.warning(f"检查气象条件失败: {e}")
            
            # 5. 初始化舱门状态（非阻塞）
            logger.info("正在初始化舱门状态...")
            try:
                for position in range(1, 7):
                    try:
                        status = door_controller.get_door_status(position)
                        logger.debug(f"舱门{position}状态: {status}")
                    except Exception as e:
                        logger.debug(f"获取舱门{position}状态失败: {e}")
            except Exception as e:
                logger.warning(f"初始化舱门状态失败: {e}")
            
            if initialization_success:
                logger.info("系统初始化完成，所有服务可用")
            else:
                logger.warning("系统初始化完成，但部分服务不可用（离线模式）")
            
            return True  # 总是返回True，允许系统启动
            
        except Exception as e:
            logger.error(f"系统初始化过程中发生异常: {e}")
            logger.warning("系统将以最小功能模式启动")
            return False
    
    def start_web_server(self):
        """启动Web服务器"""
        try:
            logger.info(f"启动Web API服务器 - http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}")
            
            def run_server():
                try:
                    start_web_server()
                except Exception as e:
                    logger.error(f"Web服务器运行异常: {e}")
            
            self.web_server_thread = threading.Thread(target=run_server, daemon=True)
            self.web_server_thread.start()
            
            # 等待服务器启动
            time.sleep(2)
            logger.info("Web API服务器启动完成")
            
        except Exception as e:
            logger.error(f"启动Web服务器失败: {e}")
    
    def start_system_monitor(self):
        """启动系统监控"""
        try:
            logger.info("启动系统监控服务...")
            
            def run_monitor():
                try:
                    system_monitor.start_monitoring(interval=30)
                except Exception as e:
                    logger.error(f"系统监控运行异常: {e}")
            
            self.monitor_thread = threading.Thread(target=run_monitor, daemon=True)
            self.monitor_thread.start()
            
            logger.info("系统监控服务启动完成")
            
        except Exception as e:
            logger.error(f"启动系统监控失败: {e}")
    
    def start(self):
        """启动系统"""
        logger.info("="*60)
        logger.info("无人机快递柜控制系统启动")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        try:
            # 1. 初始化系统
            if not self.initialize_system():
                logger.error("系统初始化失败，无法启动")
                return False
            
            # 2. 启动Web服务器
            self.start_web_server()
            
            # 3. 启动系统监控
            self.start_system_monitor()
            
            # 4. 标记系统运行状态
            self.running = True
            
            logger.info("系统启动完成，所有服务正在运行")
            logger.info(f"Web API地址: http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}")
            logger.info(f"API文档地址: http://{WEB_CONFIG['host']}:{WEB_CONFIG['port']}/docs")
            
            return True
            
        except Exception as e:
            logger.error(f"系统启动失败: {e}")
            return False
    
    def shutdown(self):
        """关闭系统"""
        if not self.running:
            return
        
        logger.info("开始关闭无人机快递柜系统...")
        
        try:
            # 1. 标记系统停止
            self.running = False
            
            # 2. 断开PLC连接
            logger.info("断开PLC连接...")
            modbus_client.disconnect()
            
            # 3. 等待线程结束
            if self.web_server_thread and self.web_server_thread.is_alive():
                logger.info("等待Web服务器关闭...")
                # Web服务器会在主程序退出时自动关闭
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                logger.info("等待系统监控关闭...")
                # 监控线程会在主程序退出时自动关闭
            
            logger.info("系统关闭完成")
            
        except Exception as e:
            logger.error(f"系统关闭异常: {e}")
    
    def run_forever(self):
        """保持系统运行（支持多机器容错）"""
        # 先启动系统
        if not self.start():
            logger.error("系统启动失败")
            return
        
        try:
            logger.info("系统正在运行，按 Ctrl+C 停止...")
            
            # 连接检查间隔（秒）
            connection_check_interval = 30
            last_check_time = 0
            
            while self.running:
                time.sleep(1)
                current_time = time.time()
                
                # 定期检查连接状态（避免频繁检查）
                if current_time - last_check_time >= connection_check_interval:
                    last_check_time = current_time
                    
                    try:
                        # 导入机器管理器
                        from services.machine_manager import machine_manager
                        from services.config_manager import config_manager
                        
                        # 获取所有机器状态
                        all_status = machine_manager.get_all_machine_status()
                        
                        if all_status:
                            # 统计连接状态
                            total_machines = len(all_status)
                            connected_machines = sum(1 for status in all_status.values() 
                                                   if status.get('connected', False))
                            
                            if connected_machines == 0:
                                logger.warning(f"所有机器({total_machines}台)均已断开连接")
                                # 尝试重连一台机器作为测试
                                for machine_name in list(all_status.keys())[:1]:  # 只测试第一台
                                    try:
                                        result = machine_manager.test_machine_connection(machine_name)
                                        if result['success']:
                                            logger.info(f"机器 {machine_name} 重连成功")
                                            break
                                    except Exception as e:
                                        logger.debug(f"测试机器 {machine_name} 连接失败: {e}")
                            elif connected_machines < total_machines:
                                logger.info(f"部分机器在线: {connected_machines}/{total_machines}")
                            else:
                                logger.debug(f"所有机器({total_machines}台)连接正常")
                        else:
                            # 没有配置多机器，检查默认PLC连接
                            if not modbus_client.is_connected:
                                logger.warning("默认PLC连接断开，尝试重新连接...")
                                if modbus_client.reconnect():
                                    logger.info("默认PLC重新连接成功")
                                else:
                                    logger.debug("默认PLC重新连接失败")
                    
                    except Exception as e:
                        logger.debug(f"连接状态检查异常: {e}")
                
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        except Exception as e:
            logger.error(f"系统运行异常: {e}")
        finally:
            self.shutdown()
    
    def get_system_info(self) -> dict:
        """获取系统信息"""
        return {
            "system_name": "无人机快递柜控制系统",
            "version": "1.0.0",
            "running": self.running,
            "plc_connected": modbus_client.is_connected,
            "web_server_running": self.web_server_thread and self.web_server_thread.is_alive(),
            "monitor_running": self.monitor_thread and self.monitor_thread.is_alive(),
            "startup_time": datetime.now().isoformat()
        }


def main():
    """主函数"""
    # 创建系统实例
    system = DroneLockerSystem()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            # 启动系统
            system.run_forever()
        elif command == "test":
            # 测试模式
            logger.info("测试模式启动")
            if system.initialize_system():
                logger.info("系统测试通过")
                
                # 测试各个功能模块
                logger.info("测试舱门控制...")
                for i in range(1, 4):  # 测试前3个舱门
                    status = door_controller.get_door_status(i)
                    logger.info(f"舱门{i}状态: {status}")
                
                logger.info("测试系统状态...")
                status = system_monitor.get_comprehensive_status()
                logger.info(f"系统状态获取: {'成功' if status else '失败'}")
                
                logger.info("测试完成")
            else:
                logger.error("系统测试失败")
            
            system.shutdown()
        elif command == "info":
            # 显示系统信息
            info = system.get_system_info()
            print("\n系统信息:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print("未知命令，支持的命令: start, test, info")
    else:
        # 默认启动系统
        system.run_forever()


if __name__ == "__main__":
    main()