# 无人机快递柜控制系统

基于Python和Modbus协议的无人机快递柜控制系统，提供完整的硬件接口控制和Web API服务。

## 系统概述

本系统实现了无人机快递柜的完整控制功能，包括：

- **舱门控制**: 支持6个舱门的开启/关闭操作
- **无人机存件**: 自动化无人机包裹存储流程
- **用户取件**: 基于取件码的用户取件流程
- **用户寄件**: 完整的用户寄件操作流程
- **系统监控**: 实时监控系统状态、气象数据和设备状态
- **Web API**: RESTful API接口，支持远程控制和状态查询

## 技术架构

- **通信协议**: Modbus TCP
- **Web框架**: FastAPI
- **日志系统**: Loguru
- **异步处理**: Python asyncio
- **数据验证**: Pydantic

## 项目结构

```
无人机快递柜控制系统/
├── config.py                    # 系统配置文件
├── modbus_client.py            # Modbus通信客户端
├── door_controller.py          # 舱门控制模块
├── drone_storage_controller.py # 无人机存件控制模块
├── user_pickup_controller.py   # 用户取件控制模块
├── user_send_controller.py     # 用户寄件控制模块
├── system_monitor.py           # 系统状态监控模块
├── web_api.py                  # Web API接口模块
├── main.py                     # 主程序入口
├── requirements.txt            # Python依赖包
└── README.md                   # 项目说明文档
```

## 安装指南

### 1. 环境要求

- Python 3.8+
- Windows 10/11 或 Linux
- PLC设备支持Modbus TCP协议

### 2. 安装依赖

```bash
# 安装Python依赖包
pip install -r requirements.txt
```

### 3. 配置系统

编辑 `config.py` 文件，配置PLC连接参数：

```python
PLC_CONFIG = {
    'host': '192.168.1.100',  # PLC设备IP地址
    'port': 502,              # Modbus端口
    'timeout': 5,             # 连接超时时间
    'unit_id': 1              # 设备单元ID
}
```

## 使用方法

### 1. 启动系统

```bash
# 启动完整系统（包含Web API服务）
python main.py start

# 或者直接运行
python main.py
```

### 2. 测试模式

```bash
# 运行系统测试
python main.py test
```

### 3. 查看系统信息

```bash
# 显示系统信息
python main.py info
```

### 4. Web API使用

系统启动后，Web API服务将在 `http://localhost:8000` 运行。

#### 主要API接口

**无人机存件接口**
```http
POST /api/drone/storage
Content-Type: application/json

{
    "pickup_code": "123456",
    "package_info": {
        "weight": 1.5,
        "dimensions": "20x15x10",
        "sender": "用户A",
        "recipient": "用户B"
    }
}
```

**存件状态查询**
```http
GET /api/drone/storage/status
```

**系统状态检查**
```http
GET /api/system/status
```

**Modbus寄存器操作**
```http
# 读取寄存器
POST /api/modbus/read
{
    "address": 3006
}

# 写入寄存器
POST /api/modbus/write
{
    "address": 3001,
    "values": [11]
}
```

#### API文档

访问 `http://localhost:8000/docs` 查看完整的API文档。

#### 主要API接口

**系统状态**
- `GET /api/system/status` - 获取系统状态
- `GET /api/system/alarms` - 获取系统报警
- `GET /api/system/weather` - 获取气象数据
- `GET /api/system/storage` - 获取存储容量

**舱门控制**
- `POST /api/door/operate` - 控制舱门开关
- `GET /api/door/status/{position}` - 获取指定舱门状态
- `GET /api/door/status` - 获取所有舱门状态

**无人机存件**
- `POST /api/drone/storage` - 启动无人机存件流程
- `GET /api/drone/storage/status` - 获取存件状态

**用户取件**
- `POST /api/user/pickup` - 启动用户取件流程
- `GET /api/user/pickup/status` - 获取取件状态
- `DELETE /api/user/pickup/cancel` - 取消取件流程

**用户寄件**
- `POST /api/user/send` - 启动用户寄件流程
- `GET /api/user/send/status` - 获取寄件状态
- `DELETE /api/user/send/cancel` - 取消寄件流程

#### API使用示例

```bash
# 获取系统状态
curl -X GET "http://localhost:8000/api/system/status"

# 开启1号舱门
curl -X POST "http://localhost:8000/api/door/operate" \
     -H "Content-Type: application/json" \
     -d '{"position": 1, "operation": "open"}'

# 启动用户取件（取件码：123456）
curl -X POST "http://localhost:8000/api/user/pickup" \
     -H "Content-Type: application/json" \
     -d '{"pickup_code": "123456"}'
```

## 业务流程

### 1. 无人机存件流程

1. 检查存储容量
2. 设置取件码
3. 等待无人机到达
4. 确认无人机起降
5. 控制舵机取包裹
6. 存储包裹到指定位置
7. 记录存件信息

### 2. 用户取件流程

1. 用户输入取件码
2. 验证取件码有效性
3. 获取包裹位置
4. 开启对应舱门
5. 等待用户取件
6. 确认取件完成
7. 关闭舱门

### 3. 用户寄件流程

1. 检查寄件容量
2. 用户输入寄件码
3. 提供空寄件箱
4. 用户放入物品
5. 称重确认
6. 存储到指定位置
7. 记录寄件信息

## 系统监控

系统提供实时监控功能：

- **设备状态**: PLC连接状态、舱门状态、舵机状态
- **系统报警**: 硬件故障、通信异常、安全报警
- **气象数据**: 风速、风向、温度、湿度、气压、降雨量
- **存储容量**: 各类存储区域的使用情况
- **历史数据**: 状态历史、报警历史、气象历史

## 配置说明

### PLC配置

```python
PLC_CONFIG = {
    'host': '192.168.1.100',    # PLC IP地址
    'port': 502,                # Modbus端口
    'timeout': 5,               # 连接超时
    'unit_id': 1,               # 设备单元ID
    'retry_count': 3,           # 重试次数
    'retry_delay': 1            # 重试延迟
}
```

### Web服务配置

```python
WEB_CONFIG = {
    'host': '0.0.0.0',          # 服务器地址
    'port': 8000,               # 服务器端口
    'debug': False              # 调试模式
}
```

### 日志配置

```python
LOG_CONFIG = {
    'level': 'INFO',            # 日志级别
    'file': 'logs/system.log',  # 日志文件
    'rotation': '10 MB',        # 日志轮转大小
    'retention': '30 days'      # 日志保留时间
}
```

## 故障排除

### 常见问题

1. **PLC连接失败**
   - 检查网络连接
   - 确认PLC IP地址和端口
   - 检查防火墙设置

2. **Web服务启动失败**
   - 检查端口是否被占用
   - 确认Python依赖包已安装
   - 查看错误日志

3. **舱门控制异常**
   - 检查PLC连接状态
   - 确认寄存器地址配置
   - 查看系统报警信息

### 日志查看

系统日志保存在 `logs/system.log` 文件中，可以通过以下方式查看：

```bash
# 查看最新日志
tail -f logs/system.log

# 查看错误日志
grep "ERROR" logs/system.log
```

## 开发说明

### 添加新功能

1. 在 `config.py` 中添加相关配置
2. 创建对应的控制器模块
3. 在 `web_api.py` 中添加API接口
4. 更新 `main.py` 中的初始化逻辑

### 代码规范

- 使用Python 3.8+语法
- 遵循PEP 8代码规范
- 添加类型注解
- 编写详细的文档字符串
- 使用loguru进行日志记录

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请联系开发团队。