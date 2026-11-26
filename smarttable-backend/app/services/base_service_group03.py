"""
基础数据服务模块
处理 Base（工作区/数据库）的 CRUD 操作和成员管理
"""
from typing import List, Optional, Dict, Any
import uuid

# 用于区分"未传递 role_id"和"明确将 role_id 设为 None"
_UNSET = object()
import threading
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models.base import Base, BaseMember, MemberRole
from app.models.base_share import BaseShare, SharePermission
from app.models.user import User
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.models.view import View
from app.models.dashboard import Dashboard
from app.utils.constants import ROLE_LEVELS
from app.services.email_config_service import EmailConfigService
from app.services.email_sender_service import EmailSenderService
from app.services.notification_service import NotificationService

class BaseServiceGroup03Mixin:
    """Mixin auto-split"""
    
    """基础数据服务类"""
    
    ROLE_LEVELS = ROLE_LEVELS
    
    
    @staticmethod
    def _create_fallback_link_field(source_field: 'Field', new_table_id: str, field_id_map: dict,
                                    table_id_map: dict, new_options: dict, target_table_id: str = None) -> None:
        """
        创建降级方案的关联字段
    
        Args:
            source_field: 源字段对象
            new_table_id: 新表 ID
            field_id_map: 字段 ID 映射字典
            table_id_map: 表 ID 映射字典
            new_options: 字段选项
            target_table_id: 目标表 ID
        """
        import copy
    
        fallback_config = copy.deepcopy(source_field.config) if source_field.config else {}
        if isinstance(fallback_config, dict) and target_table_id:
            fallback_config['linkedTableId'] = target_table_id
        elif isinstance(fallback_config, dict):
            old_linked_id = fallback_config.get('linkedTableId')
            if old_linked_id and old_linked_id in table_id_map:
                fallback_config['linkedTableId'] = table_id_map[old_linked_id]
    
        new_field = Field(
            table_id=new_table_id,
            name=source_field.name,
            type=source_field.type,
            options=new_options,
            config=fallback_config,
            order=source_field.order,
            is_primary=source_field.is_primary,
            is_required=source_field.is_required,
            description=source_field.description
        )
        db.session.add(new_field)
        db.session.flush()
        field_id_map[str(source_field.id)] = str(new_field.id)
        current_app.logger.warning(f'[BaseService] 使用降级方案创建关联字段：{new_field.id}')
    
    @staticmethod
    def _copy_table_and_fields(source_table: 'Table', new_base_id: str, 
                               field_id_map: dict, table_id_map: dict, link_field_map: dict) -> 'Table':
        """
        复制表和字段
    
        Args:
            source_table: 源表对象
            new_base_id: 新 Base ID
            field_id_map: 字段 ID 映射字典
            table_id_map: 表 ID 映射字典
            link_field_map: 关联字段映射字典
    
        Returns:
            新创建的表对象
        """
        new_table = Table(
            base_id=new_base_id,
            name=source_table.name,
            description=source_table.description,
            order=source_table.order
        )
        db.session.add(new_table)
        db.session.flush()
    
        table_id_map[str(source_table.id)] = str(new_table.id)
    
        source_fields = Field.query.filter_by(table_id=source_table.id).all()
        for source_field in source_fields:
            BaseService._copy_field(source_field, str(new_table.id), field_id_map, 
                                    table_id_map, link_field_map)
    
        if source_table.primary_field_id:
            new_primary_field_id = field_id_map.get(str(source_table.primary_field_id))
            if new_primary_field_id:
                new_table.primary_field_id = new_primary_field_id
    
        return new_table
    
    @staticmethod
    def _copy_records(source_table_id: str, new_table_id: str, 
                      field_id_map: dict, record_id_map: dict) -> None:
        """
        复制记录
    
        Args:
            source_table_id: 源表 ID
            new_table_id: 新表 ID
            field_id_map: 字段 ID 映射字典
            record_id_map: 记录 ID 映射字典
        """
        source_records = Record.query.filter_by(table_id=source_table_id).all()
        for source_record in source_records:
            new_values = {}
            for field_id, value in source_record.values.items():
                new_field_id = field_id_map.get(field_id, field_id)
                new_values[new_field_id] = value
    
            new_record = Record(
                table_id=new_table_id,
                values=new_values
            )
            db.session.add(new_record)
            db.session.flush()
            record_id_map[str(source_record.id)] = str(new_record.id)
    
    @staticmethod
    def _copy_link_values(source_table_id: str, field_id_map: dict, 
                          record_id_map: dict, link_field_map: dict) -> None:
        """
        复制关联关系值
    
        Args:
            source_table_id: 源表 ID
            field_id_map: 字段 ID 映射字典
            record_id_map: 记录 ID 映射字典
            link_field_map: 关联字段映射字典
        """
        source_link_fields = Field.query.filter(
            Field.table_id == source_table_id,
            Field.type.in_(['link', 'link_to_record'])
        ).all()
    
        for source_link_field in source_link_fields:
            source_field_id = str(source_link_field.id)
    
            if source_field_id not in link_field_map:
                continue
    
            new_field_id, target_table_id, link_relation_id = link_field_map[source_field_id]
    
            if not link_relation_id:
                continue
    
            source_link_relation = LinkRelation.query.filter_by(source_field_id=source_field_id).first()
            if not source_link_relation:
                continue
    
            source_link_values = LinkValue.query.filter_by(link_relation_id=str(source_link_relation.id)).all()
    
            for link_value in source_link_values:
                source_record_id = str(link_value.source_record_id)
                if source_record_id not in record_id_map:
                    continue
                new_source_record_id = record_id_map[source_record_id]
    
                target_record_id = str(link_value.target_record_id)
                new_target_record_id = record_id_map.get(target_record_id, target_record_id)
    
                new_link_value = LinkValue(
                    link_relation_id=link_relation_id,
                    source_record_id=new_source_record_id,
                    target_record_id=new_target_record_id
                )
                db.session.add(new_link_value)
    
    @staticmethod
    def _copy_view(source_view: 'View', new_table_id: str, field_id_map: dict) -> 'View':
        """
        复制视图
    
        Args:
            source_view: 源视图对象
            new_table_id: 新表 ID
            field_id_map: 字段 ID 映射字典
    
        Returns:
            新创建的视图对象
        """
        new_filters = []
        for filter_item in (source_view.filters or []):
            new_filter = filter_item.copy()
            if 'field_id' in new_filter and new_filter['field_id'] in field_id_map:
                new_filter['field_id'] = field_id_map[new_filter['field_id']]
            new_filters.append(new_filter)
    
        new_sorts = []
        for sort_item in (source_view.sort_config or []):
            new_sort = sort_item.copy()
            if 'field_id' in new_sort and new_sort['field_id'] in field_id_map:
                new_sort['field_id'] = field_id_map[new_sort['field_id']]
            new_sorts.append(new_sort)
    
        new_group_config = source_view.group_config or {}
        if isinstance(new_group_config, dict) and 'group_bys' in new_group_config:
            new_group_bys = [field_id_map.get(fid, fid) for fid in new_group_config['group_bys']]
            new_group_config['group_bys'] = new_group_bys
    
        new_field_visibility = {}
        for field_id, visible in (source_view.field_visibility or {}).items():
            new_field_id = field_id_map.get(field_id, field_id)
            new_field_visibility[new_field_id] = visible
    
        new_hidden_fields = [field_id_map.get(fid, fid) for fid in (source_view.hidden_fields or [])]
        new_frozen_fields = [field_id_map.get(fid, fid) for fid in (source_view.frozen_fields or [])]
    
        new_field_widths = {}
        for field_id, width in (source_view.field_widths or {}).items():
            new_field_id = field_id_map.get(field_id, field_id)
            new_field_widths[new_field_id] = width
    
        new_form_config = source_view.form_config or {}
        if isinstance(new_form_config, dict) and 'fields' in new_form_config:
            new_form_config['fields'] = [field_id_map.get(fid, fid) for fid in new_form_config['fields']]
    
        new_view = View(
            table_id=new_table_id,
            name=source_view.name,
            type=source_view.type,
            description=source_view.description,
            order=source_view.order,
            is_default=source_view.is_default,
            is_public=source_view.is_public,
            filters=new_filters,
            sort_config=new_sorts,
            group_config=new_group_config,
            field_visibility=new_field_visibility,
            hidden_fields=new_hidden_fields,
            frozen_fields=new_frozen_fields,
            row_height=source_view.row_height,
            field_widths=new_field_widths,
            form_config=new_form_config
        )
        db.session.add(new_view)
        return new_view
    
    @staticmethod
    def _copy_dashboard(source_dashboard: 'Dashboard', new_base_id: str, user_id: str,
                        table_id_map: dict, field_id_map: dict) -> 'Dashboard':
        """
        复制仪表盘
    
        Args:
            source_dashboard: 源仪表盘对象
            new_base_id: 新 Base ID
            user_id: 用户 ID
            table_id_map: 表 ID 映射字典
            field_id_map: 字段 ID 映射字典
    
        Returns:
            新创建的仪表盘对象
        """
        new_layout = source_dashboard.layout or {}
        if isinstance(new_layout, dict) and 'table_id' in new_layout:
            if new_layout['table_id'] in table_id_map:
                new_layout['table_id'] = table_id_map[new_layout['table_id']]
    
        new_widgets = []
        for widget in (source_dashboard.widgets or []):
            new_widget = widget.copy()
            if 'table_id' in new_widget and new_widget['table_id'] in table_id_map:
                new_widget['table_id'] = table_id_map[new_widget['table_id']]
            if 'field_id' in new_widget and new_widget['field_id'] in field_id_map:
                new_widget['field_id'] = field_id_map[new_widget['field_id']]
            new_widgets.append(new_widget)
    
        new_dashboard = Dashboard(
            base_id=new_base_id,
            user_id=user_id,
            name=source_dashboard.name,
            description=source_dashboard.description,
            is_default=source_dashboard.is_default,
            layout=new_layout,
            widgets=new_widgets
        )
        db.session.add(new_dashboard)
        return new_dashboard
    
    @staticmethod
    def _fix_link_field_configs(link_field_map: dict) -> None:
        """
        修复关联字段的 config 配置
    
        Args:
            link_field_map: 关联字段映射字典
        """
        from sqlalchemy.orm.attributes import flag_modified
    
        for source_field_id, (new_field_id, target_table_id, link_relation_id) in link_field_map.items():
            if link_relation_id:
                new_field = Field.query.get(new_field_id)
                if new_field:
                    if new_field.config is None:
                        new_field.config = {}
                    current_linked_table_id = new_field.config.get('linkedTableId')
                    if str(current_linked_table_id) != str(target_table_id):
                        current_app.logger.warning(
                            f'[BaseService] 修复字段 {new_field_id} 的 config.linkedTableId: '
                            f'{current_linked_table_id} -> {target_table_id}'
                        )
                        new_field.config['linkedTableId'] = target_table_id
                        flag_modified(new_field, 'config')
    
    @staticmethod
    def copy_base(base_id: str, user_id: str, new_name: str = None) -> Dict[str, Any]:
        """
        复制基础数据（多维表格）
    
        复制内容包括：
        - Base 基本信息
        - 所有数据表结构及字段配置
        - 所有数据记录
        - 所有视图配置
        - 所有仪表盘配置
    
        排除内容：
        - 分享设置
        - 访问权限设置
        - 评论及协作历史记录
    
        Args:
            base_id: 源基础数据 ID
            user_id: 复制操作的用户 ID
            new_name: 新基础数据名称（可选，默认为"原名称+副本"）
    
        Returns:
            包含操作结果的字典
        """
        from app.models.link_relation import LinkValue, LinkRelation
    
        try:
            source_base = Base.query.get(base_id)
            if not source_base:
                return {'success': False, 'error': 'source_base_does_not_exist'}
    
            new_base = BaseService._copy_base_info(source_base, user_id, new_name)
    
            table_id_map = {}
            field_id_map = {}
            record_id_map = {}
            link_field_map = {}
    
            source_tables = Table.query.filter_by(base_id=base_id).all()
            for source_table in source_tables:
                new_table = BaseService._copy_table_and_fields(
                    source_table, str(new_base.id), field_id_map, table_id_map, link_field_map
                )
    
                BaseService._copy_records(
                    str(source_table.id), str(new_table.id), field_id_map, record_id_map
                )
    
                BaseService._copy_link_values(
                    str(source_table.id), field_id_map, record_id_map, link_field_map
                )
    
                source_views = View.query.filter_by(table_id=source_table.id).all()
                for source_view in source_views:
                    BaseService._copy_view(source_view, str(new_table.id), field_id_map)
    
            source_dashboards = Dashboard.query.filter_by(base_id=base_id).all()
            for source_dashboard in source_dashboards:
                BaseService._copy_dashboard(
                    source_dashboard, str(new_base.id), user_id, table_id_map, field_id_map
                )
    
            db.session.commit()
    
            BaseService._fix_link_field_configs(link_field_map)
    
            if link_field_map:
                db.session.commit()
                current_app.logger.info(f'[BaseService] 已验证并修复 {len(link_field_map)} 个关联字段的 config')
    
            current_app.logger.info(f'[BaseService] Base 复制完成：{new_base.id}')
    
            return {
                'success': True,
                'base': new_base.to_dict(),
                'message': 'copied_successfully'
            }
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[BaseService] 复制 Base 失败：{base_id}, 错误：{str(e)}')
            return {'success': False, 'error': 'copy_failed_try_again_later'}
    
