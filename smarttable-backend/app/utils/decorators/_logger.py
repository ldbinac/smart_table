"""
装饰器模块
提供认证、权限检查、速率限制、操作日志等装饰器
"""
import json
import time
from functools import wraps
from typing import Callable, List, Optional, Union, Any, Dict

from flask import request, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.i18n import translate
from app.extensions import cache
from app.utils.response import forbidden_response, unauthorized_response, error_response


# 登录失败记录存储（内存存储，生产环境建议使用 Redis）

def operation_log(
    action: str,
    entity_type: str,
    entity_id_field: Optional[str] = None,
    capture_old_value: bool = False,
    capture_new_value: bool = True
) -> Callable:
    """
    操作日志装饰器
    自动记录管理员操作日志，包括用户 ID、操作类型、实体信息、IP 地址等
    
    使用示例:
        @admin_bp.route('/users/<user_id>', methods=['PUT'])
        @jwt_required
        @admin_required
        @operation_log(
            action='update',
            entity_type='user',
            entity_id_field='user_id',
            capture_old_value=True,
            capture_new_value=True
        )
        def update_user(user_id):
            # 视图函数代码
            return success_response(data=user_info)
    
    Args:
        action: 操作类型 (create, update, delete, suspend, activate 等)
        entity_type: 实体类型 (user, config, table, field 等)
        entity_id_field: 从路由参数或请求数据中获取 entity_id 的字段名
                        如果为 None，则尝试从 view_args 中获取
        capture_old_value: 是否捕获旧值（需要在 g 中预先设置 old_value）
        capture_new_value: 是否捕获新值（从视图函数的返回值中提取）
    
    Returns:
        装饰器函数
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import current_app
            from app.models.log import OperationLog, AdminActionType, EntityType
            from uuid import UUID
            
            # 执行视图函数
            response = fn(*args, **kwargs)
            
            try:
                # 获取当前用户 ID
                user_id = g.get('current_user_id')
                if not user_id:
                    current_app.logger.warning('operation_log: 未找到当前用户 ID')
                    return response
                
                # 获取 entity_id
                entity_id = None
                if entity_id_field:
                    # 优先从路由参数获取
                    if entity_id_field in kwargs:
                        entity_id = kwargs[entity_id_field]
                    # 其次从 view_args 获取
                    elif request.view_args and entity_id_field in request.view_args:
                        entity_id = request.view_args[entity_id_field]
                    # 最后从请求数据获取
                    elif request.is_json:
                        data = request.get_json(silent=True)
                        if data and entity_id_field in data:
                            entity_id = data[entity_id_field]
                else:
                    # 尝试从 view_args 中获取常见的 ID 字段
                    for id_field in ['user_id', 'id', 'table_id', 'field_id', 'record_id']:
                        if request.view_args and id_field in request.view_args:
                            entity_id = request.view_args[id_field]
                            break
                
                # 获取旧值
                old_value = None
                if capture_old_value and hasattr(g, 'old_value'):
                    old_value = g.old_value
                
                # 获取新值
                new_value = None
                if capture_new_value and response:
                    try:
                        # 尝试从响应中获取 data 字段
                        if hasattr(response, 'get_json'):
                            response_data = response.get_json(silent=True)
                            if response_data and 'data' in response_data:
                                new_value = response_data['data']
                        elif isinstance(response, dict) and 'data' in response:
                            new_value = response['data']
                    except Exception:
                        pass
                
                # 获取 IP 地址和 User-Agent
                ip_address = get_client_ip()
                user_agent = get_user_agent()
                
                # 创建操作日志记录
                OperationLog.log(
                    user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=UUID(entity_id) if entity_id and isinstance(entity_id, str) else entity_id,
                    old_value=old_value,
                    new_value=new_value,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # 提交数据库会话
                from app.extensions import db
                db.session.commit()
                
                current_app.logger.info(
                    f'操作日志已记录：user_id={user_id}, action={action}, '
                    f'entity_type={entity_type}, entity_id={entity_id}'
                )
                
            except Exception as e:
                # 记录日志失败不影响主流程
                from app.extensions import db
                db.session.rollback()
                current_app.logger.error(f'记录操作日志失败：{str(e)}', exc_info=True)
            
            return response
        
        return wrapper
    return decorator
