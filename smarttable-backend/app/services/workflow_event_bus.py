"""
工作流事件总线模块

提供工作流事件的发布与订阅机制，用于解耦记录/字段变更与工作流执行。
当前阶段仅实现事件发布与本地处理器调用，不阻塞用户请求。
"""
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


log = logging.getLogger(__name__)


@dataclass
class WorkflowEvent:
    """
    工作流事件数据类

    属性:
        event_type: 事件类型（record_created / record_updated / record_deleted / field_changed）
        table_id: 表格 ID
        record_id: 记录 ID（可选）
        changes: 变更内容（可选），例如 {'field_id': {'old_value': ..., 'new_value': ...}}
        actor_id: 操作者 ID（可选）
        timestamp: 事件发生时间
        metadata: 额外元数据（可选）
    """

    event_type: str
    table_id: str
    record_id: Optional[str] = None
    changes: Optional[Dict[str, Any]] = None
    actor_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'table_id': self.table_id,
            'record_id': self.record_id,
            'changes': self.changes,
            'actor_id': self.actor_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class WorkflowEventBus:
    """
    工作流事件总线（单例）

    负责接收并分发工作流相关事件。当前阶段无消费者，仅记录日志；
    后续可通过 subscribe 注册异步消费者，事件将在后台线程中分发，
    避免阻塞用户请求。
    """

    _instance: Optional['WorkflowEventBus'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'WorkflowEventBus':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._handlers: List[Callable[[WorkflowEvent], None]] = []
            self._async_mode: bool = True
            self._initialized = True

    def subscribe(self, handler: Callable[[WorkflowEvent], None]) -> None:
        """
        订阅事件

        Args:
            handler: 事件处理函数，接收一个 WorkflowEvent 参数
        """
        if handler not in self._handlers:
            self._handlers.append(handler)
            log.debug(f'[WorkflowEventBus] Handler subscribed: {handler}')

    def unsubscribe(self, handler: Callable[[WorkflowEvent], None]) -> None:
        """
        取消订阅事件

        Args:
            handler: 已注册的事件处理函数
        """
        if handler in self._handlers:
            self._handlers.remove(handler)
            log.debug(f'[WorkflowEventBus] Handler unsubscribed: {handler}')

    def publish(
        self,
        event_type: str,
        table_id: str,
        record_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowEvent:
        """
        发布工作流事件

        Args:
            event_type: 事件类型
            table_id: 表格 ID
            record_id: 记录 ID
            changes: 变更内容
            actor_id: 操作者 ID
            metadata: 额外元数据

        Returns:
            创建的 WorkflowEvent 对象
        """
        event = WorkflowEvent(
            event_type=event_type,
            table_id=table_id,
            record_id=record_id,
            changes=changes,
            actor_id=actor_id,
            metadata=metadata
        )

        log.info(f'[WorkflowEventBus] Event published: {event.to_dict()}')

        if self._handlers:
            if self._async_mode:
                threading.Thread(
                    target=self._dispatch,
                    args=(event,),
                    daemon=True,
                    name=f'workflow-event-{event.event_type}'
                ).start()
            else:
                self._dispatch(event)

        return event

    def _dispatch(self, event: WorkflowEvent) -> None:
        """
        分发事件到所有订阅者

        Args:
            event: 工作流事件
        """
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                log.exception(f'[WorkflowEventBus] Handler {handler} failed: {e}')

    def set_async_mode(self, enabled: bool) -> None:
        """
        设置是否使用异步模式分发事件

        Args:
            enabled: True 为异步（默认），False 为同步
        """
        self._async_mode = enabled

    def get_handlers(self) -> List[Callable[[WorkflowEvent], None]]:
        """
        获取当前注册的所有处理器

        Returns:
            处理器列表
        """
        return self._handlers.copy()


# 全局事件总线实例
workflow_event_bus = WorkflowEventBus()
