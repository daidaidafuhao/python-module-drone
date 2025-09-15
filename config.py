# -*- coding: utf-8 -*-
"""
无人机快递柜系统配置文件
"""

# PLC连接配置
PLC_CONFIG = {
    'host': 'sk.yunenjoy.cn',
    'port': 61464,
    'timeout': 3,
    'retry_count': 3,
    'unit_id': 1
}

# Modbus寄存器地址映射
REGISTER_MAP = {
    # 舱门控制
    'DOOR_CONTROL': 0xBB8,  # VW3000
    
    # 停机坪状态
    'LANDING_PAD_STATUS': 0xBB9,  # VW3001
    
    # 无人机存取包裹
    'DRONE_PACKAGE_OP': 0xBBA,  # VW3002
    
    # 无人机舵机状态
    'DRONE_SERVO': 0xBBB,  # VW3003
    
    # 无人机存包裹位置
    'DRONE_STORE_POS': 0xBBC,  # VW3004
    
    # 无人机取包裹位置
    'DRONE_PICKUP_POS': 0xBBD,  # VW3005
    
    # 存储状态
    'STORAGE_STATUS': 0xBBE,  # VW3006
    
    # 取件存储状态
    'PICKUP_STORAGE_STATUS': 0xBBF,  # VW3007
    
    # 舵机状态
    'SERVO_STATUS': 0xBC0,  # VW3008
    
    # 取件码（前三位）
    'PICKUP_CODE_FRONT': 0xBC1,  # VW3009
    
    # 取件码（后三位）
    'PICKUP_CODE_REAR': 0xBC2,  # VW3010
    
    # 取包裹位置信息
    'PICKUP_POSITION': 0xBC3,  # VW3011
    
    # 用户取包裹操作
    'USER_PICKUP_OP': 0xBC4,  # VW3012
    
    # 用户回收包裹操作
    'USER_RECYCLE_OP': 0xBC5,  # VW3013
    
    # 用户确认回收操作
    'USER_CONFIRM_RECYCLE': 0xBC6,  # VW3014
    
    # 用户寄件取空箱格口信息
    'SEND_EMPTY_BOX_POS': 0xBC7,  # VW3015
    
    # 用户寄件操作
    'USER_SEND_OP': 0xBC8,  # VW3016
    
    # 用户寄件存寄件箱格口信息
    'SEND_BOX_POS': 0xBCA,  # VW3018
    
    # 用户寄件存寄件箱当前重量
    'SEND_BOX_WEIGHT': 0xBCB,  # VW3019
    
    # 系统状态控制
    'SYSTEM_CONTROL': 0xBCC,  # VW3020
    
    # 系统状态读取
    'SYSTEM_STATUS': 0xBCD,  # VW3021
    
    # 系统报警
    'SYSTEM_ALARM': 0xBCE,  # VW3022
    
    # 故障清除
    'FAULT_CLEAR': 0xBCF,  # VW3023
    
    # 寄件码（前三位）
    'SEND_CODE_FRONT': 0xBD0,  # VW3024
    
    # 寄件码（后三位）
    'SEND_CODE_REAR': 0xBD1,  # VW3025
    
    # 用户寄件格口状态
    'SEND_STORAGE_STATUS': 0xBD2,  # VW3026
    
    # 气象站数据寄存器
    'WEATHER_HUMIDITY': 0x8FC,  # VW2300
    'WEATHER_TEMPERATURE': 0x8FE,  # VW2302
    'WEATHER_WIND_FORCE': 0x900,  # VW2304
    'WEATHER_RAINFALL': 0x902,  # VW2306
    'WEATHER_WIND_SPEED': 0x904,  # VW2308
    'WEATHER_WIND_DIRECTION': 0x906,  # VW2310
    'WEATHER_PRESSURE': 0x908,  # VW2312
    
    # 系统报警信息起始地址
    'ALARM_START': 0xBFE,  # VW3070
}

# 操作码定义
OPERATION_CODES = {
    # 舱门操作
    'DOOR_OPEN': 10,
    'DOOR_CLOSE': 20,
    'DOOR_OPEN_COMPLETE': 11,
    'DOOR_CLOSE_COMPLETE': 21,
    
    # 停机坪状态
    'DRONE_PRESENT': 10,
    'DRONE_ABSENT': 20,
    'DRONE_PRESENT_CONFIRM': 11,
    'DRONE_ABSENT_CONFIRM': 21,
    
    # 无人机存取包裹
    'STORE_PACKAGE': 110,
    'STORE_COMPLETE': 111,
    'PICKUP_IN_PROGRESS': 120,
    'PICKUP_COMPLETE': 121,
    'NO_PICKUP_COMPLETE': 122,
    
    # 舵机控制
    'SERVO_OPEN': 10,
    'SERVO_CLOSE': 20,
    'SERVO_OPEN_CONFIRM': 11,
    'SERVO_CLOSE_CONFIRM': 21,
    'SERVO_CAN_OPEN': 1,
    'SERVO_CAN_CLOSE': 2,
    
    # 存储状态
    'STORAGE_FULL': 10,
    'STORAGE_AVAILABLE': 20,
    
    # 用户操作
    'USER_PICKUP': 210,
    'USER_PICKUP_COMPLETE': 211,
    'USER_RECYCLE': 210,
    'USER_RECYCLE_COMPLETE': 211,
    'USER_SEND_EMPTY_BOX': 210,
    'USER_SEND_COMPLETE': 211,
    'USER_SEND_BOX_OPEN': 220,
    
    # 系统状态
    'AUTO_MODE_ON': 10,
    'PAUSE_MODE_ON': 20,
    'EMERGENCY_STOP_ON': 30,
    'AUTO_MODE_OFF': 11,
    'PAUSE_MODE_OFF': 21,
    'EMERGENCY_STOP_OFF': 31,
    'AUTO_STATUS': 12,
    'PAUSE_STATUS': 22,
    'EMERGENCY_STATUS': 32,
    
    # 故障清除
    'FAULT_CLEAR_CMD': 10,
    'FAULT_CLEAR_COMPLETE': 11,
}

# 位置编码
POSITION_CODES = {
    'POSITION_1': 101,
    'POSITION_2': 102,
    'POSITION_3': 103,
    'POSITION_4': 104,
    'POSITION_5': 105,
    'POSITION_6': 106,
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'file': 'logs/drone_locker.log',
    'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}',
    'rotation': '1 day',
    'retention': '30 days',
    'compression': 'zip'
}

# Web服务配置
WEB_CONFIG = {
    'host': '127.0.0.1',
    'port': 8000,
    'reload': True
}

# 安全配置
SECURITY_CONFIG = {
    'valid_keys': {
        'admin123',  # 管理员密钥
        'drone2024',  # 系统密钥
        'test123'     # 测试密钥
    },
    'key_expiry_hours': 24,  # 密钥有效期（小时）
    'require_key': True      # 是否启用密钥验证
}