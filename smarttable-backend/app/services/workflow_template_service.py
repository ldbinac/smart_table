"""
工作流模板服务模块

提供工作流模板的 CRUD、从工作流保存为模板、以及从模板创建工作流的能力。
"""
import copy
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.extensions import db
from app.models.base import MemberRole
from app.models.table import Table
from app.models.user import User
from app.models.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowTrigger,
    WorkflowStatus,
    WorkflowNodeType,
    WorkflowTriggerType,
    WorkflowVersion
)
from app.models.workflow_template import WorkflowTemplate
from app.services.permission_service import PermissionService


log = logging.getLogger(__name__)


# 系统内置工作流模板默认配置
DEFAULT_WORKFLOW_TEMPLATES = [
    {
        'name': '请假审批',
        'description': '新记录创建时自动发起请假审批流程，支持上级或指定用户审批（或签模式）。',
        'category': 'approval',
        'config_snapshot': {
            'name': '请假审批',
            'description': '新记录创建时自动发起请假审批流程，支持上级或指定用户审批（或签模式）。',
            'triggers': [
                {
                    'trigger_type': 'record_created',
                    'filter_config': {
                        'operator': 'and',
                        'conditions': []
                    },
                    'field_ids': []
                }
            ],
            'nodes': [
                {
                    'node_type': 'approval',
                    'name': '审批节点',
                    'config': {
                        'approver_type': 'supervisor',
                        'approver_user_ids': [],
                        'approval_mode': 'any',
                        'approval_title': '请假审批',
                        'approval_description': '请审批该请假申请'
                    },
                    'order': 0,
                    'next_nodes': []
                }
            ]
        }
    },
    {
        'name': '报销审批',
        'description': '新记录创建时自动发起报销审批流程，支持财务或指定用户审批（会签模式）。',
        'category': 'approval',
        'config_snapshot': {
            'name': '报销审批',
            'description': '新记录创建时自动发起报销审批流程，支持财务或指定用户审批（会签模式）。',
            'triggers': [
                {
                    'trigger_type': 'record_created',
                    'filter_config': {
                        'operator': 'and',
                        'conditions': []
                    },
                    'field_ids': []
                }
            ],
            'nodes': [
                {
                    'node_type': 'approval',
                    'name': '财务审批',
                    'config': {
                        'approver_type': 'finance',
                        'approver_user_ids': [],
                        'approval_mode': 'all',
                        'approval_title': '报销审批',
                        'approval_description': '请审批该报销申请'
                    },
                    'order': 0,
                    'next_nodes': []
                }
            ]
        }
    },
    {
        'name': '记录状态自动同步',
        'description': '记录状态字段更新时，根据状态值自动同步更新其他字段。',
        'category': 'automation',
        'config_snapshot': {
            'name': '记录状态自动同步',
            'description': '记录状态字段更新时，根据状态值自动同步更新其他字段。',
            'triggers': [
                {
                    'trigger_type': 'record_updated',
                    'filter_config': {
                        'operator': 'and',
                        'conditions': []
                    },
                    'field_ids': ['status']
                }
            ],
            'nodes': [
                {
                    'node_type': 'condition',
                    'name': '判断状态',
                    'config': {
                        'condition': {
                            'operator': 'and',
                            'conditions': [
                                {
                                    'field_id': 'status',
                                    'operator': 'eq',
                                    'value': 'completed'
                                }
                            ]
                        }
                    },
                    'order': 0,
                    'next_nodes': []
                },
                {
                    'node_type': 'action',
                    'name': '同步更新字段',
                    'config': {
                        'action_type': 'update_record',
                        'updates': [
                            {
                                'field_id': 'sync_status',
                                'value': 'done'
                            }
                        ]
                    },
                    'order': 1,
                    'next_nodes': []
                }
            ]
        }
    }
]


class WorkflowTemplateService:
    """工作流模板服务"""

    @staticmethod
    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    @classmethod
    def _is_admin(cls, user_id: Any) -> bool:
        """判断用户是否为系统管理员"""
        if user_id is None:
            return False
        user = User.query.get(str(user_id))
        return user is not None and user.is_admin()

    @classmethod
    def _check_editor_permission(
        cls,
        base_id: Any,
        user_id: Any
    ) -> bool:
        """校验用户是否对指定 Base 拥有 editor 及以上权限"""
        if base_id is None or user_id is None:
            return False
        return PermissionService.check_permission(
            base_id=str(base_id),
            user_id=str(user_id),
            min_role=MemberRole.EDITOR
        )

    @classmethod
    def _check_viewer_permission(
        cls,
        base_id: Any,
        user_id: Any
    ) -> bool:
        """校验用户是否对指定 Base 拥有 viewer 及以上权限"""
        if base_id is None or user_id is None:
            return False
        return PermissionService.check_permission(
            base_id=str(base_id),
            user_id=str(user_id),
            min_role=MemberRole.VIEWER
        )

    @classmethod
    def list_templates(
        cls,
        category: Optional[str] = None,
        is_system: Optional[bool] = None,
        page: int = 1,
        per_page: int = 20,
        base_id: Any = None,
        user_id: Any = None
    ) -> Dict[str, Any]:
        """
        模板列表，支持分类和是否系统模板筛选

        Args:
            category: 分类过滤
            is_system: 是否系统模板过滤
            page: 页码
            per_page: 每页数量
            base_id: 所属 Base ID（用于权限校验，可选）
            user_id: 用户 ID（用于权限校验，可选）

        Returns:
            包含 items、total、page、per_page 的字典
        """
        if base_id is not None and user_id is not None:
            if not cls._check_viewer_permission(base_id, user_id):
                return {'items': [], 'total': 0, 'page': page, 'per_page': per_page}

        query = WorkflowTemplate.query

        if category is not None:
            query = query.filter_by(category=category)
        if is_system is not None:
            query = query.filter_by(is_system=is_system)

        total = query.count()
        items = query.order_by(
            WorkflowTemplate.is_system.desc(),
            WorkflowTemplate.updated_at.desc()
        ).offset((page - 1) * per_page).limit(per_page).all()

        return {
            'items': [item.to_dict() for item in items],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @classmethod
    def get_template(
        cls,
        template_id: Any,
        base_id: Any = None,
        user_id: Any = None
    ) -> Optional[WorkflowTemplate]:
        """
        模板详情

        Args:
            template_id: 模板 ID
            base_id: 所属 Base ID（用于权限校验，可选）
            user_id: 用户 ID（用于权限校验，可选）

        Returns:
            模板对象，未找到或无权限返回 None
        """
        if base_id is not None and user_id is not None:
            if not cls._check_viewer_permission(base_id, user_id):
                return None

        return WorkflowTemplate.query.filter_by(
            id=cls._to_uuid(template_id)
        ).first()

    @classmethod
    def create_template(
        cls,
        name: str,
        description: Optional[str],
        category: Optional[str],
        config_snapshot: Dict[str, Any],
        created_by: Any,
        is_system: bool = False,
        base_id: Any = None
    ) -> Optional[WorkflowTemplate]:
        """
        创建模板

        Args:
            name: 模板名称
            description: 描述
            category: 分类
            config_snapshot: 配置快照
            created_by: 创建者 ID
            is_system: 是否系统模板
            base_id: 所属 Base ID（用于权限校验，可选）

        Returns:
            创建的模板对象，无权限返回 None
        """
        if base_id is not None and created_by is not None:
            if not cls._check_editor_permission(base_id, created_by):
                log.warning(f'[WorkflowTemplateService] 用户 {created_by} 无权限创建模板')
                return None

        template = WorkflowTemplate(
            name=name,
            description=description,
            category=category,
            config_snapshot=config_snapshot or {},
            is_system=is_system,
            created_by=cls._to_uuid(created_by)
        )

        db.session.add(template)
        db.session.commit()
        log.info(f'[WorkflowTemplateService] 模板已创建: {template.id}')
        return template

    @classmethod
    def update_template(
        cls,
        template_id: Any,
        **kwargs
    ) -> Optional[WorkflowTemplate]:
        """
        更新模板（仅非系统模板或管理员可更新）

        Args:
            template_id: 模板 ID
            **kwargs: 更新字段，可包含 user_id、base_id 用于权限校验

        Returns:
            更新后的模板对象，未找到或无权限返回 None
        """
        user_id = kwargs.pop('user_id', None)
        base_id = kwargs.pop('base_id', None)

        template = WorkflowTemplate.query.filter_by(
            id=cls._to_uuid(template_id)
        ).first()

        if not template:
            return None

        # 系统模板仅管理员可更新
        if template.is_system and not cls._is_admin(user_id):
            log.warning(f'[WorkflowTemplateService] 非管理员无法更新系统模板: {template_id}')
            return None

        if base_id is not None and user_id is not None:
            if not cls._check_editor_permission(base_id, user_id):
                log.warning(f'[WorkflowTemplateService] 用户 {user_id} 无权限更新模板')
                return None

        allowed_fields = {'name', 'description', 'category', 'config_snapshot'}
        for field_name in allowed_fields:
            if field_name in kwargs:
                setattr(template, field_name, kwargs[field_name])

        db.session.commit()
        log.info(f'[WorkflowTemplateService] 模板已更新: {template.id}')
        return template

    @classmethod
    def delete_template(
        cls,
        template_id: Any,
        user_id: Any = None,
        base_id: Any = None
    ) -> bool:
        """
        删除模板（仅非系统模板或管理员可删除）

        Args:
            template_id: 模板 ID
            user_id: 用户 ID（用于权限校验，可选）
            base_id: 所属 Base ID（用于权限校验，可选）

        Returns:
            是否删除成功
        """
        template = WorkflowTemplate.query.filter_by(
            id=cls._to_uuid(template_id)
        ).first()

        if not template:
            return False

        # 系统模板仅管理员可删除
        if template.is_system and not cls._is_admin(user_id):
            log.warning(f'[WorkflowTemplateService] 非管理员无法删除系统模板: {template_id}')
            return False

        if base_id is not None and user_id is not None:
            if not cls._check_editor_permission(base_id, user_id):
                log.warning(f'[WorkflowTemplateService] 用户 {user_id} 无权限删除模板')
                return False

        db.session.delete(template)
        db.session.commit()
        log.info(f'[WorkflowTemplateService] 模板已删除: {template_id}')
        return True

    @classmethod
    def save_as_template(
        cls,
        workflow_id: Any,
        name: str,
        description: Optional[str],
        category: Optional[str],
        created_by: Any
    ) -> Optional[uuid.UUID]:
        """
        将工作流当前版本保存为模板

        Args:
            workflow_id: 工作流 ID
            name: 模板名称
            description: 描述
            category: 分类
            created_by: 创建者 ID

        Returns:
            新模板 ID，失败返回 None
        """
        workflow = Workflow.query.filter_by(
            id=cls._to_uuid(workflow_id),
            is_deleted=False
        ).first()

        if not workflow:
            log.warning(f'[WorkflowTemplateService] 工作流不存在: {workflow_id}')
            return None

        # 权限校验：需要对工作流所属 Base 拥有 editor 及以上权限
        if not cls._check_editor_permission(workflow.base_id, created_by):
            log.warning(f'[WorkflowTemplateService] 用户 {created_by} 无权限保存模板')
            return None

        # 优先读取当前版本的 config_snapshot，否则根据当前节点和触发器构建
        config_snapshot = None
        if workflow.current_version > 0:
            version = WorkflowVersion.query.filter_by(
                workflow_id=workflow.id,
                version_number=workflow.current_version
            ).first()
            if version and version.config_snapshot:
                config_snapshot = copy.deepcopy(version.config_snapshot)

        if not config_snapshot:
            config_snapshot = {
                'name': workflow.name,
                'description': workflow.description,
                'nodes': [node.to_dict() for node in workflow.nodes.order_by(WorkflowNode.order).all()],
                'triggers': [trigger.to_dict() for trigger in workflow.triggers.all()]
            }

        # 覆盖名称和描述，确保模板元数据由调用方指定
        config_snapshot['name'] = name
        config_snapshot['description'] = description

        template = WorkflowTemplate(
            name=name,
            description=description,
            category=category,
            config_snapshot=config_snapshot,
            is_system=False,
            created_by=cls._to_uuid(created_by)
        )

        db.session.add(template)
        db.session.commit()
        log.info(f'[WorkflowTemplateService] 工作流 {workflow_id} 已保存为模板: {template.id}')
        return template.id

    @classmethod
    def create_from_template(
        cls,
        template_id: Any,
        table_id: Any,
        created_by: Any
    ) -> Optional[uuid.UUID]:
        """
        基于模板在指定 table 上创建新的工作流（状态为 draft）

        Args:
            template_id: 模板 ID
            table_id: 表格 ID
            created_by: 创建者 ID

        Returns:
            新工作流 ID，失败返回 None
        """
        template = WorkflowTemplate.query.filter_by(
            id=cls._to_uuid(template_id)
        ).first()

        if not template:
            log.warning(f'[WorkflowTemplateService] 模板不存在: {template_id}')
            return None

        table = Table.query.filter_by(id=cls._to_uuid(table_id)).first()
        if not table:
            log.warning(f'[WorkflowTemplateService] 表格不存在: {table_id}')
            return None

        # 权限校验：需要对该表格所属 Base 拥有 editor 及以上权限
        if not cls._check_editor_permission(table.base_id, created_by):
            log.warning(f'[WorkflowTemplateService] 用户 {created_by} 无权限从模板创建工作流')
            return None

        config_snapshot = template.config_snapshot or {}

        workflow = Workflow(
            base_id=table.base_id,
            table_id=table.id,
            name=config_snapshot.get('name', template.name),
            description=config_snapshot.get('description', template.description),
            status=WorkflowStatus.DRAFT,
            created_by=cls._to_uuid(created_by)
        )

        db.session.add(workflow)
        db.session.flush()

        # 复制触发器配置
        for trigger_data in config_snapshot.get('triggers', []):
            trigger_type = trigger_data.get('trigger_type')
            trigger = WorkflowTrigger(
                workflow_id=workflow.id,
                trigger_type=WorkflowTriggerType(trigger_type) if trigger_type else WorkflowTriggerType.RECORD_CREATED,
                filter_config=trigger_data.get('filter_config', {}),
                field_ids=trigger_data.get('field_ids', [])
            )
            db.session.add(trigger)

        # 复制节点配置
        old_node_id_map: Dict[str, str] = {}
        nodes_config = config_snapshot.get('nodes', [])

        for index, node_data in enumerate(nodes_config):
            old_node_id = node_data.get('id')
            node = WorkflowNode(
                workflow_id=workflow.id,
                node_type=WorkflowNodeType(node_data.get('node_type', 'action')),
                name=node_data.get('name', f'节点 {index + 1}'),
                config=node_data.get('config', {}),
                order=node_data.get('order', index),
                next_nodes=[]
            )
            db.session.add(node)
            db.session.flush()
            if old_node_id:
                old_node_id_map[old_node_id] = str(node.id)

        # 重建 next_nodes 中的旧节点 ID 映射为新节点 ID
        new_nodes = WorkflowNode.query.filter_by(workflow_id=workflow.id).order_by(WorkflowNode.order).all()
        for new_node, node_data in zip(new_nodes, nodes_config):
            old_next_nodes = node_data.get('next_nodes', [])
            new_next_nodes = []
            for next_id in old_next_nodes:
                mapped_id = old_node_id_map.get(str(next_id))
                if mapped_id:
                    new_next_nodes.append(mapped_id)
            new_node.next_nodes = new_next_nodes

        db.session.commit()
        log.info(f'[WorkflowTemplateService] 已从模板 {template_id} 创建工作流: {workflow.id}')
        return workflow.id


def init_default_templates():
    """
    初始化系统内置工作流模板
    如果模板已存在则跳过，避免重复创建
    """
    try:
        print("[WorkflowTemplateService] 开始初始化系统工作流模板...")

        created_count = 0
        skipped_count = 0

        for template_data in DEFAULT_WORKFLOW_TEMPLATES:
            name = template_data['name']

            existing = WorkflowTemplate.query.filter_by(
                name=name,
                is_system=True
            ).first()

            if existing:
                print(f"[WorkflowTemplateService] 系统模板 '{name}' 已存在，跳过")
                skipped_count += 1
                continue

            template = WorkflowTemplate(
                name=name,
                description=template_data['description'],
                category=template_data['category'],
                config_snapshot=template_data['config_snapshot'],
                is_system=True,
                created_by=None
            )

            db.session.add(template)
            print(f"[WorkflowTemplateService] 创建系统模板 '{name}'")
            created_count += 1

        db.session.commit()
        print(f"[WorkflowTemplateService] 初始化完成：创建 {created_count} 个，跳过 {skipped_count} 个")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"[WorkflowTemplateService] 初始化系统模板失败：{str(e)}")
        return False
