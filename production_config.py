#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境配置文件
包含云服务器部署所需的配置参数
"""

import os
from config import Config

class ProductionConfig(Config):
    """生产环境配置类"""
    
    # Flask配置
    DEBUG = False
    TESTING = False
    
    # 安全配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-production-secret-key-change-this')
    
    # 数据库配置 - 使用环境变量
    DATABASE_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'drone_cabinet'),
        'charset': 'utf8mb4'
    }
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'production.log')
    
    # Modbus配置 - 生产环境
    MODBUS_CONFIG = {
        'host': os.environ.get('MODBUS_HOST', '192.168.1.100'),
        'port': int(os.environ.get('MODBUS_PORT', 502)),
        'timeout': 10,
        'retry_count': 3
    }
    
    # API配置
    API_KEY_REQUIRED = True
    DEFAULT_API_KEY = os.environ.get('API_KEY', 'default-api-key-change-this')
    
    # 性能配置
    THREADED = True
    PROCESSES = 1
    
    # 监控配置
    HEALTH_CHECK_INTERVAL = 30  # 秒
    CONNECTION_TIMEOUT = 5      # 秒
    
    @staticmethod
    def validate_config():
        """验证生产环境配置"""
        required_env_vars = [
            'SECRET_KEY',
            'DB_HOST',
            'DB_USER', 
            'DB_PASSWORD',
            'DB_NAME',
            'MODBUS_HOST',
            'API_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"警告: 以下环境变量未设置: {', '.join(missing_vars)}")
            print("建议在部署前设置这些环境变量以确保安全性")
        
        return len(missing_vars) == 0

# 导出配置
config = ProductionConfig()