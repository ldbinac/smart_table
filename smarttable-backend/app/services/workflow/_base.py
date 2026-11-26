import html
import json
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.i18n import translate
from app.extensions import db
from app.models.webhook import WebhookConfig
from app.models.record import Record
from app.models.table import Table
from app.models.workflow import Workflow, WorkflowNode, WorkflowNodeType
from app.models.workflow_instance import (
    WorkflowInstance,
    WorkflowExecutionLog,
    WorkflowInstanceStatus,
)
from app.services.email_queue_service import email_queue
from app.services.record_service import RecordService
from app.services.workflow_event_bus import workflow_event_bus, WorkflowEvent

log = logging.getLogger(__name__)

class WorkflowExecutionEngineBase:
    """Engine 工具方法已拆分到 _core.py，这里仅保持向后兼容"""
    pass


class WorkflowServiceBase:
    """WorkflowServiceBase — 共享工具方法"""

    def _to_uuid(value: Any) -> Optional[uuid.UUID]:
        """将字符串或 UUID 对象转换为 UUID 对象"""
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))