# -*- coding: utf-8 -*-
"""
多机器配置功能测试脚本
"""

import asyncio
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.config_manager import config_manager
from services.machine_manager import machine_manager
from models.drone_cabinet import DroneCabinetDAO
from database.connection import db_manager

async def test_database_connection():
    """测试数据库连接"""
    logger.info("=== 测试数据库连接 ===")
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.success(f"数据库连接成功: {result}")
            return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False

async def test_config_manager():
    """测试配置管理器"""
    logger.info("=== 测试配置管理器 ===")
    try:
        # 加载配置
        config_manager.load_config()
        
        # 获取PLC配置
        plc_config = config_manager.get_plc_config()
        logger.info(f"默认PLC配置: {plc_config}")
        
        # 获取机器配置
        machines = config_manager.get_all_machines()
        logger.info(f"所有机器配置: {machines}")
        
        # 获取指定机器配置
        if machines:
            machine_name = list(machines.keys())[0]
            machine_config = config_manager.get_machine_config(machine_name)
            logger.info(f"机器 {machine_name} 配置: {machine_config}")
        
        return True
    except Exception as e:
        logger.error(f"配置管理器测试失败: {e}")
        return False

async def test_machine_manager():
    """测试机器管理器"""
    logger.info("=== 测试机器管理器 ===")
    try:
        # 初始化机器管理器
        machine_manager.initialize()
        
        # 获取所有机器状态
        status = machine_manager.get_all_status()
        logger.info(f"所有机器状态: {status}")
        
        # 尝试连接机器（如果配置存在）
        machines = config_manager.get_all_machines()
        if machines:
            machine_name = list(machines.keys())[0]
            logger.info(f"尝试连接机器: {machine_name}")
            
            success = machine_manager.connect_machine(machine_name)
            logger.info(f"连接结果: {success}")
            
            # 获取连接状态
            machine_status = machine_manager.get_machine_status(machine_name)
            logger.info(f"机器 {machine_name} 状态: {machine_status}")
            
            # 断开连接
            machine_manager.disconnect_machine(machine_name)
            logger.info(f"已断开机器 {machine_name} 连接")
        
        return True
    except Exception as e:
        logger.error(f"机器管理器测试失败: {e}")
        return False

async def test_dao_operations():
    """测试数据访问对象操作"""
    logger.info("=== 测试DAO操作 ===")
    try:
        dao = DroneCabinetDAO()
        
        # 获取所有机器
        machines = dao.get_all_machines()
        logger.info(f"数据库中的机器: {machines}")
        
        # 测试创建机器（如果不存在）
        test_machine_name = "test_machine"
        existing = dao.get_machine_by_name(test_machine_name)
        
        if not existing:
            machine_id = dao.create_machine({
                'machine_name': test_machine_name,
                'host': '192.168.1.200',
                'port': 502,
                'description': '测试机器',
                'is_active': True
            })
            logger.success(f"创建测试机器成功，ID: {machine_id}")
            
            # 更新机器
            dao.update_machine(test_machine_name, {
                'description': '更新后的测试机器',
                'port': 503
            })
            logger.success("更新测试机器成功")
            
            # 获取更新后的机器
            updated_machine = dao.get_machine_by_name(test_machine_name)
            logger.info(f"更新后的机器: {updated_machine}")
            
            # 删除测试机器
            dao.delete_machine(test_machine_name)
            logger.success("删除测试机器成功")
        else:
            logger.info(f"测试机器已存在: {existing}")
        
        return True
    except Exception as e:
        logger.error(f"DAO操作测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("开始多机器配置功能测试")
    
    tests = [
        ("数据库连接", test_database_connection),
        ("配置管理器", test_config_manager),
        ("DAO操作", test_dao_operations),
        ("机器管理器", test_machine_manager),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n开始测试: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.success(f"✓ {test_name} 测试通过")
            else:
                logger.error(f"✗ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"✗ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    logger.info("\n=== 测试结果汇总 ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        logger.success("🎉 所有测试通过！多机器配置功能正常")
    else:
        logger.warning(f"⚠️  有 {total - passed} 项测试失败，请检查配置")

if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # 运行测试
    asyncio.run(main())