"""
工作流调度服务模块

使用 APScheduler BackgroundScheduler 管理指定时间（specified_time）工作流的定时触发。
生命周期、调度注册/移除与回调触发均在此模块实现。
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger(__name__)

# 全局调度器与 Flask 应用引用
scheduler: BackgroundScheduler | None = None
_app = None


def start_scheduler(app):
    """
    启动后台调度器并绑定 Flask 应用上下文。

    Args:
        app: Flask 应用实例
    """
    global scheduler, _app
    stop_scheduler()
    _app = app
    scheduler = BackgroundScheduler()
    scheduler.start()
    log.info('[WorkflowSchedulerService] 后台调度器已启动')


def stop_scheduler():
    """停止并清理后台调度器"""
    global scheduler, _app
    if scheduler is not None:
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
        except Exception as e:
            log.warning(f'[WorkflowSchedulerService] 停止调度器时发生异常: {e}')
        finally:
            scheduler = None
    _app = None


def _job_id(workflow_id) -> str:
    """生成 APScheduler 任务 ID"""
    return f'workflow-schedule-{workflow_id}'


def _build_trigger(schedule: dict, start_dt: datetime):
    """根据 schedule 配置构建 APScheduler 触发器"""
    repeat_type = schedule['repeat_type']

    end_date = None
    if schedule.get('end_type') == 'end_date' and schedule.get('end_date'):
        tz = start_dt.tzinfo or ZoneInfo(str(schedule.get('timezone', 'UTC')))
        end_date = datetime.strptime(str(schedule['end_date']), '%Y-%m-%d').replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=tz
        )

    if repeat_type == 'no_repeat':
        return DateTrigger(run_date=start_dt)

    if repeat_type == 'custom':
        interval = schedule['custom_interval']
        unit = schedule['custom_unit']
        # APScheduler IntervalTrigger 仅支持 weeks/days/hours/minutes/seconds
        unit_map = {
            'day': 'days',
            'week': 'weeks',
            'month': 'days',
            'year': 'days',
        }
        kwargs = {unit_map[unit]: interval}
        if unit == 'month':
            kwargs['days'] = interval * 30
        elif unit == 'year':
            kwargs['days'] = interval * 365
        return IntervalTrigger(start_date=start_dt, end_date=end_date, **kwargs)

    cron_kwargs = {
        'hour': start_dt.hour,
        'minute': start_dt.minute,
        'second': 0,
    }

    if repeat_type == 'daily':
        pass
    elif repeat_type == 'weekly':
        cron_kwargs['day_of_week'] = start_dt.weekday()
    elif repeat_type == 'monthly':
        cron_kwargs['day'] = start_dt.day
    elif repeat_type == 'yearly':
        cron_kwargs['month'] = start_dt.month
        cron_kwargs['day'] = start_dt.day
    elif repeat_type == 'weekdays':
        cron_kwargs['day_of_week'] = 'mon-fri'
    else:
        raise ValueError(f'不支持的 repeat_type: {repeat_type}')

    if end_date:
        cron_kwargs['end_date'] = end_date

    return CronTrigger(**cron_kwargs)


def schedule_workflow(workflow_id) -> bool:
    """
    为 active 且触发类型为 specified_time 的工作流添加/更新定时任务。

    Args:
        workflow_id: 工作流 ID

    Returns:
        是否成功注册任务
    """
    from app.models.workflow import Workflow, WorkflowTrigger, WorkflowStatus, WorkflowTriggerType
    from app.services.workflow_service import WorkflowService

    if scheduler is None:
        log.warning('[WorkflowSchedulerService] 调度器未启动，无法注册任务')
        return False

    workflow = Workflow.query.filter_by(id=workflow_id, is_deleted=False).first()
    if not workflow or workflow.status != WorkflowStatus.ACTIVE:
        return False

    trigger = WorkflowTrigger.query.filter_by(workflow_id=workflow.id).first()
    if not trigger or trigger.trigger_type != WorkflowTriggerType.SPECIFIED_TIME:
        return False

    schedule = (trigger.filter_config or {}).get('schedule')
    if not schedule:
        return False

    try:
        start_dt = WorkflowService._validate_schedule_config(schedule)
    except ValueError as e:
        log.warning(f'[WorkflowSchedulerService] schedule 配置校验失败: {e}')
        return False

    trigger_obj = _build_trigger(schedule, start_dt)
    job_id = _job_id(workflow.id)

    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    scheduler.add_job(
        _trigger_workflow,
        trigger=trigger_obj,
        id=job_id,
        args=[str(workflow.id)],
        replace_existing=True,
    )
    log.info(f'[WorkflowSchedulerService] 已注册定时任务: {job_id}')
    return True


def unschedule_workflow(workflow_id) -> None:
    """
    移除工作流对应的定时任务，不存在时静默通过。

    Args:
        workflow_id: 工作流 ID
    """
    if scheduler is None:
        return

    job_id = _job_id(workflow_id)
    try:
        scheduler.remove_job(job_id)
        log.info(f'[WorkflowSchedulerService] 已移除定时任务: {job_id}')
    except Exception:
        pass


def reschedule_all(app) -> None:
    """
    应用启动后扫描所有 active 且触发类型为 specified_time 的工作流并注册任务。

    Args:
        app: Flask 应用实例
    """
    global _app
    _app = app

    from app.models.workflow import Workflow, WorkflowTrigger, WorkflowStatus, WorkflowTriggerType

    if scheduler is None:
        log.warning('[WorkflowSchedulerService] 调度器未启动，跳过 reschedule_all')
        return

    triggers = (
        WorkflowTrigger.query.join(Workflow)
        .filter(
            Workflow.status == WorkflowStatus.ACTIVE,
            Workflow.is_deleted == False,
            WorkflowTrigger.trigger_type == WorkflowTriggerType.SPECIFIED_TIME,
        )
        .all()
    )

    for trigger in triggers:
        schedule_workflow(trigger.workflow_id)

    log.info(f'[WorkflowSchedulerService] reschedule_all 完成，共注册 {len(triggers)} 个任务')


def _trigger_workflow(workflow_id: str) -> None:
    """
    调度任务回调：在 Flask 应用上下文中启动工作流实例并异步执行。

    Args:
        workflow_id: 工作流 ID 字符串
    """
    from app.models.workflow import Workflow, WorkflowTrigger, WorkflowStatus, WorkflowTriggerType
    from app.services.workflow_event_bus import WorkflowEvent
    from app.services.workflow_execution_engine import workflow_execution_engine

    if _app is None:
        log.error('[WorkflowSchedulerService] 缺少 Flask 应用上下文，无法触发工作流')
        return

    with _app.app_context():
        workflow = Workflow.query.filter_by(id=workflow_id, is_deleted=False).first()
        if not workflow or workflow.status != WorkflowStatus.ACTIVE:
            return

        trigger = WorkflowTrigger.query.filter_by(workflow_id=workflow.id).first()
        if not trigger or trigger.trigger_type != WorkflowTriggerType.SPECIFIED_TIME:
            return

        event = WorkflowEvent(
            event_type='specified_time',
            table_id=str(workflow.table_id),
            record_id=None,
            actor_id=None,
            metadata={'workflow_id': str(workflow.id)},
        )

        instance = workflow_execution_engine.start_instance(workflow, event)
        if instance:
            workflow_execution_engine.executor.submit(
                workflow_execution_engine._run_instance, str(instance.id)
            )
            log.info(
                f'[WorkflowSchedulerService] 定时触发工作流实例已提交: {instance.id} '
                f'(workflow={workflow.id})'
            )
