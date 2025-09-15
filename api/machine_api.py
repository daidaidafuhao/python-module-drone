# -*- coding: utf-8 -*-
"""
机器配置管理API模块
提供多机器配置的CRUD接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

# 导入服务模块
from services.config_manager import config_manager
from services.machine_manager import machine_manager
from models.drone_cabinet import DroneCabinetDAO

# 创建路由器
router = APIRouter(prefix="/api/machines", tags=["机器配置管理"])

# 请求模型定义
class MachineConfigRequest(BaseModel):
    """机器配置请求模型"""
    machine_name: str = Field(..., min_length=1, max_length=50, description="机器名称")
    host: str = Field(..., description="PLC主机地址")
    port: int = Field(..., ge=1, le=65535, description="PLC端口号")
    description: Optional[str] = Field(None, max_length=200, description="机器描述")
    is_active: bool = Field(True, description="是否启用")

class MachineConfigUpdate(BaseModel):
    """机器配置更新模型"""
    host: Optional[str] = Field(None, description="PLC主机地址")
    port: Optional[int] = Field(None, ge=1, le=65535, description="PLC端口号")
    description: Optional[str] = Field(None, max_length=200, description="机器描述")
    is_active: Optional[bool] = Field(None, description="是否启用")

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

# 机器配置管理接口
@router.get("/", response_model=ApiResponse)
async def get_all_machines():
    """获取所有机器配置"""
    try:
        dao = DroneCabinetDAO()
        machines = dao.get_all_machines()
        return create_response(True, "获取机器配置成功", {"machines": machines})
    except Exception as e:
        logger.error(f"获取机器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{machine_name}", response_model=ApiResponse)
async def get_machine_config(machine_name: str):
    """获取指定机器配置"""
    try:
        dao = DroneCabinetDAO()
        machine = dao.get_machine_by_name(machine_name)
        if not machine:
            raise HTTPException(status_code=404, detail=f"机器 {machine_name} 不存在")
        return create_response(True, "获取机器配置成功", {"machine": machine})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取机器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ApiResponse)
async def create_machine_config(request: MachineConfigRequest):
    """创建机器配置"""
    try:
        dao = DroneCabinetDAO()
        
        # 检查机器名称是否已存在
        existing = dao.get_machine_by_name(request.machine_name)
        if existing:
            raise HTTPException(status_code=400, detail=f"机器名称 {request.machine_name} 已存在")
        
        # 创建机器配置
        machine_id = dao.create_machine({
            'machine_name': request.machine_name,
            'host': request.host,
            'port': request.port,
            'description': request.description,
            'is_active': request.is_active
        })
        
        # 刷新配置管理器
        config_manager.refresh_config()
        
        return create_response(True, f"机器配置创建成功", {"machine_id": machine_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建机器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{machine_name}", response_model=ApiResponse)
async def update_machine_config(machine_name: str, request: MachineConfigUpdate):
    """更新机器配置"""
    try:
        dao = DroneCabinetDAO()
        
        # 检查机器是否存在
        existing = dao.get_machine_by_name(machine_name)
        if not existing:
            raise HTTPException(status_code=404, detail=f"机器 {machine_name} 不存在")
        
        # 构建更新数据
        update_data = {}
        if request.host is not None:
            update_data['host'] = request.host
        if request.port is not None:
            update_data['port'] = request.port
        if request.description is not None:
            update_data['description'] = request.description
        if request.is_active is not None:
            update_data['is_active'] = request.is_active
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的数据")
        
        # 更新机器配置
        dao.update_machine(machine_name, update_data)
        
        # 刷新配置管理器
        config_manager.refresh_config()
        
        # 如果机器连接存在，重新连接
        if machine_manager.has_connection(machine_name):
            machine_manager.disconnect_machine(machine_name)
            if update_data.get('is_active', True):
                machine_manager.connect_machine(machine_name)
        
        return create_response(True, f"机器配置更新成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新机器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{machine_name}", response_model=ApiResponse)
async def delete_machine_config(machine_name: str):
    """删除机器配置"""
    try:
        dao = DroneCabinetDAO()
        
        # 检查机器是否存在
        existing = dao.get_machine_by_name(machine_name)
        if not existing:
            raise HTTPException(status_code=404, detail=f"机器 {machine_name} 不存在")
        
        # 断开连接
        if machine_manager.has_connection(machine_name):
            machine_manager.disconnect_machine(machine_name)
        
        # 删除机器配置
        dao.delete_machine(machine_name)
        
        # 刷新配置管理器
        config_manager.refresh_config()
        
        return create_response(True, f"机器配置删除成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除机器配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 机器连接管理接口
@router.post("/{machine_name}/connect", response_model=ApiResponse)
async def connect_machine(machine_name: str):
    """连接指定机器"""
    try:
        success = machine_manager.connect_machine(machine_name)
        if success:
            return create_response(True, f"机器 {machine_name} 连接成功")
        else:
            raise HTTPException(status_code=500, detail=f"机器 {machine_name} 连接失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接机器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{machine_name}/disconnect", response_model=ApiResponse)
async def disconnect_machine(machine_name: str):
    """断开指定机器连接"""
    try:
        success = machine_manager.disconnect_machine(machine_name)
        if success:
            return create_response(True, f"机器 {machine_name} 断开连接成功")
        else:
            return create_response(False, f"机器 {machine_name} 未连接或断开失败")
    except Exception as e:
        logger.error(f"断开机器连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{machine_name}/status", response_model=ApiResponse)
async def get_machine_status(machine_name: str):
    """获取机器连接状态"""
    try:
        status = machine_manager.get_machine_status(machine_name)
        return create_response(True, "获取机器状态成功", {"status": status})
    except Exception as e:
        logger.error(f"获取机器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/all", response_model=ApiResponse)
async def get_all_machines_status():
    """获取所有机器连接状态"""
    try:
        status = machine_manager.get_all_status()
        return create_response(True, "获取所有机器状态成功", {"machines_status": status})
    except Exception as e:
        logger.error(f"获取所有机器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/health-check", response_model=ApiResponse)
async def health_check_all_machines():
    """对所有机器进行健康检查"""
    try:
        results = machine_manager.health_check_all()
        return create_response(True, "健康检查完成", {"results": results})
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))