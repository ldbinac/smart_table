"""
工作流记录时间扫描器模块

周期性扫描 active 状态的 record_time_reached 工作流，
查询到达触发时间的记录并逐条启动工作流实例。
仅支持一次性触发：通过 workflow_record_time_triggers 表追踪已触发记录。
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

log = logging.getLogger(__name__)

# 全局 Flask 应用引用
_app = None

# 扫描间隔（秒）
SCAN_INTERVAL_SECONDS = 60

# 任务 ID
_SCANNER_JOB_ID = 'workflow-record-time-scanner'

# 最近一次扫描统计（供监控使用）
_last_scan_stats = {
    'last_scan_at': None,
    'last_scan_utc': None,
    'scanned_workflows': 0,
    'triggered_instances': 0,
    'errors': 0,
    'last_error': None,
}


def get_scan_stats() -> dict:
    """返回最近一次扫描的统计信息，供监控端点使用"""
    return dict(_last_scan_stats)


def _record_scan_stats(scanned: int, triggered: int, errors: int, error_msg: Optional[str] = None) -> None:
    """更新扫描统计"""
    now_local = datetime.now().astimezone()
    now_utc = datetime.now(timezone.utc)
    _last_scan_stats.update({
        'last_scan_at': now_local.isoformat(),
        'last_scan_utc': now_utc.isoformat(),
        'scanned_workflows': scanned,
        'triggered_instances': triggered,
        'errors': errors,
        'last_error': error_msg,
    })


def _get_local_timezone():
    """获取系统本地时区"""
    return datetime.now().astimezone().tzinfo


def start_scanner(app) -> None:
    """
    注册周期扫描任务到 APScheduler。

    复用 WorkflowSchedulerService 的 BackgroundScheduler 实例。

    Args:
        app: Flask 应用实例
    """
    global _app
    _app = app

    from app.services.workflow_scheduler_service import scheduler

    if scheduler is None:
        log.warning('[WorkflowRecordTimeScanner] 调度器未启动，无法注册扫描任务')
        return

    try:
        scheduler.remove_job(_SCANNER_JOB_ID)
    except Exception:
        pass

    scheduler.add_job(
        _scan_all_job,
        trigger='interval',
        seconds=SCAN_INTERVAL_SECONDS,
        id=_SCANNER_JOB_ID,
        replace_existing=True,
    )
    log.info(f'[WorkflowRecordTimeScanner] 已注册周期扫描任务，间隔 {SCAN_INTERVAL_SECONDS} 秒')


def stop_scanner() -> None:
    """移除周期扫描任务"""
    from app.services.workflow_scheduler_service import scheduler

    if scheduler is None:
        return

    try:
        scheduler.remove_job(_SCANNER_JOB_ID)
        log.info('[WorkflowRecordTimeScanner] 已移除周期扫描任务')
    except Exception:
        pass


def _scan_all_job() -> None:
    """APScheduler 任务回调：在 Flask 应用上下文中执行扫描"""
    if _app is None:
        log.error('[WorkflowRecordTimeScanner] 缺少 Flask 应用上下文')
        return

    with _app.app_context():
        try:
            scan_all()
        except Exception as e:
            log.exception(f'[WorkflowRecordTimeScanner] 扫描执行失败: {e}')


def scan_all() -> int:
    """
    扫描所有 active 的 record_time_reached 工作流，逐个调用 scan_workflow。

    Returns:
        触发的工作流实例数量
    """
    from app.models.workflow import Workflow, WorkflowTrigger, WorkflowStatus, WorkflowTriggerType

    triggers = (
        WorkflowTrigger.query.join(Workflow)
        .filter(
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.is_deleted == False,
            WorkflowTrigger.trigger_type == WorkflowTriggerType.RECORD_TIME_REACHED,
        )
        .all()
    )

    total_triggered = 0
    errors = 0
    last_error = None
    for trigger in triggers:
        try:
            count = scan_workflow(trigger)
            total_triggered += count
        except Exception as e:
            errors += 1
            last_error = str(e)
            log.exception(
                f'[WorkflowRecordTimeScanner] scan_workflow 失败 '
                f'(workflow={trigger.workflow_id}, trigger={trigger.id}): {e}'
            )

    _record_scan_stats(
        scanned=len(triggers),
        triggered=total_triggered,
        errors=errors,
        error_msg=last_error,
    )

    if total_triggered > 0:
        log.info(f'[WorkflowRecordTimeScanner] scan_all 完成，扫描 {len(triggers)} 个工作流，触发 {total_triggered} 个实例')
    return total_triggered


def scan_workflow(trigger) -> int:
    """
    扫描单个工作流的到期记录并触发实例。

    匹配语义：
    - 日期字段：记录日期 <= 本地今天（即日期已到达）
    - 日期时间字段：记录时间 <= 当前 UTC 时间（即时间已到达）
    一次性触发保证：通过 WorkflowRecordTimeTrigger 追踪表 + UNIQUE 约束防止重复。

    Args:
        trigger: WorkflowTrigger 对象，触发类型为 record_time_reached

    Returns:
        触发的实例数量
    """
    from app.models.field import Field, FieldType
    from app.models.record import Record
    from app.models.workflow import Workflow, WorkflowStatus
    from app.models.workflow_record_time_trigger import WorkflowRecordTimeTrigger
    from app.services.workflow_event_bus import WorkflowEvent
    from app.services.workflow_execution_engine import workflow_execution_engine
    from app.extensions import db

    workflow = trigger.workflow
    if not workflow:
        return 0

    # 兼容 SQLite（status 可能是字符串）和 PostgreSQL（status 是枚举）
    status_value = workflow.status.value if isinstance(workflow.status, WorkflowStatus) else workflow.status
    if status_value != WorkflowStatus.ACTIVE.value or workflow.is_deleted:
        return 0

    filter_config = trigger.filter_config or {}
    time_field_id = filter_config.get('time_field_id')
    if not time_field_id:
        log.warning(f'[WorkflowRecordTimeScanner] 触发器缺少 time_field_id: {trigger.id}')
        return 0

    # 查询时间字段，确认类型
    field = Field.query.filter_by(id=time_field_id, table_id=workflow.table_id).first()
    if not field:
        log.warning(f'[WorkflowRecordTimeScanner] 时间字段不存在: {time_field_id}')
        return 0

    field_type = field.type.value if isinstance(field.type, FieldType) else field.type
    is_date_only = field_type == FieldType.DATE.value
    is_date_time = field_type == FieldType.DATE_TIME.value
    if not is_date_only and not is_date_time:
        log.warning(f'[WorkflowRecordTimeScanner] 时间字段类型不是日期/日期时间: {field.type}')
        return 0

    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now(_get_local_timezone())
    today_local = now_local.date()

    # 查询该表格下所有未删除记录
    records = Record.query.filter_by(
        table_id=workflow.table_id,
        is_deleted=False
    ).all()

    # 筛选到达触发时间的记录
    # - 日期字段：记录日期 <= 本地今天（日期已到达）
    # - 日期时间字段：记录时间 <= 当前 UTC 时间（时间已到达）
    # 追踪表保证一次性触发，不会重复
    matching_records = []
    for record in records:
        field_value = (record.values or {}).get(str(time_field_id))
        if field_value is None:
            continue

        try:
            if is_date_only:
                record_date = _parse_date(field_value)
                if record_date and record_date <= today_local:
                    matching_records.append(record)
            elif is_date_time:
                record_dt = _parse_datetime(field_value)
                if record_dt and record_dt <= now_utc:
                    matching_records.append(record)
        except (ValueError, TypeError) as e:
            log.debug(f'[WorkflowRecordTimeScanner] 解析时间值失败: {field_value} - {e}')
            continue

    if not matching_records:
        return 0

    # 排除已触发记录
    triggered_ids = set()
    existing_triggers = WorkflowRecordTimeTrigger.query.filter_by(
        workflow_id=workflow.id,
        field_id=time_field_id,
    ).all()
    for et in existing_triggers:
        triggered_ids.add(str(et.record_id))

    new_records = [r for r in matching_records if str(r.id) not in triggered_ids]
    if not new_records:
        return 0

    # 应用触发过滤条件
    conditions = filter_config.get('conditions', [])
    conjunction = filter_config.get('conjunction', 'and')
    if conditions:
        from app.services.workflow_execution_engine import WorkflowExecutionEngine
        condition_config = {'conditions': conditions, 'conjunction': conjunction}
        filtered_records = []
        for record in new_records:
            context = {fid: record.values.get(fid) for fid in (record.values or {})}
            if WorkflowExecutionEngine.evaluate_condition(condition_config, context):
                filtered_records.append(record)
        new_records = filtered_records

    if not new_records:
        return 0

    # 为每条匹配记录：写入追踪 + 触发实例
    # 关键：先提交追踪记录，再启动实例，确保追踪记录独立提交，
    # 避免实例启动失败导致追踪回滚（从而引发重复触发）
    triggered_count = 0
    for record in new_records:
        try:
            # 写入追踪记录（利用 UNIQUE 约束防止并发重复）
            tracking = WorkflowRecordTimeTrigger(
                workflow_id=workflow.id,
                record_id=record.id,
                field_id=uuid.UUID(str(time_field_id)),
                triggered_at=now_utc,
            )
            db.session.add(tracking)
            db.session.commit()  # 独立提交追踪记录，确保一次性触发语义
        except Exception as e:
            # UNIQUE 约束冲突说明已被其他进程触发，跳过
            if 'uq_wf_rec_time_trigger' in str(e) or 'UniqueViolation' in str(e.__class__.__name__) or 'unique' in str(e).lower():
                log.debug(f'[WorkflowRecordTimeScanner] 记录已被触发，跳过: {record.id}')
                db.session.rollback()
                continue
            log.exception(f'[WorkflowRecordTimeScanner] 写入追踪记录失败: {record.id} - {e}')
            db.session.rollback()
            continue

        # 追踪记录已提交，现在启动实例
        # 如果实例启动失败，追踪记录已防止重复触发（符合一次性语义）
        try:
            event = WorkflowEvent(
                event_type='record_time_reached',
                table_id=str(workflow.table_id),
                record_id=str(record.id),
                actor_id=None,
                metadata={
                    'workflow_id': str(workflow.id),
                    'time_field_id': str(time_field_id),
                },
            )

            instance = workflow_execution_engine.start_instance(workflow, event)
            if instance:
                try:
                    workflow_execution_engine.executor.submit(
                        workflow_execution_engine._run_instance, str(instance.id)
                    )
                except Exception as submit_err:
                    # 实例已创建但提交执行失败，记录错误但不回滚追踪
                    log.exception(
                        f'[WorkflowRecordTimeScanner] 实例提交执行失败: {instance.id} - {submit_err}'
                    )
                triggered_count += 1
                log.info(
                    f'[WorkflowRecordTimeScanner] 触发工作流实例: {instance.id} '
                    f'(workflow={workflow.id}, record={record.id})'
                )
        except Exception as e:
            log.exception(
                f'[WorkflowRecordTimeScanner] 启动实例失败 (tracking 已提交，不会重复触发): '
                f'record={record.id} - {e}'
            )

    return triggered_count


def _parse_date(value) -> Optional[object]:
    """
    解析日期值，返回 date 对象。
    支持格式：YYYY-MM-DD、ISO 8601 日期时间（取日期部分）。
    """
    from datetime import date

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    s = str(value).strip()
    if not s:
        return None

    # 尝试解析 ISO 8601 日期时间，取日期部分
    try:
        dt = datetime.fromisoformat(s)
        return dt.date()
    except (ValueError, TypeError):
        pass

    # 尝试解析纯日期
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        pass

    # 尝试常见格式
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue

    return None


def _parse_datetime(value) -> Optional[datetime]:
    """
    解析日期时间值，返回带时区的 datetime 对象。
    支持格式：ISO 8601、常见日期时间格式。
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    s = str(value).strip()
    if not s:
        return None

    # 尝试解析 ISO 8601
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass

    # 尝试常见格式
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

    return None
