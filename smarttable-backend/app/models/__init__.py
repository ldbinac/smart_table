"""
模型模块初始化，导出所有模型类供外部使用
"""
from app.models.user import User, TokenBlocklist
from app.models.base import Base, BaseMember
from app.models.base_share import BaseShare, SharePermission
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.models.record_history import RecordHistory, HistoryAction
from app.models.view import View
from app.models.dashboard import Dashboard
from app.models.attachment import Attachment
from app.models.operation_history import OperationHistory, OperationType, ResourceType
from app.models.log import OperationLog, AdminActionType, EntityType
from app.models.config import SystemConfig
from app.models.link_relation import LinkRelation, LinkValue, RelationshipType
from app.models.form_share import FormShare
from app.models.form_submission import FormSubmission
from app.models.email_template import EmailTemplate
from app.models.email_log import EmailLog, EmailStatus
from app.models.collaboration_session import CollaborationSession

__all__ = [
    'User',
    'TokenBlocklist',
    'Base',
    'BaseMember',
    'BaseShare',
    'SharePermission',
    'Table',
    'Field',
    'Record',
    'RecordHistory',
    'HistoryAction',
    'View',
    'Dashboard',
    'Attachment',
    'OperationHistory',
    'OperationType',
    'ResourceType',
    'OperationLog',
    'AdminActionType',
    'EntityType',
    'SystemConfig',
    'LinkRelation',
    'LinkValue',
    'RelationshipType',
    'FormShare',
    'FormSubmission',
    'EmailTemplate',
    'EmailLog',
    'EmailStatus',
    'CollaborationSession'
]
