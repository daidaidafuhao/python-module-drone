# -*- coding: utf-8 -*-
"""
Web API接口模块
提供RESTful API服务，方便外部系统调用无人机柜的各种功能
"""

from math import log
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
from loguru import logger
from config import SECURITY_CONFIG

# 全局变量存储有效的安全key - 从配置文件加载
valid_keys = SECURITY_CONFIG['valid_keys'].copy()

# 安全校验中间件
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 跳过静态文件和设置key的请求
        if (
            request.url.path.startswith("/static/") or 
            request.url.path == "/" or
            "/key=" in str(request.url) or
            request.url.path == "/api/health"
        ):
            response = await call_next(request)
            return response
        
        # 检查key参数
        key = request.query_params.get("key")
        if not key or key not in valid_keys:
            # 如果是API请求，返回JSON错误
            if request.url.path.startswith('/api/'):
                return JSONResponse(
                    status_code=401,
                    content={"success": False, "message": "安全校验失败：key丢失或无效，请通过正确的链接重新访问"}
                )
            # 如果是页面请求，返回错误页面
            else:
                from fastapi.responses import HTMLResponse
                try:
                    with open('templates/key_error.html', 'r', encoding='utf-8') as f:
                        error_html = f.read()
                    return HTMLResponse(content=error_html, status_code=401)
                except FileNotFoundError:
                    return HTMLResponse(
                        content="<h1>安全验证失败</h1><p>key丢失或无效，请通过正确的链接重新访问</p>",
                        status_code=401
                    )
        
        response = await call_next(request)
        return response

# 导入控制器模块
from modbus_client import modbus_client
from door_controller import door_controller
from drone_storage_controller import drone_storage_controller
from user_pickup_controller import user_pickup_controller
from user_send_controller import user_send_controller
from system_monitor import system_monitor
from config import WEB_CONFIG

# 导入新的服务模块
from services.config_manager import config_manager
from services.machine_manager import machine_manager
from api.machine_api import router as machine_router

# 创建FastAPI应用
app = FastAPI(
    title="无人机快递柜控制系统API",
    description="提供无人机快递柜的完整控制接口",
    version="1.0.0"
)

# 添加安全校验中间件
app.add_middleware(SecurityMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 配置模板
templates = Jinja2Templates(directory="templates")

# 注册机器管理路由
app.include_router(machine_router)

# 请求模型定义
class DoorOperationRequest(BaseModel):
    """舱门操作请求模型"""
    position: int = Field(..., ge=1, le=6, description="舱门位置 (1-6)")
    operation: str = Field(..., description="操作类型: open/close")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class DroneStorageRequest(BaseModel):
    """无人机存件请求模型"""
    pickup_code: str = Field(..., min_length=6, max_length=6, description="6位取件码")
    package_info: Optional[Dict[str, Any]] = Field(None, description="包裹信息")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class UserPickupRequest(BaseModel):
    """用户取件请求模型"""
    pickup_code: str = Field(..., min_length=6, max_length=6, description="6位取件码")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class UserSendRequest(BaseModel):
    """用户寄件请求模型"""
    send_code: str = Field(..., min_length=6, max_length=6, description="6位寄件码")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class ModbusWriteRequest(BaseModel):
    """Modbus写入请求模型"""
    address: int = Field(..., description="寄存器地址")
    values: List[int] = Field(..., description="要写入的值列表")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class ModbusReadRequest(BaseModel):
    """Modbus读取请求模型"""
    address: int = Field(..., description="寄存器地址")
    machine_name: Optional[str] = Field(None, description="机器名称，不指定则使用默认机器")

class ApiResponse(BaseModel):
    """API响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# 工具函数
def create_response(success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> ApiResponse:
    """创建标准API响应"""
    return ApiResponse(success=success, message=message, data=data)

def get_machine_connection(machine_name: Optional[str] = None):
    """获取机器连接"""
    try:
        if machine_name:
            # 使用指定机器
            connection = machine_manager.get_connection(machine_name)
            if connection:
                client = connection.get_client()
                if not client or not client.is_connected:
                    raise HTTPException(status_code=503, detail=f"机器 {machine_name} 连接不可用")
                return client
            else:
                raise HTTPException(status_code=404, detail=f"机器 {machine_name} 未找到")
        else:
            # 使用默认连接
            return modbus_client
    except Exception as e:
        logger.error(f"获取机器连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取机器连接失败: {str(e)}")


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def machine_list_page(request: Request):
    """机器列表页面"""
    return templates.TemplateResponse("machine_list.html", {"request": request})


@app.get("/machine/{machine_name}/key={key_value}")
async def validate_security_key(machine_name: str, key_value: str):
    """验证安全校验key并重定向到机器控制页面"""
    try:
        # 验证key是否在配置的有效key集合中
        if key_value not in valid_keys:
            logger.warning(f"无效的安全key: {key_value} for machine: {machine_name}")
            raise HTTPException(status_code=401, detail="无效的安全key")
        
        logger.info(f"安全key验证成功: {key_value} for machine: {machine_name}")
        
        # 重定向到机器控制页面，并在URL中包含key
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"/machine/{machine_name}?key={key_value}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证安全key失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"验证安全key失败: {str(e)}")

@app.get("/machine/{machine_name}", response_class=HTMLResponse)
async def machine_control_page(request: Request, machine_name: str):
    """机器控制页面"""
    try:
        # 获取机器配置信息
        machine_info = config_manager.get_plc_config(machine_name)
        if not machine_info:
            raise HTTPException(status_code=404, detail=f"机器 {machine_name} 未找到")
        
        # 从数据库获取机器详细信息
        from models.drone_cabinet import DroneCabinetDAO
        cabinet = DroneCabinetDAO.get_by_code(machine_name)
        
        location = '未设置'
        if cabinet:
            location = cabinet.address or f"{cabinet.name} ({cabinet.code})"
        
        return templates.TemplateResponse("machine_control.html", {
            "request": request,
            "machine_name": machine_name,
            "location": location,
            "plc_host": machine_info.get('host', ''),
            "plc_port": machine_info.get('port', '')
        })
    except Exception as e:
        logger.error(f"获取机器控制页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 机器管理API ====================

@app.get("/api/machines", response_model=ApiResponse)
async def get_machines_list():
    """获取所有机器列表"""
    try:
        machine_names = config_manager.get_machine_list()
        result = []
        
        for machine_name in machine_names:
            # 获取机器配置信息
            plc_config = config_manager.get_plc_config(machine_name)
            
            # 测试连接状态
            is_online = False
            try:
                test_result = machine_manager.test_machine_connection(machine_name)
                is_online = test_result.get('success', False)
            except:
                pass
            
            result.append({
                'machine_name': machine_name,
                'location': plc_config.get('location', ''),
                'plc_host': plc_config.get('host', ''),
                'plc_port': plc_config.get('port', 0),
                'is_online': is_online,
                'updated_at': ''
            })
        
        return create_response(True, "获取机器列表成功", {'machines': result})
    except Exception as e:
        logger.error(f"获取机器列表失败: {e}")
        return create_response(False, f"获取机器列表失败: {str(e)}")


@app.get("/api/machines/{machine_name}/test", response_model=ApiResponse)
async def test_machine_connection(machine_name: str):
    """测试机器连接"""
    try:
        result = machine_manager.test_machine_connection(machine_name)
        return create_response(
            success=result['success'],
            message=result.get('message', '连接测试完成'),
            data=result
        )
    except Exception as e:
        logger.error(f"测试机器连接失败: {e}")
        return create_response(False, f"测试连接失败: {str(e)}")


@app.get("/api/machines/{machine_name}/status", response_model=ApiResponse)
async def get_machine_status(machine_name: str):
    """获取机器状态"""
    try:
        # 首先检查机器是否在配置中
        if not config_manager.is_machine_available(machine_name):
            return create_response(False, "机器未找到")
        
        # 尝试获取连接
        connection = machine_manager.get_connection(machine_name)
        
        if connection:
            # 如果连接存在，返回详细状态
            stats = connection.get_stats()
            return create_response(True, "获取状态成功", {
                'connected': stats['connected'],
                'last_communication': stats.get('last_used', '无'),
                'system_status': '正常' if stats['connected'] else '离线'
            })
        else:
            # 如果连接不存在，返回基本状态
            return create_response(True, "获取状态成功", {
                'connected': False,
                'last_communication': '无',
                'system_status': '离线'
            })
    except Exception as e:
        logger.error(f"获取机器状态失败: {e}")
        return create_response(False, f"获取状态失败: {str(e)}")


# ==================== 舱门控制API ====================

@app.post("/api/machines/{machine_name}/door/{action}", response_model=ApiResponse)
async def control_machine_door(machine_name: str, action: str):
    """控制指定机器的舱门"""
    try:
        if action not in ['open', 'close']:
            return create_response(False, "无效的操作类型，只支持 open 或 close")
        
        # 获取机器连接
        client = get_machine_connection(machine_name)
        
        # 执行舱门操作
        if action == 'open':
            result = door_controller.open_door(1, client=client)  # 默认操作第1个舱门
        else:
            result = door_controller.close_door(1, client=client)
        
        if result:
            return create_response(True, f"舱门{action}操作成功")
        else:
            return create_response(False, f"舱门{action}操作失败")
    
    except Exception as e:
        logger.error(f"舱门控制失败: {e}")
        return create_response(False, f"舱门控制失败: {str(e)}")


@app.get("/api/machines/{machine_name}/door/status", response_model=ApiResponse)
async def get_machine_door_status(machine_name: str):
    """获取指定机器的舱门状态"""
    try:
        client = get_machine_connection(machine_name)
        status = door_controller.get_door_status(1, client)  # 默认查询第1个舱门
        
        return create_response(True, "获取舱门状态成功", {
            'status': status,
            'door_position': 1
        })
    
    except Exception as e:
        logger.error(f"获取舱门状态失败: {e}")
        return create_response(False, f"获取舱门状态失败: {str(e)}")

@app.get("/api/machines/{machine_name}/pickup/status", response_model=ApiResponse)
async def get_machine_pickup_status(machine_name: str):
    """获取指定机器的取件状态"""
    try:
        client = get_machine_connection(machine_name)
        # 读取取件格口状态 (地址0xBBF)
        pickup_status = client.read_holding_register(0xBBF)
        
        status_text = "正常"
        if pickup_status == 10:  # 0x0A
            status_text = "无包裹"
        elif pickup_status is None:
            status_text = "读取失败"
        
        return create_response(True, "获取取件状态成功", {
            'status': status_text,
            'raw_value': pickup_status
        })
    
    except Exception as e:
        logger.error(f"获取取件状态失败: {e}")
        return create_response(False, f"获取取件状态失败: {str(e)}")

@app.get("/api/machines/{machine_name}/send/status", response_model=ApiResponse)
async def get_machine_send_status(machine_name: str):
    """获取指定机器的寄件状态"""
    try:
        client = get_machine_connection(machine_name)
        # 读取寄件格口状态 (地址0xBBE)
        send_status = client.read_holding_register(0xBBE)
        
        status_text = "正常"
        if send_status == 10:  # 0x0A
            status_text = "已存满"
        elif send_status is None:
            status_text = "读取失败"
        
        return create_response(True, "获取寄件状态成功", {
            'status': status_text,
            'raw_value': send_status
        })
    
    except Exception as e:
        logger.error(f"获取寄件状态失败: {e}")
        return create_response(False, f"获取寄件状态失败: {str(e)}")


# ==================== 存件流程API ====================

@app.post("/api/machines/{machine_name}/storage/confirm-start", response_model=ApiResponse)
async def confirm_storage_start(machine_name: str):
    """确认存件开始"""
    try:
        client = get_machine_connection(machine_name)
        
        # 检查存件格口状态 (地址0xBBE)
        storage_status = client.read_holding_register(0xBBE)
        if storage_status == 10:  # 0x0A
            return create_response(False, "当前机柜已存满，无法执行存件流程")
        elif storage_status == 11:  # 0x0B
            return create_response(True, "机柜未存满，可以执行存件流程")
        else:
            return create_response(False, f"存件格口状态异常: {storage_status}")
    
    except Exception as e:
        logger.error(f"确认存件开始失败: {e}")
        return create_response(False, f"确认存件开始失败: {str(e)}")


@app.post("/api/machines/{machine_name}/storage/execute", response_model=ApiResponse)
async def execute_storage_process(machine_name: str, request: Request):
    """执行完整存件流程"""
    try:
        data = await request.json()
        pickup_code_first = data.get('pickup_code_first')
        pickup_code_last = data.get('pickup_code_last')
        
        if not pickup_code_first or not pickup_code_last:
            return create_response(False, "请提供完整的取件码")
        
        client = get_machine_connection(machine_name)
        
        # 1. 开舱门
        door_result = door_controller.open_door(1, client=client)
        if not door_result:
            return create_response(False, "开舱门失败")
        
        # 2. 等待无人机降落
        # 在地址0xBB9写10(0x0A)代表飞机降落完成
        client.write_holding_register(0xBB9, 10)
        
        # 等待确认：读地址0xBB9值为11(0x0B)代表下位已确认停机坪有飞机
        import time
        for _ in range(30):  # 最多等待30秒
            status = client.read_holding_register(0xBB9)
            if status == 11:
                break
            time.sleep(1)
        else:
            return create_response(False, "等待无人机降落确认超时")
        
        # 3. 在地址0xBBA写110（0x6E）代表开始执行存件动作
        client.write_holding_register(0xBBA, 110)
        logger.info(f"开始执行存件动作")
        
        # 4. 下发取件码 (地址0xBC0和0xBC1)
        logger.info(f"下发取件码 (地址0xBC0和0xBC1)")
        client.write_holding_register(0xBC0, int(pickup_code_first))
        client.write_holding_register(0xBC1, int(pickup_code_last))
        
        logger.info(" 舵机打开前延时50秒让货叉到达指定位置")
        # 7. 舵机打开后延时40秒让货叉到达指定位置
        time.sleep(40)
        logger.info("延时完成")
        
        # 5. 读地址0xBBB值为1(0x01)代表无人机可以打开舵机
        for _ in range(30):
            servo_status = client.read_holding_register(0xBBB)
            if servo_status == 1:
                # 无人机打开舵机后在地址0xBBB写10(0x0A)
                client.write_holding_register(0xBBB, 10)
                break
            time.sleep(1)
        else:
            return create_response(False, "等待舵机打开信号超时")
        
        # 6. 等待舵机打开确认
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 11:  # 0x0B 下位已确认舵机打开
                break
            time.sleep(1)
        else:
            return create_response(False, "等待舵机打开确认超时")
        

        # 8. 读取包裹操作类型并分支处理
        # 循环读取直到获得120或122的值
        for _ in range(60):  # 最多等待60秒
            package_status = client.read_holding_register(0xBBA)
            if package_status == 120 or package_status == 122:
                break
            time.sleep(1)
        else:
            return create_response(False, "等待包裹操作类型超时")
        logger.info(f"包裹操作类型: {package_status}")
        if package_status == 120:  # 0x78 取空包裹分支
            logger.info("取空包裹分支...")
            # 等待取件包裹到位
            for _ in range(30):
                status = client.read_holding_register(0xBBB)
                if status == 2:  # 0x02 取件包裹到位
                    break
                time.sleep(1)
            
            # 取件包裹到位后延时10秒
            time.sleep(10)
            
            # 关闭舵机
            client.write_holding_register(0xBBB, 20)  # 0x14 无人机已关闭舵机
            
            # 等待舵机关闭确认
            for _ in range(10):
                status = client.read_holding_register(0xBBB)
                if status == 21:  # 0x15 下位已确认舵机关闭
                    break
                time.sleep(1)
            
            # 检查是否可以起飞
            # 循环读取直到获得121的值
            for _ in range(30):  # 最多等待30秒
                takeoff_status = client.read_holding_register(0xBBA)
                logger.info(f"取空包裹分支 - 读取到的takeoff_status: {takeoff_status}")
                if takeoff_status == 121:  # 0x79 无人机可以起飞
                    break
                time.sleep(1)
            else:
                return create_response(False, "等待无人机起飞信号超时")
            
            if takeoff_status == 121:  # 0x79 无人机可以起飞
                logger.info("取空包裹分支 - 无人机可以起飞")
                client.write_holding_register(0xBB9, 20)  # 0x14 停机坪无飞机
                
                # 等待起飞确认
                for _ in range(30):
                    status = client.read_holding_register(0xBB9)
                    if status == 21:  # 0x15 下位已确认停机坪无飞机
                        break
                    time.sleep(1)
                else:
                    logger.error("取空包裹分支 - 等待起飞确认超时")
                    return create_response(False, "等待起飞确认超时")
                
            logger.info("取空包裹分支 - 无人机起飞后延时10秒")
            # 无人机起飞后延时10秒
            time.sleep(10)
            
            # 关闭舱门
            door_result = door_controller.close_door(1, client=client)
            if not door_result:
                return create_response(False, "关闭舱门失败")
            
            # 读取结果（取空包裹分支读取两个地址）
            result_1 = client.read_holding_register(0xBBC)
            result_2 = client.read_holding_register(0xBBD)
            
            return create_response(True, "存件流程执行成功（取空包裹）", {
                'result_code_1': result_1,
                'result_code_2': result_2,
                'package_type': 'empty_package'
            })
            
        elif package_status == 122:  # 0x7A 不取空包裹分支
            logger.info("不取空包裹分支...")
                       
            # 延迟关闭舵机
            time.sleep(10)
            logger.info("准备关闭舵机...")
            client.write_holding_register(0xBBB, 20)  # 0x14 无人机已关闭舵机
            
            logger.info("等待舵机关闭确认...")
            # 等待舵机关闭确认
            for _ in range(10):
                status = client.read_holding_register(0xBBB)
                if status == 21:  # 0x15 下位已确认舵机关闭，无人机可以起飞
                    break
                time.sleep(1)
            else:
                logger.error("等待舵机关闭确认超时")
                return create_response(False, "等待舵机关闭确认超时")
            
            # 无人机起飞
            logger.debug("准备起飞...")
            client.write_holding_register(0xBB9, 20)  # 0x14 停机坪无飞机
            
            # 等待起飞确认
            for _ in range(30):
                status = client.read_holding_register(0xBB9)
                if status == 21:  # 0x15 下位已确认停机坪无飞机
                    break
                time.sleep(1)
            else:
                logger.error("等待起飞确认超时")
                return create_response(False, "等待起飞确认超时")
            
            logger.info("无人机起飞后延时10秒")
            # 无人机起飞后延时10秒
            time.sleep(10)
            
            # 关闭舱门
            door_result = door_controller.close_door(1, client=client)
            if not door_result:
                return create_response(False, "关闭舱门失败")
            
            # 读取结果（不取空包裹分支只读取一个地址）
            result_1 = client.read_holding_register(0xBBC)
            logger.info(f"读取到的结果: {result_1}")
            return create_response(True, "存件流程执行成功（不取空包裹）", {
                'result_code_1': result_1,
                'package_type': 'no_empty_package'
            })
            
        else:
             return create_response(False, f"未知的包裹操作类型: {package_status}")
    
    except Exception as e:
        logger.error(f"执行存件流程失败: {e}")
        return create_response(False, f"执行存件流程失败: {str(e)}")


@app.post("/api/machines/{machine_name}/storage/drone-landed", response_model=ApiResponse)
async def confirm_drone_landed(machine_name: str):
    """确认无人机降落"""
    try:
        client = get_machine_connection(machine_name)
        
        # 在地址0xBB9写10(0x0A)代表飞机降落完成
        client.write_holding_register(0xBB9, 10)
        
        # 等待确认：读地址0xBB9值为11(0x0B)代表下位已确认停机坪有飞机
        import time
        for _ in range(30):  # 最多等待30秒
            status = client.read_holding_register(0xBB9)
            if status == 11:
                # 在地址0xBBA写110（0x6E）代表开始执行存件动作
                client.write_holding_register(0xBBA, 110)
                return create_response(True, "无人机降落确认成功，开始存件动作")
            time.sleep(1)
        
        return create_response(False, "等待无人机降落确认超时")
    
    except Exception as e:
        logger.error(f"确认无人机降落失败: {e}")
        return create_response(False, f"确认无人机降落失败: {str(e)}")


@app.post("/api/machines/{machine_name}/storage/servo-open", response_model=ApiResponse)
async def confirm_servo_open(machine_name: str):
    """确认舵机打开"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB值为1(0x01)代表无人机可以打开舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 1:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为1")
        
        # 无人机打开舵机后在地址0xBBB写10(0x0A)代表无人机已打开舵机
        client.write_holding_register(0xBBB, 10)
        
        # 等待确认：读地址0xBBB值为11(0x0B)代表下位已确认舵机打开
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 11:
                return create_response(True, "舵机打开确认成功")
            time.sleep(1)
        
        return create_response(False, "等待舵机打开确认超时")
    
    except Exception as e:
        logger.error(f"确认舵机打开失败: {e}")
        return create_response(False, f"确认舵机打开失败: {str(e)}")


@app.post("/api/machines/{machine_name}/storage/servo-close", response_model=ApiResponse)
async def confirm_servo_close(machine_name: str):
    """确认舵机关闭"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB读到值2(0x02)，代表取件包裹到位无人机可关舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 2:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为2")
        
        # 无人机关闭舵机后在地址0xBBB写20(0x14)代表无人机已关闭舵机
        client.write_holding_register(0xBBB, 20)
        
        # 等待确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 21:
                return create_response(True, "舵机关闭确认成功")
            time.sleep(1)
        
        return create_response(False, "等待舵机关闭确认超时")
    
    except Exception as e:
        logger.error(f"确认舵机关闭失败: {e}")
        return create_response(False, f"确认舵机关闭失败: {str(e)}")


@app.post("/api/machines/{machine_name}/storage/drone-takeoff", response_model=ApiResponse)
async def confirm_drone_takeoff(machine_name: str):
    """确认无人机起飞"""
    try:
        client = get_machine_connection(machine_name)
        
        # 1. 先检查舵机关闭确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 21:
            return create_response(False, f"舵机未关闭确认，当前状态: {servo_status}，期望值为21")
        
        # 2. 再检查起飞许可：读地址0xBBA值为121(0x79)或122(0x7A)代表无人机可以起飞
        takeoff_status = client.read_holding_register(0xBBA)
        if takeoff_status not in [121, 122]:
            return create_response(False, f"起飞状态异常: {takeoff_status}，期望值为121或122")
        
        # 无人机起飞后，在地址0xBB9写20(0x14)代表停机坪无飞机
        client.write_holding_register(0xBB9, 20)
        
        # 等待确认：读地址0xBB9值为21(0x15)代表下位已确认停机坪无飞机
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBB9)
            if status == 21:
                # 关闭舱门
                door_result = door_controller.close_door(1, client=client)
                if door_result:
                    # 读取存件结果 (地址0xBBC、0xBBD)
                    result_1 = client.read_holding_register(0xBBC)
                    result_2 = client.read_holding_register(0xBBD)
                    return create_response(True, "存件流程完成", {
                        'result_code_1': result_1,
                        'result_code_2': result_2
                    })
                else:
                    return create_response(False, "关闭舱门失败")
            time.sleep(1)
        
        return create_response(False, "等待无人机起飞确认超时")
    
    except Exception as e:
        logger.error(f"确认无人机起飞失败: {e}")
        return create_response(False, f"确认无人机起飞失败: {str(e)}")


# ==================== 取件流程API ====================

@app.post("/api/machines/{machine_name}/pickup/set-code", response_model=ApiResponse)
async def set_pickup_code(machine_name: str, request: Request):
    """设置取件码"""
    try:
        data = await request.json()
        pickup_code_first = data.get('pickup_code_first')
        pickup_code_last = data.get('pickup_code_last')
        
        if not pickup_code_first or not pickup_code_last:
            return create_response(False, "请提供完整的取件码")
        
        client = get_machine_connection(machine_name)
        
        # 设置取件码 (地址0xBC2和0xBC3)
        client.write_holding_register(0xBC2, int(pickup_code_first))
        client.write_holding_register(0xBC3, int(pickup_code_last))
        
        return create_response(True, "取件码设置成功")
    
    except Exception as e:
        logger.error(f"设置取件码失败: {e}")
        return create_response(False, f"设置取件码失败: {str(e)}")


@app.post("/api/machines/{machine_name}/pickup/start", response_model=ApiResponse)
async def start_pickup_process(machine_name: str, request: Request):
    """开始取件流程"""
    try:
        data = await request.json()
        pickup_code_first = data.get('pickup_code_first')
        pickup_code_last = data.get('pickup_code_last')
        
        if not pickup_code_first or not pickup_code_last:
            return create_response(False, "请提供完整的取件码")
        
        client = get_machine_connection(machine_name)
        
        # 检查取件格口状态 (地址0xBBF)
        pickup_status = client.read_holding_register(0xBBF)
        if pickup_status == 10:  # 0x0A
            return create_response(False, "当前机柜无包裹，无法执行取件流程")
        
        # 设置取件码 (地址0xBC2和0xBC3)
        client.write_holding_register(0xBC2, int(pickup_code_first))
        client.write_holding_register(0xBC3, int(pickup_code_last))
        
        # 开始取件流程：先开舱门
        door_result = door_controller.open_door(1, client=client)
        if not door_result:
            return create_response(False, "开舱门失败")
        
        return create_response(True, "取件流程启动成功，请等待无人机降落")
    
    except Exception as e:
        logger.error(f"启动取件流程失败: {e}")
        return create_response(False, f"启动取件流程失败: {str(e)}")


@app.post("/api/machines/{machine_name}/pickup/drone-landed", response_model=ApiResponse)
async def confirm_pickup_drone_landed(machine_name: str):
    """确认取件无人机降落"""
    try:
        client = get_machine_connection(machine_name)
        
        # 在地址0xBB9写10(0x0A)代表飞机降落完成
        client.write_holding_register(0xBB9, 10)
        
        # 等待确认：读地址0xBB9值为11(0x0B)代表下位已确认停机坪有飞机
        import time
        for _ in range(30):  # 最多等待30秒
            status = client.read_holding_register(0xBB9)
            if status == 11:
                # 在地址0xBBA写120（0x78）代表开始执行取件动作
                client.write_holding_register(0xBBA, 120)
                return create_response(True, "无人机降落确认成功，开始取件动作")
            time.sleep(1)
        
        return create_response(False, "等待无人机降落确认超时")
    
    except Exception as e:
        logger.error(f"确认取件无人机降落失败: {e}")
        return create_response(False, f"确认取件无人机降落失败: {str(e)}")


@app.post("/api/machines/{machine_name}/pickup/servo-open", response_model=ApiResponse)
async def confirm_pickup_servo_open(machine_name: str):
    """确认取件舵机打开"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB值为1(0x01)代表无人机可以打开舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 1:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为1")
        
        # 无人机打开舵机后在地址0xBBB写10(0x0A)代表无人机已打开舵机
        client.write_holding_register(0xBBB, 10)
        
        # 等待确认：读地址0xBBB值为11(0x0B)代表下位已确认舵机打开
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 11:
                return create_response(True, "取件舵机打开确认成功")
            time.sleep(1)
        
        return create_response(False, "等待取件舵机打开确认超时")
    
    except Exception as e:
        logger.error(f"确认取件舵机打开失败: {e}")
        return create_response(False, f"确认取件舵机打开失败: {str(e)}")


@app.post("/api/machines/{machine_name}/pickup/servo-close", response_model=ApiResponse)
async def confirm_pickup_servo_close(machine_name: str):
    """确认取件舵机关闭"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB读到值2(0x02)，代表存件包裹到位无人机可关舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 2:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为2")
        
        # 无人机关闭舵机后在地址0xBBB写20(0x14)代表无人机已关闭舵机
        client.write_holding_register(0xBBB, 20)
        
        # 等待确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 21:
                return create_response(True, "取件舵机关闭确认成功")
            time.sleep(1)
        
        return create_response(False, "等待取件舵机关闭确认超时")
    
    except Exception as e:
        logger.error(f"确认取件舵机关闭失败: {e}")
        return create_response(False, f"确认取件舵机关闭失败: {str(e)}")


@app.post("/api/machines/{machine_name}/pickup/drone-takeoff", response_model=ApiResponse)
async def confirm_pickup_drone_takeoff(machine_name: str):
    """确认取件无人机起飞"""
    try:
        client = get_machine_connection(machine_name)
        
        # 1. 先检查舵机关闭确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 21:
            return create_response(False, f"舵机未关闭确认，当前状态: {servo_status}，期望值为21")
        
        # 2. 再检查起飞许可：读地址0xBBA值为131(0x83)代表无人机可以起飞
        takeoff_status = client.read_holding_register(0xBBA)
        if takeoff_status != 131:
            return create_response(False, f"起飞状态异常: {takeoff_status}，期望值为131")
        
        # 无人机起飞后，在地址0xBB9写20(0x14)代表停机坪无飞机
        client.write_holding_register(0xBB9, 20)
        
        # 等待确认：读地址0xBB9值为21(0x15)代表下位已确认停机坪无飞机
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBB9)
            if status == 21:
                # 关闭舱门
                door_result = door_controller.close_door(1, client=client)
                if door_result['success']:
                    # 读取取件结果 (地址0xBC4、0xBC5)
                    result_1 = client.read_holding_register(0xBC4)
                    result_2 = client.read_holding_register(0xBC5)
                    return create_response(True, "取件流程完成", {
                        'result_code_1': result_1,
                        'result_code_2': result_2
                    })
                else:
                    return create_response(False, f"关闭舱门失败: {door_result.get('message')}")
            time.sleep(1)
        
        return create_response(False, "等待取件无人机起飞确认超时")
    
    except Exception as e:
        logger.error(f"确认取件无人机起飞失败: {e}")
        return create_response(False, f"确认取件无人机起飞失败: {str(e)}")


# ==================== 寄件流程API ====================

@app.post("/api/machines/{machine_name}/send/set-code", response_model=ApiResponse)
async def set_send_code(machine_name: str, request: Request):
    """设置寄件码"""
    try:
        data = await request.json()
        send_code_first = data.get('send_code_first')
        send_code_last = data.get('send_code_last')
        
        if not send_code_first or not send_code_last:
            return create_response(False, "请提供完整的寄件码")
        
        client = get_machine_connection(machine_name)
        
        # 检查寄件格口状态 (地址0xBD2)
        send_status = client.read_holding_register(0xBD2)
        if send_status == 11:  # 0x0B - 无空寄件箱不可寄件
            return create_response(False, "当前无空寄件箱，无法设置寄件码")
        elif send_status != 10:  # 0x0A - 有空寄件箱可寄件
            return create_response(False, f"寄件格口状态异常，无法设置寄件码: {send_status}")
        
        # 设置寄件码 (地址0xBD0和0xBD1)
        client.write_holding_register(0xBD0, int(send_code_first))
        client.write_holding_register(0xBD1, int(send_code_last))
        
        return create_response(True, "寄件码设置成功")
    
    except Exception as e:
        logger.error(f"设置寄件码失败: {e}")
        return create_response(False, f"设置寄件码失败: {str(e)}")


@app.post("/api/machines/{machine_name}/send/start", response_model=ApiResponse)
async def start_send_process(machine_name: str, request: Request):
    """开始寄件流程"""
    try:
        data = await request.json()
        send_code_first = data.get('send_code_first')
        send_code_last = data.get('send_code_last')
        
        if not send_code_first or not send_code_last:
            return create_response(False, "请提供完整的寄件码")
        
        client = get_machine_connection(machine_name)
        
        # 检查寄件格口状态 (地址0xBD2)
        send_status = client.read_holding_register(0xBD2)
        if send_status == 11:  # 0x0B - 无空寄件箱不可寄件
            return create_response(False, "当前无空寄件箱，无法执行寄件流程")
        elif send_status != 10:  # 0x0A - 有空寄件箱可寄件
            return create_response(False, f"寄件格口状态异常: {send_status}")
        
        # 设置寄件码 (地址0xBD0和0xBD1)
        client.write_holding_register(0xBD0, int(send_code_first))
        client.write_holding_register(0xBD1, int(send_code_last))
        
        return create_response(True, "寄件码设置成功，请在交互界面输入寄件码进行取空箱操作，系统将监视0xBC7状态")
    
    except Exception as e:
        logger.error(f"启动寄件流程失败: {e}")
        return create_response(False, f"启动寄件流程失败: {str(e)}")


@app.get("/api/machines/{machine_name}/send/operation-status", response_model=ApiResponse)
async def get_send_operation_status(machine_name: str):
    """获取寄件操作状态 (监视0xBC7)"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读取寄件操作状态 (地址0xBC7)
        operation_status = client.read_holding_register(0xBC7)
        
        # 解析状态含义
        status_map = {
            210: "正在取空箱",  # 0xD2
            211: "取空箱完成",  # 0xD3
            220: "用户存寄件箱中",  # 0xDC
            230: "正在存寄件箱",  # 0xE6
            231: "存寄件箱完成"  # 0xE7
        }
        
        status_description = status_map.get(operation_status, f"未知状态: {operation_status}")
        
        return create_response(True, "获取寄件操作状态成功", {
            "raw_status": operation_status,
            "status_description": status_description,
            "hex_value": f"0x{operation_status:X}" if operation_status is not None else None
        })
    
    except Exception as e:
        logger.error(f"获取寄件操作状态失败: {e}")
        return create_response(False, f"获取寄件操作状态失败: {str(e)}")


@app.post("/api/machines/{machine_name}/shipping/start", response_model=ApiResponse)
async def start_shipping_process(machine_name: str, request: Request):
    """开始寄件流程"""
    try:
        data = await request.json()
        pickup_code_first = data.get('pickup_code_first')
        pickup_code_last = data.get('pickup_code_last')
        
        if not pickup_code_first or not pickup_code_last:
            return create_response(False, "请提供完整的取件码")
        
        client = get_machine_connection(machine_name)
        
        # 检查寄件格口状态 (地址0xBC0)
        shipping_status = client.read_holding_register(0xBC0)
        if shipping_status == 10:  # 0x0A
            return create_response(False, "当前机柜已存满，无法执行寄件流程")
        
        # 设置取件码 (地址0xBC6和0xBC7)
        client.write_holding_register(0xBC6, int(pickup_code_first))
        client.write_holding_register(0xBC7, int(pickup_code_last))
        
        # 开始寄件流程：先开舱门
        door_result = door_controller.open_door(1, client=client)
        if not door_result:
            return create_response(False, "开舱门失败")
        
        return create_response(True, "寄件流程启动成功，请等待无人机降落")
    
    except Exception as e:
        logger.error(f"启动寄件流程失败: {e}")
        return create_response(False, f"启动寄件流程失败: {str(e)}")


@app.post("/api/machines/{machine_name}/shipping/drone-landed", response_model=ApiResponse)
async def confirm_shipping_drone_landed(machine_name: str):
    """确认寄件无人机降落"""
    try:
        client = get_machine_connection(machine_name)
        
        # 在地址0xBB9写10(0x0A)代表飞机降落完成
        client.write_holding_register(0xBB9, 10)
        
        # 等待确认：读地址0xBB9值为11(0x0B)代表下位已确认停机坪有飞机
        import time
        for _ in range(30):  # 最多等待30秒
            status = client.read_holding_register(0xBB9)
            if status == 11:
                # 在地址0xBBA写130（0x82）代表开始执行寄件动作
                client.write_holding_register(0xBBA, 130)
                return create_response(True, "无人机降落确认成功，开始寄件动作")
            time.sleep(1)
        
        return create_response(False, "等待无人机降落确认超时")
    
    except Exception as e:
        logger.error(f"确认寄件无人机降落失败: {e}")
        return create_response(False, f"确认寄件无人机降落失败: {str(e)}")


@app.post("/api/machines/{machine_name}/shipping/servo-open", response_model=ApiResponse)
async def confirm_shipping_servo_open(machine_name: str):
    """确认寄件舵机打开"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB值为1(0x01)代表无人机可以打开舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 1:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为1")
        
        # 无人机打开舵机后在地址0xBBB写10(0x0A)代表无人机已打开舵机
        client.write_holding_register(0xBBB, 10)
        
        # 等待确认：读地址0xBBB值为11(0x0B)代表下位已确认舵机打开
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 11:
                return create_response(True, "寄件舵机打开确认成功")
            time.sleep(1)
        
        return create_response(False, "等待寄件舵机打开确认超时")
    
    except Exception as e:
        logger.error(f"确认寄件舵机打开失败: {e}")
        return create_response(False, f"确认寄件舵机打开失败: {str(e)}")


@app.post("/api/machines/{machine_name}/shipping/servo-close", response_model=ApiResponse)
async def confirm_shipping_servo_close(machine_name: str):
    """确认寄件舵机关闭"""
    try:
        client = get_machine_connection(machine_name)
        
        # 读地址0xBBB读到值2(0x02)，代表寄件包裹到位无人机可关舵机
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 2:
            return create_response(False, f"舵机状态异常: {servo_status}，期望值为2")
        
        # 无人机关闭舵机后在地址0xBBB写20(0x14)代表无人机已关闭舵机
        client.write_holding_register(0xBBB, 20)
        
        # 等待确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBBB)
            if status == 21:
                return create_response(True, "寄件舵机关闭确认成功")
            time.sleep(1)
        
        return create_response(False, "等待寄件舵机关闭确认超时")
    
    except Exception as e:
        logger.error(f"确认寄件舵机关闭失败: {e}")
        return create_response(False, f"确认寄件舵机关闭失败: {str(e)}")


@app.post("/api/machines/{machine_name}/shipping/drone-takeoff", response_model=ApiResponse)
async def confirm_shipping_drone_takeoff(machine_name: str):
    """确认寄件无人机起飞"""
    try:
        client = get_machine_connection(machine_name)
        
        # 1. 先检查舵机关闭确认：读地址0xBBB值为21(0x15)代表下位已确认舵机关闭
        servo_status = client.read_holding_register(0xBBB)
        if servo_status != 21:
            return create_response(False, f"舵机未关闭确认，当前状态: {servo_status}，期望值为21")
        
        # 2. 再检查起飞许可：读地址0xBBA值为141(0x8D)代表无人机可以起飞
        takeoff_status = client.read_holding_register(0xBBA)
        if takeoff_status != 141:
            return create_response(False, f"起飞状态异常: {takeoff_status}，期望值为141")
        
        # 无人机起飞后，在地址0xBB9写20(0x14)代表停机坪无飞机
        client.write_holding_register(0xBB9, 20)
        
        # 等待确认：读地址0xBB9值为21(0x15)代表下位已确认停机坪无飞机
        import time
        for _ in range(10):
            status = client.read_holding_register(0xBB9)
            if status == 21:
                # 关闭舱门
                door_result = door_controller.close_door(1, client=client)
                if door_result['success']:
                    # 读取寄件结果 (地址0xBC8、0xBC9)
                    result_1 = client.read_holding_register(0xBC8)
                    result_2 = client.read_holding_register(0xBC9)
                    return create_response(True, "寄件流程完成", {
                        'result_code_1': result_1,
                        'result_code_2': result_2
                    })
                else:
                    return create_response(False, f"关闭舱门失败: {door_result.get('message')}")
            time.sleep(1)
        
        return create_response(False, "等待寄件无人机起飞确认超时")
    
    except Exception as e:
        logger.error(f"确认寄件无人机起飞失败: {e}")
        return create_response(False, f"确认寄件无人机起飞失败: {str(e)}")


# 系统状态接口
@app.get("/api/system/status", response_model=ApiResponse)
async def get_system_status():
    """获取系统状态"""
    try:
        status = system_monitor.get_comprehensive_status()
        return create_response(True, "获取系统状态成功", status)
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/alarms", response_model=ApiResponse)
async def get_system_alarms():
    """获取系统报警信息"""
    try:
        alarms = system_monitor.get_system_alarms()
        return create_response(True, "获取系统报警成功", alarms)
    except Exception as e:
        logger.error(f"获取系统报警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/weather", response_model=ApiResponse)
async def get_weather_data():
    """获取气象数据"""
    try:
        weather_data = system_monitor.get_weather_data()
        weather_check = system_monitor.check_weather_conditions()
        
        result = {
            'current_weather': weather_data,
            'flight_conditions': weather_check
        }
        
        return create_response(True, "获取气象数据成功", result)
    except Exception as e:
        logger.error(f"获取气象数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/storage", response_model=ApiResponse)
async def get_storage_capacity():
    """获取存储容量状态"""
    try:
        capacity = system_monitor.get_storage_capacity()
        return create_response(True, "获取存储容量成功", capacity)
    except Exception as e:
        logger.error(f"获取存储容量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 舱门控制接口
@app.post("/api/door/operate", response_model=ApiResponse)
async def operate_door(request: DoorOperationRequest):
    """控制舱门开关"""
    try:
        # 获取机器连接
        connection = get_machine_connection(request.machine_name)
        
        if request.operation.lower() == "open":
            success = door_controller.open_door(request.position, client=connection)
            machine_info = f"[{request.machine_name}]" if request.machine_name else ""
            message = f"{machine_info}舱门{request.position}开启{'成功' if success else '失败'}"
        elif request.operation.lower() == "close":
            success = door_controller.close_door(request.position, client=connection)
            machine_info = f"[{request.machine_name}]" if request.machine_name else ""
            message = f"{machine_info}舱门{request.position}关闭{'成功' if success else '失败'}"
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型，只支持 open/close")
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return create_response(True, message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"舱门操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/door/status/{position}", response_model=ApiResponse)
async def get_door_status(position: int, machine_name: Optional[str] = Query(None, description="机器名称")):
    """获取指定舱门状态"""
    if position < 1 or position > 6:
        raise HTTPException(status_code=400, detail="舱门位置必须在1-6之间")
    
    try:
        # 获取机器连接
        connection = get_machine_connection(machine_name)
        status = door_controller.get_door_status(position, connection)
        machine_info = f"[{machine_name}]" if machine_name else ""
        return create_response(True, f"{machine_info}获取舱门状态成功", {"position": position, "status": status, "machine_name": machine_name})
    except Exception as e:
        logger.error(f"获取舱门状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/door/status", response_model=ApiResponse)
async def get_all_doors_status(machine_name: Optional[str] = Query(None, description="机器名称")):
    """获取所有舱门状态"""
    try:
        # 获取机器连接
        connection = get_machine_connection(machine_name)
        all_status = {}
        for position in range(1, 7):
            all_status[f"door_{position}"] = door_controller.get_door_status(position, connection)
        
        machine_info = f"[{machine_name}]" if machine_name else ""
        return create_response(True, f"{machine_info}获取所有舱门状态成功", {"doors": all_status, "machine_name": machine_name})
    except Exception as e:
        logger.error(f"获取所有舱门状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 无人机存件接口
@app.post("/api/drone/storage", response_model=ApiResponse)
async def drone_storage(request: DroneStorageRequest, background_tasks: BackgroundTasks):
    """无人机存件"""
    try:
        # 获取机器连接
        connection = get_machine_connection(request.machine_name)
        
        # 在后台执行存件流程
        def execute_storage():
            success, storage_info = drone_storage_controller.execute_complete_storage_process(
                request.pickup_code, connection
            )
            machine_info = f"[{request.machine_name}]" if request.machine_name else ""
            logger.info(f"{machine_info}无人机存件完成: {success}, 信息: {storage_info}")
        
        background_tasks.add_task(execute_storage)
        
        machine_info = f"[{request.machine_name}]" if request.machine_name else ""
        return create_response(True, f"{machine_info}无人机存件流程已启动，取件码: {request.pickup_code}")
    except Exception as e:
        logger.error(f"无人机存件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drone/storage/status", response_model=ApiResponse)
async def get_drone_storage_status():
    """获取无人机存件状态"""
    try:
        status = drone_storage_controller.get_storage_status()
        return create_response(True, "获取无人机存件状态成功", {"status": status})
    except Exception as e:
        logger.error(f"获取无人机存件状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 用户取件接口
@app.post("/api/user/pickup", response_model=ApiResponse)
async def user_pickup(request: UserPickupRequest, background_tasks: BackgroundTasks):
    """用户取件"""
    try:
        # 在后台执行取件流程
        def execute_pickup():
            success, pickup_info = user_pickup_controller.execute_complete_pickup_process(
                request.pickup_code
            )
            logger.info(f"用户取件完成: {success}, 信息: {pickup_info}")
        
        background_tasks.add_task(execute_pickup)
        
        return create_response(True, f"用户取件流程已启动，取件码: {request.pickup_code}")
    except Exception as e:
        logger.error(f"用户取件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/pickup/status", response_model=ApiResponse)
async def get_user_pickup_status():
    """获取用户取件状态"""
    try:
        status = user_pickup_controller.get_pickup_status()
        return create_response(True, "获取用户取件状态成功", {"status": status})
    except Exception as e:
        logger.error(f"获取用户取件状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/user/pickup/cancel", response_model=ApiResponse)
async def cancel_user_pickup():
    """取消用户取件"""
    try:
        success = user_pickup_controller.cancel_pickup_process()
        message = "取件流程取消" + ("成功" if success else "失败")
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return create_response(True, message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消用户取件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 用户寄件接口
@app.post("/api/user/send", response_model=ApiResponse)
async def user_send(request: UserSendRequest, background_tasks: BackgroundTasks):
    """用户寄件"""
    try:
        # 在后台执行寄件流程
        def execute_send():
            success, send_info = user_send_controller.execute_complete_send_process(
                request.send_code
            )
            logger.info(f"用户寄件完成: {success}, 信息: {send_info}")
        
        background_tasks.add_task(execute_send)
        
        return create_response(True, f"用户寄件流程已启动，寄件码: {request.send_code}")
    except Exception as e:
        logger.error(f"用户寄件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/send/status", response_model=ApiResponse)
async def get_user_send_status():
    """获取用户寄件状态"""
    try:
        status = user_send_controller.get_send_status()
        return create_response(True, "获取用户寄件状态成功", {"status": status})
    except Exception as e:
        logger.error(f"获取用户寄件状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/user/send/cancel", response_model=ApiResponse)
async def cancel_user_send():
    """取消用户寄件"""
    try:
        success = user_send_controller.cancel_send_process()
        message = "寄件流程取消" + ("成功" if success else "失败")
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return create_response(True, message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消用户寄件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# PLC连接管理接口
@app.get("/api/plc/status", response_model=ApiResponse)
async def get_plc_status():
    """获取PLC连接状态"""
    try:
        is_connected = modbus_client.is_connected
        return create_response(True, "获取PLC状态成功", {"connected": is_connected})
    except Exception as e:
        logger.error(f"获取PLC状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plc/connect", response_model=ApiResponse)
async def connect_plc():
    """连接PLC"""
    try:
        success = modbus_client.connect()
        message = "PLC连接" + ("成功" if success else "失败")
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return create_response(True, message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接PLC失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plc/disconnect", response_model=ApiResponse)
async def disconnect_plc():
    """断开PLC连接"""
    try:
        modbus_client.disconnect()
        return create_response(True, "PLC连接已断开")
    except Exception as e:
        logger.error(f"断开PLC连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plc/reconnect", response_model=ApiResponse)
async def reconnect_plc():
    """重新连接PLC"""
    try:
        success = modbus_client.reconnect()
        message = "PLC重新连接" + ("成功" if success else "失败")
        
        if not success:
            raise HTTPException(status_code=500, detail=message)
        
        return create_response(True, message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新连接PLC失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modbus/write", response_model=ApiResponse)
async def modbus_write(request: ModbusWriteRequest):
    """Modbus寄存器写入"""
    try:
        # 写入多个寄存器值
        for i, value in enumerate(request.values):
            success = modbus_client.write_holding_register(request.address + i, value)
            if not success:
                raise HTTPException(status_code=500, detail=f"写入寄存器 {request.address + i} 失败")
        
        return create_response(True, f"成功写入寄存器 {request.address}，共 {len(request.values)} 个值")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus写入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/modbus/read", response_model=ApiResponse)
async def modbus_read(request: ModbusReadRequest):
    """Modbus读取接口"""
    try:
        value = modbus_client.read_holding_register(request.address)
        if value is None:
            raise Exception(f"读取寄存器 {request.address} 失败")
        
        logger.info(f"成功读取寄存器 {request.address}: {value}")
        return create_response(True, f"成功读取寄存器 {request.address}", {"value": value})
    except Exception as e:
        logger.error(f"Modbus读取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 模式2：用户本地取件码直接取件
@app.post("/api/user/pickup/auto", response_model=ApiResponse)
async def user_pickup_auto(request: UserPickupRequest):
    """模式2：用户输入取件码自动开门取件"""
    try:
        pickup_code = request.pickup_code
        
        if len(pickup_code) != 6 or not pickup_code.isdigit():
            raise HTTPException(status_code=400, detail="取件码必须为6位数字")
        
        logger.info(f"模式2取件开始，取件码: {pickup_code}")
        
        # 根据通信协议，将取件码分为前三位和后三位
        # VW3008 (0xBC0): 取件码前三位
        # VW3009 (0xBC1): 取件码后三位
        front_three = int(pickup_code[:3])
        back_three = int(pickup_code[3:])
        
        # 写入取件码到寄存器
        success1 = modbus_client.write_holding_register(0xBC0, front_three)
        success2 = modbus_client.write_holding_register(0xBC1, back_three)
        
        if not (success1 and success2):
            raise HTTPException(status_code=500, detail="写入取件码失败")
        
        logger.info(f"取件码已写入寄存器: VW3008={front_three}, VW3009={back_three}")
        
        # 等待一小段时间让PLC处理
        import asyncio
        await asyncio.sleep(0.5)
        
        # 读取PLC确定的取件位置 VW3010 (0xBC2)
        position_code = modbus_client.read_holding_register(0xBC2)
        pickup_position = None
        
        if position_code:
            position_value = position_code
            # 根据通信协议映射位置
            position_map = {
                101: "1#位置",  # 0x65
                102: "2#位置",  # 0x66
                103: "3#位置"   # 0x67
            }
            pickup_position = position_map.get(position_value, f"未知位置({position_value})")
            logger.info(f"PLC确定的取件位置: {pickup_position} (代码: {position_value})")
        
        # 等待PLC验证并检查取件状态 VW3011 (0xBC3)
        await asyncio.sleep(1.0)  # 给PLC更多时间处理
        
        pickup_status = modbus_client.read_holding_register(0xBC3)
        verification_success = False
        status_message = "取件码验证失败"
        
        if pickup_status:
            if pickup_status == 210:  # 0xD2 - 正在取件
                verification_success = True
                status_message = "取件码验证成功，正在开门取件"
            elif pickup_status == 211:  # 0xD3 - 取件完毕
                verification_success = True
                status_message = "取件码验证成功，取件已完成"
            else:
                status_message = f"取件状态异常: {pickup_status}"
        
        message = f"取件码: {pickup_code}, {status_message}"
        if pickup_position:
            message += f"，位置: {pickup_position}"
        
        return create_response(verification_success, message, {
            "pickup_code": pickup_code,
            "position": pickup_position,
            "front_three": front_three,
            "back_three": back_three,
            "verification_success": verification_success,
            "pickup_status": pickup_status,
            "status_message": status_message
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模式2取件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 查询取件验证状态
@app.get("/api/user/pickup/verification", response_model=ApiResponse)
async def get_pickup_verification_status():
    """查询当前取件验证状态"""
    try:
        # 读取取件状态 VW3011 (0xBC3)
        pickup_status = modbus_client.read_holding_register(0xBC3)
        
        # 读取取件位置 VW3010 (0xBC2)
        position_code = modbus_client.read_holding_register(0xBC2)
        pickup_position = None
        
        if position_code:
            position_map = {
                101: "1#位置",  # 0x65
                102: "2#位置",  # 0x66
                103: "3#位置"   # 0x67
            }
            pickup_position = position_map.get(position_code, f"未知位置({position_code})")
        
        # 读取当前取件码
        front_three = modbus_client.read_holding_register(0xBC0)
        back_three = modbus_client.read_holding_register(0xBC1)
        current_pickup_code = None
        if front_three and back_three:
            current_pickup_code = f"{front_three:03d}{back_three:03d}"
        
        verification_success = False
        status_message = "无取件操作"
        
        if pickup_status:
            if pickup_status == 210:  # 0xD2 - 正在取件
                verification_success = True
                status_message = "取件码验证成功，正在开门取件"
            elif pickup_status == 211:  # 0xD3 - 取件完毕
                verification_success = True
                status_message = "取件码验证成功，取件已完成"
            elif pickup_status == 0:
                status_message = "等待取件操作"
            else:
                status_message = f"取件状态异常: {pickup_status}"
        
        return create_response(True, "获取取件验证状态成功", {
            "verification_success": verification_success,
            "pickup_status": pickup_status,
            "status_message": status_message,
            "position": pickup_position,
            "current_pickup_code": current_pickup_code,
            "front_three": front_three,
            "back_three": back_three
        })
        
    except Exception as e:
        logger.error(f"获取取件验证状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 历史数据接口
@app.get("/api/history/status", response_model=ApiResponse)
async def get_status_history(limit: int = 100):
    """获取状态历史记录"""
    try:
        history = system_monitor.get_status_history(limit)
        return create_response(True, "获取状态历史成功", {"history": history, "count": len(history)})
    except Exception as e:
        logger.error(f"获取状态历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/alarms", response_model=ApiResponse)
async def get_alarm_history(limit: int = 100):
    """获取报警历史记录"""
    try:
        history = system_monitor.get_alarm_history(limit)
        return create_response(True, "获取报警历史成功", {"history": history, "count": len(history)})
    except Exception as e:
        logger.error(f"获取报警历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/weather", response_model=ApiResponse)
async def get_weather_history(limit: int = 100):
    """获取气象数据历史记录"""
    try:
        history = system_monitor.get_weather_history(limit)
        return create_response(True, "获取气象历史成功", {"history": history, "count": len(history)})
    except Exception as e:
        logger.error(f"获取气象历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 寄存器监视接口
@app.get("/api/machines/{machine_name}/registers/all", response_model=ApiResponse)
async def get_all_registers(machine_name: str):
    """获取所有寄存器的值"""
    try:
        client = get_machine_connection(machine_name)
        if not client:
            return create_response(False, f"机器 {machine_name} 连接失败")
        
        # 定义所有寄存器地址和名称
        registers = {
            # 舱门操作
            "0xBB8": {"name": "舱门操作", "address": 0xBB8, "description": "开关舱门状态"},
            
            # 停机坪状态
            "0xBB9": {"name": "停机坪状态", "address": 0xBB9, "description": "停机坪有无飞机状态"},
            
            # 无人机存取包裹
            "0xBBA": {"name": "无人机存取包裹", "address": 0xBBA, "description": "无人机存取包裹操作状态"},
            "0xBBB": {"name": "无人机舵机状态", "address": 0xBBB, "description": "无人机舵机开关状态"},
            "0xBBC": {"name": "无人机存包裹位置", "address": 0xBBC, "description": "当前存包裹位置(1-3号)"},
            "0xBBD": {"name": "无人机取包裹位置", "address": 0xBBD, "description": "当前取包裹位置(4-6号)"},
            "0xBBE": {"name": "无人机存件格口状态", "address": 0xBBE, "description": "机柜存满状态"},
            
            # 用户取包裹
            "0xBC0": {"name": "取件码前三位", "address": 0xBC0, "description": "用户取件码前三位"},
            "0xBC1": {"name": "取件码后三位", "address": 0xBC1, "description": "用户取件码后三位"},
            "0xBC2": {"name": "取包裹位置", "address": 0xBC2, "description": "用户取包裹位置信息"},
            "0xBC3": {"name": "用户取包裹操作", "address": 0xBC3, "description": "用户取包裹操作状态"},
            
            # 用户回收包裹
            "0xBC4": {"name": "用户回收包裹-开箱", "address": 0xBC4, "description": "用户回收包裹开箱操作"},
            "0xBC5": {"name": "用户回收包裹-确认", "address": 0xBC5, "description": "用户确认回收包裹操作"},
            
            # 用户寄件
            "0xBC6": {"name": "寄件取空箱位置", "address": 0xBC6, "description": "用户寄件取空箱格口信息"},
            "0xBC7": {"name": "用户寄件操作", "address": 0xBC7, "description": "用户寄件操作状态"},
            "0xBCA": {"name": "寄件存箱位置", "address": 0xBCA, "description": "用户寄件存箱格口信息"},
            "0xBCB": {"name": "寄件箱重量", "address": 0xBCB, "description": "用户寄件箱当前重量(KG)"},
            
            # 系统状态
            "0xBCC": {"name": "系统模式控制", "address": 0xBCC, "description": "系统模式控制(自动/暂停/急停)"},
            "0xBCD": {"name": "系统状态", "address": 0xBCD, "description": "当前系统状态"},
            "0xBCE": {"name": "故障清除", "address": 0xBCE, "description": "系统故障清除操作"},
            
            # 寄件码
            "0xBD0": {"name": "寄件码前三位", "address": 0xBD0, "description": "用户寄件码前三位"},
            "0xBD1": {"name": "寄件码后三位", "address": 0xBD1, "description": "用户寄件码后三位"},
            "0xBD2": {"name": "寄件格口状态", "address": 0xBD2, "description": "用户寄件格口状态"},
            
            # 气象站
            "0x8FC": {"name": "湿度", "address": 0x8FC, "description": "环境湿度"},
            "0x8FE": {"name": "温度", "address": 0x8FE, "description": "环境温度"},
            "0x900": {"name": "风力", "address": 0x900, "description": "风力等级"},
            "0x902": {"name": "雨量", "address": 0x902, "description": "降雨量"},
            "0x904": {"name": "风速", "address": 0x904, "description": "风速"},
            "0x906": {"name": "风向", "address": 0x906, "description": "风向"},
        }
        
        # 系统报警寄存器 (0xBFE - 0xC0A)
        alarm_registers = {
            "0xBFE": "货叉Z1轴_伺服驱动器故障",
            "0xBFF": "货叉Z2轴_伺服驱动器故障", 
            "0xC00": "A_X前1轴_步进轴故障",
            "0xC01": "A_X前2轴_步进轴故障",
            "0xC02": "A_X后1轴_步进轴故障",
            "0xC03": "A_X后2轴_步进轴故障",
            "0xC04": "A_Y左1轴_步进轴故障",
            "0xC05": "A_Y左2轴_步进轴故障",
            "0xC06": "A_Y右1轴_步进轴故障",
            "0xC07": "A_Y右2轴_步进轴故障",
            "0xC08": "舱门左轴_步进轴故障",
            "0xC09": "舱门右轴_步进轴故障",
            "0xC0A": "取货口电磁锁故障"
        }
        
        # 添加报警寄存器到主寄存器字典
        for hex_addr, desc in alarm_registers.items():
            registers[hex_addr] = {
                "name": desc,
                "address": int(hex_addr, 16),
                "description": f"系统报警: {desc}"
            }
        
        # 读取所有寄存器的值
        register_values = {}
        failed_registers = []
        
        for hex_addr, reg_info in registers.items():
            try:
                result = client.read_holding_registers(reg_info["address"], 1)
                if result is None or len(result) == 0:
                    failed_registers.append(hex_addr)
                    register_values[hex_addr] = {
                        "name": reg_info["name"],
                        "address": hex_addr,
                        "value": None,
                        "decimal": None,
                        "description": reg_info["description"],
                        "error": "读取失败"
                    }
                else:
                    value = result[0]
                    register_values[hex_addr] = {
                        "name": reg_info["name"],
                        "address": hex_addr,
                        "value": f"0x{value:04X}",
                        "decimal": value,
                        "description": reg_info["description"],
                        "error": None
                    }
            except Exception as e:
                failed_registers.append(hex_addr)
                register_values[hex_addr] = {
                    "name": reg_info["name"],
                    "address": hex_addr,
                    "value": None,
                    "decimal": None,
                    "description": reg_info["description"],
                    "error": str(e)
                }
        
        return create_response(
            success=True,
            message=f"成功读取寄存器，失败数量: {len(failed_registers)}",
            data={
                "registers": register_values,
                "total_count": len(registers),
                "success_count": len(registers) - len(failed_registers),
                "failed_count": len(failed_registers),
                "failed_registers": failed_registers,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"读取所有寄存器失败: {e}")
        return create_response(False, f"读取所有寄存器失败: {str(e)}")

# 健康检查接口
@app.get("/api/health", response_model=ApiResponse)
async def health_check():
    """健康检查"""
    try:
        plc_connected = modbus_client.is_connected
        system_status = system_monitor.get_system_status()
        
        health_info = {
            "api_status": "healthy",
            "plc_connected": plc_connected,
            "system_normal": system_status and system_status.get('is_normal', False) if system_status else False,
            "timestamp": datetime.now().isoformat()
        }
        
        return create_response(True, "系统健康检查完成", health_info)
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 启动函数
def start_web_server():
    """启动Web服务器"""
    logger.info(f"启动Web API服务器，端口: {WEB_CONFIG['port']}")
    
    uvicorn.run(
        app,
        host=WEB_CONFIG['host'],
        port=WEB_CONFIG['port'],
        log_level="info"
    )

if __name__ == "__main__":
    start_web_server()