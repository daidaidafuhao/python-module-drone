#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境部署启动脚本
用于在云服务器上启动无人机柜控制系统
"""

import os
import sys
from main import app
from config import Config

def setup_production_environment():
    """设置生产环境配置"""
    # 设置环境变量
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = 'False'
    
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    print("生产环境配置完成")

def main():
    """主启动函数"""
    setup_production_environment()
    
    # 获取配置
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print(f"启动无人机柜控制系统...")
    print(f"监听地址: {host}:{port}")
    print(f"访问地址: http://{host}:{port}")
    
    # 启动应用
    app.run(
        host=host,
        port=port,
        debug=False,
        threaded=True
    )

if __name__ == '__main__':
    main()