"""
记录服务模块
"""
from typing import List, Optional, Dict, Any
import uuid
import re
from datetime import datetime, timezone

from sqlalchemy import cast, or_, select, and_
from sqlalchemy.types import String
from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.models.record import Record
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.field import Field, FieldType
from app.models.record_history import RecordHistory, HistoryAction
from app.models.table import Table
from app.services.field_service import FieldService
from app.services.formula_service import FormulaService
from app.services.link_service import LinkService
from app.services.workflow_event_bus import workflow_event_bus
from app.errors.handlers import ConflictError

import logging


log = logging.getLogger(__name__)


def _escape_like_pattern(pattern: str) -> str:
    """
    转义 SQL LIKE 查询中的通配符，防止通配符注入
    
    Args:
        pattern: 原始搜索模式
        
    Returns:
        转义后的安全搜索模式
    """
    if not pattern:
        return pattern
    return pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _format_date_value(value: str, field: Field) -> str:
    """
    根据字段类型（date 或 date_time）格式化日期值

    Args:
        value: 原始日期值（ISO 8601 格式或 YYYY-MM-DD 格式）
        field: 字段对象

    Returns:
        格式化后的日期字符串
    """
    if value is None:
        return None

    # 根据字段类型决定格式
    is_date_time = field.type == FieldType.DATE_TIME.value

    try:
        # 解析日期时间
        if 'T' in str(value):
            # ISO 8601 格式: 2026-04-12T00:00:00.000Z 或 2026-04-12T00:00:00+00:00
            dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        else:
            # 已经是 YYYY-MM-DD 或 YYYY-MM-DD HH:mm:ss 格式
            if len(str(value)) <= 10:
                dt = datetime.strptime(str(value), '%Y-%m-%d')
            else:
                dt = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')

        # 根据字段类型格式化
        if is_date_time:
            # 保留 UTC ISO 格式（如 2026-05-10T16:16:40.478Z）
            return dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        else:
            return dt.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # 如果解析失败，返回原始值
        return value

class RecordServiceGroup03Mixin:
    """Mixin auto-split"""
    
    """记录服务类"""
    
    
    @staticmethod
    def get_tree_records(table_id: str, parent_field_id: str) -> List[Dict]:
        """
        获取树形记录数据
    
        根据 parent_field_id 字段的值构建树形结构，最多支持 4 层嵌套。
    
        Args:
            table_id: 表格 ID
            parent_field_id: 父记录字段 ID（LINK_TO_RECORD 类型）
    
        Returns:
            树形记录列表，每个节点包含 id, values, children, depth, has_children
        """
        records = Record.query.filter_by(table_id=table_id).all()
    
        # 构建节点映射
        record_map: Dict[str, Dict] = {}
        for record in records:
            record_map[str(record.id)] = {
                'id': str(record.id),
                'values': dict(record.values) if record.values else {},
                'children': [],
                'depth': 0,
                'has_children': False
            }
    
        # 构建父子关系：自关联字段存储的是父级记录的 ID（每个记录最多一个父级）
        # 记录通过 parent_field_id 指向其父记录；父级字段为空的记录是根节点
        roots: List[Dict] = []
        for node in record_map.values():
            values = node['values']
            parent_id = values.get(parent_field_id)
            if isinstance(parent_id, list):
                parent_id = parent_id[0] if parent_id else None
            elif parent_id is not None:
                parent_id = str(parent_id)
    
            if parent_id and parent_id in record_map:
                parent_node = record_map[parent_id]
                parent_node['children'].append(node)
                parent_node['has_children'] = True
            else:
                roots.append(node)
    
        # 递归设置深度，最多 4 层
        def _assign_depth(nodes: List[Dict], depth: int = 0) -> None:
            if depth >= 4:
                return
            for n in nodes:
                n['depth'] = depth
                if n['children']:
                    _assign_depth(n['children'], depth + 1)
    
        _assign_depth(roots)
    
        return roots
    
    @staticmethod
    def get_filtered_tree_records(table_id: str, parent_field_id: str, search: str) -> List[Dict]:
        """
        获取筛选后的树形记录数据（包含匹配记录的父级上下文）
    
        根据搜索关键词筛选记录，并确保匹配记录的父级祖先链也被包含在结果中，
        以便在前端展示筛选结果时保留层级上下文。
    
        Args:
            table_id: 表格 ID
            parent_field_id: 父记录字段 ID
            search: 搜索关键词
    
        Returns:
            筛选后的树形记录列表
        """
        # 获取所有记录
        records = Record.query.filter_by(table_id=table_id).all()
    
        # 构建节点映射
        record_map: Dict[str, Dict] = {}
        for record in records:
            record_map[str(record.id)] = {
                'id': str(record.id),
                'values': dict(record.values) if record.values else {},
                'children': [],
                'depth': 0,
                'has_children': False
            }
    
        # 构建父子关系：自关联字段存储的是父级记录的 ID（每个记录最多一个父级）
        # 同时构建子记录→父记录的映射，用于查找祖先链
        child_to_parent: Dict[str, str] = {}
        for node in record_map.values():
            values = node['values']
            parent_id = values.get(parent_field_id)
            if isinstance(parent_id, list):
                parent_id = parent_id[0] if parent_id else None
            elif parent_id is not None:
                parent_id = str(parent_id)
    
            if parent_id and parent_id in record_map:
                parent_node = record_map[parent_id]
                parent_node['children'].append(node)
                parent_node['has_children'] = True
                child_to_parent[node['id']] = parent_id
    
        # 搜索匹配的记录 ID 集合
        search_lower = search.lower()
        matched_ids = set()
        for node_id, node in record_map.items():
            values_str = str(node['values']).lower()
            if search_lower in values_str:
                matched_ids.add(node_id)
    
        # 收集匹配记录的祖先链
        ancestor_ids = set()
        for node_id in matched_ids:
            current_id = node_id
            while True:
                parent_id = child_to_parent.get(current_id)
                if parent_id and parent_id in record_map:
                    ancestor_ids.add(parent_id)
                    current_id = parent_id
                else:
                    break
    
        # 需要保留的节点 ID = 匹配记录 + 祖先节点
        keep_ids = matched_ids | ancestor_ids
    
        # 过滤树：只保留需要保留的节点
        def _filter_children(nodes: List[Dict]) -> List[Dict]:
            result = []
            for node in nodes:
                if node['id'] in keep_ids:
                    filtered_children = _filter_children(node['children'])
                    node['children'] = filtered_children
                    if filtered_children:
                        node['has_children'] = True
                    result.append(node)
            return result
    
        # 根节点：父级字段为空（或父级不在当前表中）的记录
        roots: List[Dict] = []
        for node in record_map.values():
            if node['id'] not in child_to_parent:
                roots.append(node)
    
        # 过滤并设置深度
        filtered_roots = _filter_children(roots)
    
        def _assign_depth(nodes: List[Dict], depth: int = 0) -> None:
            if depth >= 4:
                return
            for n in nodes:
                n['depth'] = depth
                if n['children']:
                    _assign_depth(n['children'], depth + 1)
    
        _assign_depth(filtered_roots)
    
        return filtered_roots
    
    @staticmethod
    def search_records(table_id: str, query: str, 
                      field_ids: List[str] = None,
                      page: int = 1, per_page: int = 100) -> tuple:
        """
        搜索记录（B7 已下推到 SQL 分页）
    
        Args:
            table_id: 表格 ID
            query: 搜索关键词
            field_ids: 要搜索的字段 ID 列表；为 None 时搜索表内全部字段
            page: 页码（从 1 开始），默认 1
            per_page: 每页条数，默认 100；传 None 或 0 表示不限制（全量拉回）
    
        Returns:
            (records, total) 元组
        """
        escaped_query = _escape_like_pattern(query)
        like_pattern = f'%{escaped_query}%'
    
        if not field_ids:
            fields = FieldService.get_all_fields(table_id)
            field_ids = [str(f.id) for f in fields]
    
        query_obj = Record.query.filter_by(table_id=table_id, is_deleted=False)
    
        if field_ids:
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            valid_field_ids = [fid for fid in field_ids if uuid_pattern.match(str(fid))]
    
            if not valid_field_ids:
                return [], 0
    
            conditions = []
            for field_id in valid_field_ids:
                conditions.append(Record.values.op('->>')(field_id).ilike(like_pattern))
            if conditions:
                query_obj = query_obj.filter(or_(*conditions))
    
        # B7：total 用 SQL COUNT（比 Python len(all()) 快得多，10 万行差 ~10 倍）
        total = query_obj.count()
    
        # B7：SQL 分页 — per_page=None/0 表示不限制（linkable_records 场景需要全量）
        ordered_query = query_obj.order_by(
            Record.created_at.desc(), Record.id.desc()
        )
        if per_page:
            records = ordered_query.offset(
                (page - 1) * per_page
            ).limit(per_page).all()
        else:
            records = ordered_query.all()
    
        return records, total
    
