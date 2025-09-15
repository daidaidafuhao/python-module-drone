# -*- coding: utf-8 -*-
"""
无人机柜数据模型
对应数据库表结构的模型类
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from database.connection import db_manager
import logging

logger = logging.getLogger(__name__)

@dataclass
class DroneCabinet:
    """无人机柜模型"""
    id: Optional[int] = None
    name: str = ''
    code: str = ''
    ip: str = ''
    port: int = 502
    slave_id: int = 1
    address: str = ''
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    status: int = 0  # 0-离线 1-在线 2-故障
    total_boxes: int = 0
    available_boxes: int = 0
    last_online_time: Optional[datetime] = None
    last_offline_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    error_message: Optional[str] = None
    remark: Optional[str] = None
    creator: str = ''
    create_time: Optional[datetime] = None
    updater: str = ''
    update_time: Optional[datetime] = None
    deleted: bool = False
    tenant_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DroneCabinet':
        """从字典创建对象"""
        # 处理datetime字段
        datetime_fields = ['last_online_time', 'last_offline_time', 'last_error_time', 'create_time', 'update_time']
        for field in datetime_fields:
            if field in data and data[field] and isinstance(data[field], str):
                try:
                    data[field] = datetime.strptime(data[field], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    data[field] = None
        
        # 处理deleted字段（bit类型）
        if 'deleted' in data:
            data['deleted'] = bool(data['deleted'])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class DroneCabinetLog:
    """无人机柜操作日志模型"""
    id: Optional[int] = None
    cabinet_id: int = 0
    operation_type: str = ''
    operation_result: int = 0  # 0-失败 1-成功
    error_message: Optional[str] = None
    operator: str = ''
    operation_time: Optional[datetime] = None
    remark: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
            else:
                result[key] = value
        return result

@dataclass
class DroneCabinetBox:
    """无人机柜格口模型"""
    id: Optional[int] = None
    cabinet_id: int = 0
    box_no: str = ''
    status: int = 0  # 0-空闲 1-占用 2-故障
    package_code: Optional[str] = None
    pickup_code: Optional[str] = None
    last_operation_time: Optional[datetime] = None
    last_operation_type: Optional[str] = None
    remark: Optional[str] = None
    creator: str = ''
    create_time: Optional[datetime] = None
    updater: str = ''
    update_time: Optional[datetime] = None
    deleted: bool = False
    tenant_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.strftime('%Y-%m-%d %H:%M:%S') if value else None
            else:
                result[key] = value
        return result

class DroneCabinetDAO:
    """无人机柜数据访问对象"""
    
    @staticmethod
    def get_all_active() -> List[DroneCabinet]:
        """获取所有活跃的无人机柜"""
        try:
            sql = """
                SELECT * FROM drone_cabinet 
                WHERE deleted = 0 AND status IN (1, 2)
                ORDER BY create_time DESC
            """
            results = db_manager.execute_query(sql)
            return [DroneCabinet.from_dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取活跃无人机柜失败: {e}")
            return []
    
    @staticmethod
    def get_by_code(code: str) -> Optional[DroneCabinet]:
        """根据编号获取无人机柜"""
        try:
            sql = "SELECT * FROM drone_cabinet WHERE code = %s AND deleted = 0"
            results = db_manager.execute_query(sql, (code,))
            if results:
                return DroneCabinet.from_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"根据编号获取无人机柜失败: {e}")
            return None
    
    @staticmethod
    def get_by_id(cabinet_id: int) -> Optional[DroneCabinet]:
        """根据ID获取无人机柜"""
        try:
            sql = "SELECT * FROM drone_cabinet WHERE id = %s AND deleted = 0"
            results = db_manager.execute_query(sql, (cabinet_id,))
            if results:
                return DroneCabinet.from_dict(results[0])
            return None
        except Exception as e:
            logger.error(f"根据ID获取无人机柜失败: {e}")
            return None
    
    @staticmethod
    def create(cabinet: DroneCabinet) -> Optional[int]:
        """创建无人机柜"""
        try:
            sql = """
                INSERT INTO drone_cabinet 
                (name, code, ip, port, slave_id, address, longitude, latitude, 
                 status, total_boxes, available_boxes, remark, creator, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                cabinet.name, cabinet.code, cabinet.ip, cabinet.port, cabinet.slave_id,
                cabinet.address, cabinet.longitude, cabinet.latitude, cabinet.status,
                cabinet.total_boxes, cabinet.available_boxes, cabinet.remark,
                cabinet.creator, cabinet.tenant_id
            )
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"创建无人机柜失败: {e}")
            return None
    
    @staticmethod
    def update(cabinet: DroneCabinet) -> bool:
        """更新无人机柜"""
        try:
            sql = """
                UPDATE drone_cabinet SET 
                name = %s, ip = %s, port = %s, slave_id = %s, address = %s,
                longitude = %s, latitude = %s, status = %s, total_boxes = %s,
                available_boxes = %s, remark = %s, updater = %s
                WHERE id = %s AND deleted = 0
            """
            params = (
                cabinet.name, cabinet.ip, cabinet.port, cabinet.slave_id,
                cabinet.address, cabinet.longitude, cabinet.latitude, cabinet.status,
                cabinet.total_boxes, cabinet.available_boxes, cabinet.remark,
                cabinet.updater, cabinet.id
            )
            
            result = db_manager.execute_update(sql, params)
            return result > 0
        except Exception as e:
            logger.error(f"更新无人机柜失败: {e}")
            return False
    
    @staticmethod
    def update_status(cabinet_id: int, status: int, error_message: str = None) -> bool:
        """更新无人机柜状态"""
        try:
            if status == 1:  # 在线
                sql = """
                    UPDATE drone_cabinet SET 
                    status = %s, last_online_time = NOW(), error_message = NULL
                    WHERE id = %s AND deleted = 0
                """
                params = (status, cabinet_id)
            elif status == 0:  # 离线
                sql = """
                    UPDATE drone_cabinet SET 
                    status = %s, last_offline_time = NOW()
                    WHERE id = %s AND deleted = 0
                """
                params = (status, cabinet_id)
            else:  # 故障
                sql = """
                    UPDATE drone_cabinet SET 
                    status = %s, last_error_time = NOW(), error_message = %s
                    WHERE id = %s AND deleted = 0
                """
                params = (status, error_message, cabinet_id)
            
            result = db_manager.execute_update(sql, params)
            return result > 0
        except Exception as e:
            logger.error(f"更新无人机柜状态失败: {e}")
            return False
    
    @staticmethod
    def delete(cabinet_id: int) -> bool:
        """删除无人机柜（软删除）"""
        try:
            sql = "UPDATE drone_cabinet SET deleted = 1 WHERE id = %s"
            result = db_manager.execute_update(sql, (cabinet_id,))
            return result > 0
        except Exception as e:
            logger.error(f"删除无人机柜失败: {e}")
            return False
    
    @staticmethod
    def get_connection_configs() -> Dict[str, Dict[str, Any]]:
        """获取所有机器的连接配置"""
        try:
            sql = """
                SELECT code, ip, port, slave_id, status 
                FROM drone_cabinet 
                WHERE deleted = 0 AND status IN (1, 2)
            """
            results = db_manager.execute_query(sql)
            
            configs = {}
            for row in results:
                configs[row['code']] = {
                    'host': row['ip'],
                    'port': row['port'],
                    'unit_id': row['slave_id'],
                    'status': row['status']
                }
            
            return configs
        except Exception as e:
            logger.error(f"获取连接配置失败: {e}")
            return {}

class DroneCabinetLogDAO:
    """无人机柜日志数据访问对象"""
    
    @staticmethod
    def create_log(log: DroneCabinetLog) -> bool:
        """创建操作日志"""
        try:
            sql = """
                INSERT INTO drone_cabinet_log 
                (cabinet_id, operation_type, operation_result, error_message, operator, remark)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (
                log.cabinet_id, log.operation_type, log.operation_result,
                log.error_message, log.operator, log.remark
            )
            
            result = db_manager.execute_update(sql, params)
            return result > 0
        except Exception as e:
            logger.error(f"创建操作日志失败: {e}")
            return False
    
    @staticmethod
    def get_logs_by_cabinet(cabinet_id: int, limit: int = 100) -> List[DroneCabinetLog]:
        """获取指定柜子的操作日志"""
        try:
            sql = """
                SELECT * FROM drone_cabinet_log 
                WHERE cabinet_id = %s 
                ORDER BY operation_time DESC 
                LIMIT %s
            """
            results = db_manager.execute_query(sql, (cabinet_id, limit))
            
            logs = []
            for row in results:
                log = DroneCabinetLog(
                    id=row['id'],
                    cabinet_id=row['cabinet_id'],
                    operation_type=row['operation_type'],
                    operation_result=row['operation_result'],
                    error_message=row['error_message'],
                    operator=row['operator'],
                    operation_time=row['operation_time'],
                    remark=row['remark']
                )
                logs.append(log)
            
            return logs
        except Exception as e:
            logger.error(f"获取操作日志失败: {e}")
            return []