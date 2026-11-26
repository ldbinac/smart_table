"""
关联字段服务模块
处理 LinkRelation（关联关系）和 LinkValue（关联值）的 CRUD 操作
支持双向关联的自动同步
使用 Redis 缓存优化性能
"""
import json
import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.attributes import flag_modified
from flask import current_app

from app.extensions import db, cache
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.field import Field, FieldType
from app.models.record import Record
from app.models.table import Table
from app.services.table_service import TableService
from app.services.field_service import FieldService
from app.i18n import translate


# 缓存键前缀
CACHE_PREFIX = "link:"
CACHE_TTL = 300  # 5分钟缓存过期时间


def _get_cache_key(*parts: str) -> str:
    """生成缓存键"""
    return f"{CACHE_PREFIX}{':'.join(parts)}"


def _get_record_links_cache_key(record_id: str) -> str:
    """获取记录关联数据的缓存键"""
    return _get_cache_key("record", record_id, "links")


def _get_field_links_cache_key(field_id: str) -> str:
    """获取字段关联关系的缓存键"""
    return _get_cache_key("field", field_id, "relation")


def _invalidate_record_links_cache(record_id: str) -> None:
    """清除记录关联数据的缓存"""
    cache_key = _get_record_links_cache_key(record_id)
    cache.delete(cache_key)
    current_app.logger.debug(f"[LinkService] 清除缓存: {cache_key}")


def _invalidate_field_links_cache(field_id: str) -> None:
    """清除字段关联关系的缓存"""
    cache_key = _get_field_links_cache_key(field_id)
    cache.delete(cache_key)
    current_app.logger.debug(f"[LinkService] 清除缓存: {cache_key}")


def _format_select_display_value(raw_value: Any, field: Field) -> str:
    """
    将单选/多选字段的原始值转换为可读的选项名称
    
    Args:
        raw_value: 字段原始值（可能是 ID、ID 列表、JSON 字符串或对象）
        field: 字段对象
        
    Returns:
        可读的选项名称字符串
    """
    if not field or not field.options:
        return str(raw_value) if raw_value is not None else ''
    
    options = field.options.get('choices') or field.options.get('options') or []
    if not isinstance(options, list):
        return str(raw_value) if raw_value is not None else ''
    
    # 构建 ID->名称 和 名称->名称 的映射
    option_map: Dict[str, str] = {}
    for opt in options:
        if isinstance(opt, dict):
            opt_id = str(opt.get('id', ''))
            opt_name = str(opt.get('name', ''))
            if opt_id:
                option_map[opt_id] = opt_name or opt_id
            if opt_name:
                option_map[opt_name] = opt_name
    
    if field.type == FieldType.SINGLE_SELECT.value:
        # 兼容对象格式 {id, name}
        if isinstance(raw_value, dict):
            raw_value = raw_value.get('name') or raw_value.get('id')
        key = str(raw_value) if raw_value is not None else ''
        return option_map.get(key, key)
    
    if field.type == FieldType.MULTI_SELECT.value:
        ids: List[Any] = []
        if isinstance(raw_value, list):
            ids = raw_value
        elif isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, list):
                    ids = parsed
            except Exception:
                ids = [v.strip() for v in raw_value.split(',') if v.strip()]
        
        names: List[str] = []
        for item in ids:
            if isinstance(item, dict):
                item_id = str(item.get('id', ''))
                item_name = str(item.get('name', ''))
                names.append(item_name or option_map.get(item_id, item_id))
            else:
                item_key = str(item)
                names.append(option_map.get(item_key, item_key))
        return ', '.join(names)
    
    return str(raw_value) if raw_value is not None else ''

class LinkServiceGroup02Mixin:
    """Mixin auto-split"""
    
    """关联字段服务类"""
    
    
    @staticmethod
    def batch_match_link_values(
        field_id: str,
        match_field_id: str,
        pairs: List[Dict[str, Any]],
        updated_by: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        按值批量匹配并建立关联（用于 Excel 导入自动关联场景）
    
        根据关联字段的目标表，在 match_field_id 字段上按 pairs 中的值
        精确匹配目标记录，批量创建 LinkValue 并同步双向冗余存储。
    
        Args:
            field_id: 关联字段 ID（link / link_to_record 类型）
            match_field_id: 目标表中用于匹配值的字段 ID
            pairs: [{record_id: 源记录 ID, value: 匹配值}]
            updated_by: 操作者 ID（预留）
    
        Returns:
            (统计结果 dict 或 None, 错误信息)
            统计: {matched_count, unmatched_count, unmatched_values,
                   skipped_count, duplicate_target_count}
        """
        try:
            # 1. 校验关联字段并获取/补建关联关系
            field = db.session.get(Field, field_id)
            if not field:
                return None, 'field_does_not_exist'
            if field.type not in [FieldType.LINK_TO_RECORD.value, FieldType.LINK.value]:
                return None, 'field_not_link_field'
    
            link_relation, rel_error = LinkService._get_or_create_link_relation_for_field(field)
            if not link_relation:
                return None, rel_error
    
            # 2. 校验匹配字段属于目标表
            match_field = db.session.get(Field, match_field_id)
            if not match_field:
                return None, 'field_does_not_exist'
            if str(match_field.table_id) != str(link_relation.target_table_id):
                return None, 'match_field_not_in_target_table'
    
            empty_result = {
                'matched_count': 0,
                'unmatched_count': 0,
                'unmatched_values': [],
                'skipped_count': 0,
                'duplicate_target_count': 0
            }
            if not pairs:
                return empty_result, None
    
            # 3. 校验源记录属于关联字段所在表（一次 IN 查询）
            source_record_ids = list({str(p.get('record_id')) for p in pairs if p.get('record_id')})
            source_records = Record.query.filter(
                Record.id.in_(source_record_ids),
                Record.table_id == field.table_id
            ).all() if source_record_ids else []
            valid_source_ids = {str(r.id) for r in source_records}
    
            # 4. 构建目标表匹配映射（重复值取第一条并计数）
            target_records = Record.query.filter_by(table_id=link_relation.target_table_id).all()
            value_map: Dict[str, str] = {}
            duplicate_target_count = 0
            for tr in target_records:
                raw = (tr.values or {}).get(str(match_field.id))
                if raw is None or (isinstance(raw, (list, dict))):
                    continue
                key = str(raw).strip()
                if not key:
                    continue
                if key in value_map:
                    duplicate_target_count += 1
                    continue
                value_map[key] = str(tr.id)
    
            # 5. 逐 pair 匹配
            one_to_one = link_relation.relationship_type == RelationshipType.ONE_TO_ONE.value
            matched: Dict[str, List[str]] = {}
            unmatched_counter: Dict[str, int] = {}
            skipped_count = 0
    
            def _match_keys(raw_value):
                """把导出的单元格值解析为待匹配的显示名称列表。
    
                关联字段导出格式是 ", " 分隔的显示名称（一对多），历史版本还会
                把双向关联重复导出成「苹果, 苹果」。优先整串精确匹配，避免把
                名称本身含逗号的记录误拆；整串匹配不到时再按中英文逗号拆分，
                并去重以兼容历史重复值。
                """
                key = str(raw_value).strip() if raw_value is not None else ''
                if not key:
                    return []
                if key in value_map:
                    return [key]
                parts = [part.strip() for part in re.split(r'[,，]', key) if part.strip()]
                if len(parts) <= 1:
                    return [key]
                return list(dict.fromkeys(parts))
    
            for p in pairs:
                src = str(p.get('record_id') or '')
                raw_value = p.get('value')
                key = str(raw_value).strip() if raw_value is not None else ''
                if not src or src not in valid_source_ids or not key:
                    skipped_count += 1
                    continue
                for match_key in _match_keys(raw_value):
                    target_id = value_map.get(match_key)
                    if not target_id:
                        unmatched_counter[match_key] = unmatched_counter.get(match_key, 0) + 1
                        continue
                    bucket = matched.setdefault(src, [])
                    if one_to_one and bucket:
                        skipped_count += 1
                        continue
                    if target_id not in bucket:
                        bucket.append(target_id)
    
            # 6. 过滤已存在的关联
            all_new = [(src, tid) for src, tids in matched.items() for tid in tids]
            existing: set = set()
            if all_new:
                src_ids = list({s for s, _ in all_new})
                rows = db.session.execute(
                    select(LinkValue.source_record_id, LinkValue.target_record_id).where(
                        and_(
                            LinkValue.link_relation_id == link_relation.id,
                            LinkValue.source_record_id.in_(src_ids)
                        )
                    )
                ).all()
                existing = {(str(s), str(t)) for s, t in rows}
            to_insert = [(s, t) for s, t in all_new if (s, t) not in existing]
    
            # 7. 批量插入 LinkValue，并同步源/目标记录的 values 冗余存储
            source_field_key = str(field.id)
            inverse_field_key = (
                str(link_relation.target_field_id)
                if (link_relation.bidirectional and link_relation.target_field_id)
                else None
            )
            target_ids_involved = {t for _, t in to_insert}
            target_record_map: Dict[str, Record] = {}
            if target_ids_involved:
                trows = Record.query.filter(Record.id.in_(list(target_ids_involved))).all()
                target_record_map = {str(t.id): t for t in trows}
            source_record_map = {str(r.id): r for r in source_records}
    
            for src, tid in to_insert:
                db.session.add(LinkValue(
                    link_relation_id=link_relation.id,
                    source_record_id=src,
                    target_record_id=tid
                ))
    
                s_rec = source_record_map.get(src)
                if s_rec is not None:
                    sv = dict(s_rec.values or {})
                    cur = sv.get(source_field_key)
                    if not isinstance(cur, list):
                        cur = [cur] if cur else []
                    if tid not in cur:
                        cur.append(tid)
                    sv[source_field_key] = cur
                    s_rec.values = sv
                    flag_modified(s_rec, 'values')
    
                if inverse_field_key:
                    t_rec = target_record_map.get(tid)
                    if t_rec is not None:
                        tv = dict(t_rec.values or {})
                        cur = tv.get(inverse_field_key)
                        if not isinstance(cur, list):
                            cur = [cur] if cur else []
                        if src not in cur:
                            cur.append(src)
                            tv[inverse_field_key] = cur
                            t_rec.values = tv
                            flag_modified(t_rec, 'values')
    
            db.session.commit()
    
            # 8. 清除涉及的记录关联缓存
            touched = {s for s, _ in to_insert} | {t for _, t in to_insert}
            for rid in touched:
                _invalidate_record_links_cache(rid)
    
            unmatched_values = sorted(
                [{'value': v, 'count': c} for v, c in unmatched_counter.items()],
                key=lambda x: x['count'], reverse=True
            )[:50]
    
            result = {
                'matched_count': len(to_insert),
                'unmatched_count': sum(unmatched_counter.values()),
                'unmatched_values': unmatched_values,
                'skipped_count': skipped_count,
                'duplicate_target_count': duplicate_target_count
            }
            current_app.logger.info(
                f'[LinkService] 批量匹配关联: field={field_id}, match_field={match_field_id}, '
                f"matched={result['matched_count']}, unmatched={result['unmatched_count']}, "
                f"skipped={result['skipped_count']}"
            )
            return result, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 批量匹配关联失败: {str(e)}')
            return None, 'failed_batch_match_link_values_try_again_later'
    
    @staticmethod
    def _sync_bidirectional_links(
        link_relation: LinkRelation,
        source_record_id: str,
        target_record_ids: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        同步双向关联
    
        Args:
            link_relation: 关联关系对象
            source_record_id: 源记录 ID
            target_record_ids: 目标记录 ID 列表
    
        Returns:
            (是否成功, 错误信息)
        """
        try:
            if not link_relation.target_field_id:
                return True, None  # 没有目标字段，无需同步
    
            # 查找或创建反向的关联关系
            reverse_relation = db.session.execute(
                select(LinkRelation).where(
                    and_(
                        LinkRelation.source_field_id == link_relation.target_field_id,
                        LinkRelation.target_field_id == link_relation.source_field_id
                    )
                )
            ).scalar_one_or_none()
    
            if not reverse_relation:
                inverse_relationship_type = LinkService.get_inverse_relationship_type(link_relation.relationship_type)
                current_app.logger.info(
                    f'[_sync_bidirectional_links] 创建反向关联关系: '
                    f'正向类型={link_relation.relationship_type}, 反向类型={inverse_relationship_type}'
                )
                reverse_relation = LinkRelation(
                    source_table_id=link_relation.target_table_id,
                    target_table_id=link_relation.source_table_id,
                    source_field_id=link_relation.target_field_id,
                    target_field_id=link_relation.source_field_id,
                    relationship_type=inverse_relationship_type,
                    bidirectional=True
                )
                db.session.add(reverse_relation)
                db.session.flush()
    
            # 对每个目标记录，更新其反向关联
            for target_id in target_record_ids:
                target_record = db.session.get(Record, target_id)
                if not target_record:
                    continue
    
                # 获取目标记录当前的反向关联
                existing_reverse = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == reverse_relation.id,
                            LinkValue.source_record_id == target_id,
                            LinkValue.target_record_id == source_record_id
                        )
                    )
                ).scalar_one_or_none()
    
                # 如果不存在，创建反向关联
                if not existing_reverse:
                    reverse_link = LinkValue(
                        link_relation_id=reverse_relation.id,
                        source_record_id=target_id,
                        target_record_id=source_record_id
                    )
                    db.session.add(reverse_link)
    
                # 更新目标记录的字段值
                target_values = target_record.values or {}
                current_links = target_values.get(str(link_relation.target_field_id), [])
                if not isinstance(current_links, list):
                    current_links = [current_links] if current_links else []
                if source_record_id not in current_links:
                    current_links.append(source_record_id)
                    target_values[str(link_relation.target_field_id)] = current_links
                    target_record.values = target_values
                    flag_modified(target_record, 'values')
    
            # 处理已移除的关联（需要删除反向关联）
            # 获取所有应该存在的反向关联
            existing_reverse_links = db.session.execute(
                select(LinkValue).where(
                    and_(
                        LinkValue.link_relation_id == reverse_relation.id,
                        LinkValue.target_record_id == source_record_id
                    )
                )
            ).scalars().all()
    
            for reverse_link in existing_reverse_links:
                if str(reverse_link.source_record_id) not in target_record_ids:
                    # 删除这个反向关联
                    db.session.delete(reverse_link)
    
                    # 更新对应记录的字段值
                    target_record = db.session.get(Record, reverse_link.source_record_id)
                    if target_record:
                        target_values = target_record.values or {}
                        current_links = target_values.get(str(link_relation.target_field_id), [])
                        if isinstance(current_links, list) and source_record_id in current_links:
                            current_links.remove(source_record_id)
                            target_values[str(link_relation.target_field_id)] = current_links
                            target_record.values = target_values
                            flag_modified(target_record, 'values')
    
            current_app.logger.info(
                f'[LinkService] 双向关联同步完成: link_relation={link_relation.id}'
            )
    
            return True, None
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 双向关联同步失败: {str(e)}')
            'bidirectional_link_sync_failed_try_again_later'
    
    @staticmethod
    def sync_bidirectional_link(link_relation_id: str) -> Tuple[bool, Optional[str]]:
        """
        同步双向关联（重新计算所有关联）
    
        Args:
            link_relation_id: 关联关系 ID
    
        Returns:
            (是否成功, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            if not link_relation.bidirectional:
                return True, None  # 不是双向关联，无需同步
    
            # 获取所有关联值
            all_link_values = db.session.execute(
                select(LinkValue).where(
                    LinkValue.link_relation_id == link_relation_id
                )
            ).scalars().all()
    
            # 按源记录分组
            links_by_source: Dict[str, List[str]] = {}
            for link_value in all_link_values:
                source_id = str(link_value.source_record_id)
                target_id = str(link_value.target_record_id)
                if source_id not in links_by_source:
                    links_by_source[source_id] = []
                links_by_source[source_id].append(target_id)
    
            # 对每个源记录同步双向关联
            for source_id, target_ids in links_by_source.items():
                result, error = LinkService._sync_bidirectional_links(
                    link_relation, source_id, target_ids
                )
                if not result:
                    db.session.rollback()
                    return False, translate('sync_record_failed', source_id, error)
    
            current_app.logger.info(
                f'[LinkService] 双向关联全量同步完成: link_relation={link_relation_id}, '
                f'处理了 {len(links_by_source)} 个源记录'
            )
    
            db.session.commit()
            return True, None
    
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'[LinkService] 双向关联同步失败: {str(e)}')
            'bidirectional_link_sync_failed_try_again_later'
    
    @staticmethod
    def get_table_link_relations(table_id: str) -> List[LinkRelation]:
        """
        获取表格的所有关联关系（作为源表或目标表）
    
        Args:
            table_id: 表格 ID
    
        Returns:
            关联关系列表
        """
        try:
            results = db.session.execute(
                select(LinkRelation).where(
                    or_(
                        LinkRelation.source_table_id == table_id,
                        LinkRelation.target_table_id == table_id
                    )
                )
            ).scalars().all()
    
            return list(results)
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 获取表格关联关系失败: {str(e)}')
            return []
    
    @staticmethod
    def validate_link_constraint(
        link_relation_id: str,
        source_record_id: str,
        target_record_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        验证关联约束（如一对一约束）
    
        Args:
            link_relation_id: 关联关系 ID
            source_record_id: 源记录 ID
            target_record_id: 目标记录 ID
    
        Returns:
            (是否通过验证, 错误信息)
        """
        try:
            link_relation = db.session.get(LinkRelation, link_relation_id)
            if not link_relation:
                'link_relation_does_not_exist'
    
            # 一对一约束检查
            if link_relation.relationship_type == RelationshipType.ONE_TO_ONE.value:
                # 检查源记录是否已有其他关联
                existing = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkValue.link_relation_id == link_relation_id,
                            LinkValue.source_record_id == source_record_id
                        )
                    )
                ).scalar_one_or_none()
    
                if existing and str(existing.target_record_id) != target_record_id:
                    'one_one_constraint_source_record_already_link'
    
                # 检查目标记录是否已被其他源记录关联
                existing_target = db.session.execute(
                    select(LinkValue).where(
                        and_(
                            LinkRelation.id == link_relation_id,
                            LinkValue.target_record_id == target_record_id
                        )
                    )
                ).scalar_one_or_none()
    
                if existing_target and str(existing_target.source_record_id) != source_record_id:
                    'one_one_constraint_target_record_already_linked_another_record'
    
            return True, None
    
        except Exception as e:
            current_app.logger.error(f'[LinkService] 验证关联约束失败: {str(e)}')
            'verification_failed_try_again_later'
    
