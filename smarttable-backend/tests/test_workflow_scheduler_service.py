"""
WorkflowSchedulerService 单元测试
测试 APScheduler 调度生命周期、任务注册/移除/幂等更新与回调触发。
"""
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Base,
    Table,
    Workflow,
    WorkflowStatus,
    WorkflowTriggerType,
    WorkflowInstance,
    WorkflowInstanceStatus,
)
from app.models.workflow import WorkflowNode, WorkflowTrigger
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def scheduler_app():
    """为每个调度器测试创建独立应用实例"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def ctx(scheduler_app):
    """每次测试提供应用上下文"""
    with scheduler_app.app_context():
        yield


@pytest.fixture(scope='function')
def owner(ctx):
    user = User(email='owner@example.com', name='所有者')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user


@pytest.fixture(scope='function')
def base(ctx, owner):
    b = Base(name='测试 Base', owner_id=owner.id)
    db.session.add(b)
    db.session.commit()
    db.session.refresh(b)
    return b


@pytest.fixture(scope='function')
def table(ctx, base):
    t = Table(base_id=base.id, name='测试表格', order=0)
    db.session.add(t)
    db.session.commit()
    db.session.refresh(t)
    return t


@pytest.fixture(scope='function', autouse=True)
def stop_scheduler_after_test():
    """每个测试结束后停止调度器，避免后台线程泄漏"""
    yield
    from app.services import workflow_scheduler_service

    workflow_scheduler_service.stop_scheduler()


def _future_schedule(repeat_type='no_repeat', extra=None):
    """构造一个未来的合法定时配置"""
    future = datetime.now(timezone.utc) + timedelta(days=1)
    schedule = {
        'start_date': future.strftime('%Y-%m-%d'),
        'start_time': future.strftime('%H:%M'),
        'repeat_type': repeat_type,
        'end_type': 'never',
    }
    if repeat_type == 'custom':
        schedule['custom_interval'] = 1
        schedule['custom_unit'] = 'day'
    if extra:
        schedule.update(extra)
    return schedule


def _create_specified_time_workflow(
    base, table, owner, status=WorkflowStatus.ACTIVE, schedule=None
):
    """辅助函数：创建一个指定时间触发工作流"""
    workflow = WorkflowService.create_workflow(
        base_id=base.id,
        table_id=table.id,
        name='定时测试工作流',
        created_by=owner.id,
        trigger_config={
            'trigger_type': 'specified_time',
            'filter_config': {'schedule': schedule or _future_schedule()},
        },
        nodes_config=[
            {'node_type': 'trigger', 'name': '触发', 'config': {}, 'order': 0}
        ],
    )
    if status != WorkflowStatus.DRAFT:
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
    if status == WorkflowStatus.PAUSED:
        WorkflowService.pause_workflow(workflow.id, user_id=owner.id)
    if status == WorkflowStatus.ARCHIVED:
        WorkflowService.archive_workflow(workflow.id, user_id=owner.id)
    return workflow


class TestAppLifecycle:
    """测试应用生命周期中调度器的启动与停止"""

    def test_init_services_starts_scheduler_on_first_request(self, scheduler_app):
        """首次请求时应启动调度器、加载任务并注册退出停止"""
        with patch(
            'app.services.workflow_scheduler_service.start_scheduler'
        ) as mock_start, patch(
            'app.services.workflow_scheduler_service.reschedule_all'
        ) as mock_reschedule, patch(
            'app.services.workflow_scheduler_service.stop_scheduler'
        ) as mock_stop, patch(
            'atexit.register'
        ) as mock_atexit:
            with scheduler_app.test_client() as client:
                response = client.get('/api/health')

        assert response.status_code == 200
        mock_start.assert_called_once_with(scheduler_app)
        mock_reschedule.assert_called_once_with(scheduler_app)
        # atexit.register 还会注册 WebhookService.stop_retry_scheduler，因此至少注册一次 stop_scheduler
        registered_callees = [call.args[0] for call in mock_atexit.call_args_list]
        assert mock_stop in registered_callees


class TestSchedulerLifecycle:
    """测试调度器生命周期"""

    def test_start_scheduler_creates_running_background_scheduler(self, scheduler_app):
        """start_scheduler 应创建并启动 BackgroundScheduler"""
        from app.services import workflow_scheduler_service

        workflow_scheduler_service.start_scheduler(scheduler_app)
        assert workflow_scheduler_service.scheduler is not None
        assert isinstance(workflow_scheduler_service.scheduler, BackgroundScheduler)
        assert workflow_scheduler_service.scheduler.running is True

    def test_stop_scheduler_shuts_down_running_scheduler(self, scheduler_app):
        """stop_scheduler 应关闭运行中的调度器"""
        from app.services import workflow_scheduler_service

        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.stop_scheduler()
        assert workflow_scheduler_service.scheduler is None

    def test_stop_scheduler_is_safe_when_not_started(self):
        """未启动时调用 stop_scheduler 不应抛异常"""
        from app.services import workflow_scheduler_service

        workflow_scheduler_service.scheduler = None
        workflow_scheduler_service.stop_scheduler()
        assert workflow_scheduler_service.scheduler is None


class TestScheduleWorkflow:
    """测试为工作流注册调度任务"""

    def test_schedule_workflow_creates_job_for_active_specified_time(
        self, ctx, scheduler_app, base, table, owner
    ):
        """active 且 specified_time 工作流应被加入调度器"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        workflow_scheduler_service.start_scheduler(scheduler_app)

        result = workflow_scheduler_service.schedule_workflow(workflow.id)
        assert result is True

        job_id = f'workflow-schedule-{workflow.id}'
        job = workflow_scheduler_service.scheduler.get_job(job_id)
        assert job is not None
        assert job.func == workflow_scheduler_service._trigger_workflow

    def test_schedule_workflow_skips_non_active(self, ctx, scheduler_app, base, table, owner):
        """非 active 状态工作流不应被调度"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, status=WorkflowStatus.DRAFT
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)

        result = workflow_scheduler_service.schedule_workflow(workflow.id)
        assert result is False
        job_id = f'workflow-schedule-{workflow.id}'
        assert workflow_scheduler_service.scheduler.get_job(job_id) is None

    def test_schedule_workflow_skips_non_specified_time(
        self, ctx, scheduler_app, base, table, owner
    ):
        """非 specified_time 触发类型不应被调度"""
        from app.services import workflow_scheduler_service

        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='事件触发工作流',
            created_by=owner.id,
            trigger_config={
                'trigger_type': 'record_created',
                'filter_config': {},
            },
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'config': {}, 'order': 0}
            ],
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
        workflow_scheduler_service.start_scheduler(scheduler_app)

        result = workflow_scheduler_service.schedule_workflow(workflow.id)
        assert result is False

    def test_schedule_workflow_is_idempotent(self, ctx, scheduler_app, base, table, owner):
        """重复调度同一工作流应幂等更新任务"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        workflow_scheduler_service.start_scheduler(scheduler_app)

        workflow_scheduler_service.schedule_workflow(workflow.id)
        first_job = workflow_scheduler_service.scheduler.get_job(
            f'workflow-schedule-{workflow.id}'
        )

        workflow_scheduler_service.schedule_workflow(workflow.id)
        second_job = workflow_scheduler_service.scheduler.get_job(
            f'workflow-schedule-{workflow.id}'
        )

        assert second_job is not None
        assert second_job.id == first_job.id

    def test_schedule_workflow_no_repeat_uses_date_trigger(
        self, ctx, scheduler_app, base, table, owner
    ):
        """no_repeat 应使用 DateTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, schedule=_future_schedule('no_repeat')
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, DateTrigger)

    def test_schedule_workflow_daily_uses_cron_trigger(
        self, ctx, scheduler_app, base, table, owner
    ):
        """daily 应使用 CronTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, schedule=_future_schedule('daily')
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)

    def test_schedule_workflow_weekly_uses_cron_trigger_with_weekday(
        self, ctx, scheduler_app, base, table, owner
    ):
        """weekly 应使用按开始日期星期几触发的 CronTrigger"""
        from app.services import workflow_scheduler_service

        future = datetime.now(timezone.utc) + timedelta(days=10)
        workflow = _create_specified_time_workflow(
            base,
            table,
            owner,
            schedule=_future_schedule(
                'weekly', {'start_date': future.strftime('%Y-%m-%d')}
            ),
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)

    def test_schedule_workflow_monthly_uses_cron_trigger_with_day(
        self, ctx, scheduler_app, base, table, owner
    ):
        """monthly 应使用按开始日期日号触发的 CronTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, schedule=_future_schedule('monthly')
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)

    def test_schedule_workflow_yearly_uses_cron_trigger_with_month_day(
        self, ctx, scheduler_app, base, table, owner
    ):
        """yearly 应使用按开始日期月/日触发的 CronTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, schedule=_future_schedule('yearly')
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)

    def test_schedule_workflow_weekdays_uses_cron_trigger_mon_fri(
        self, ctx, scheduler_app, base, table, owner
    ):
        """weekdays 应使用周一至周五的 CronTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base, table, owner, schedule=_future_schedule('weekdays')
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)

    def test_schedule_workflow_custom_uses_interval_trigger(
        self, ctx, scheduler_app, base, table, owner
    ):
        """custom 应使用 IntervalTrigger"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(
            base,
            table,
            owner,
            schedule=_future_schedule('custom', {'custom_interval': 2, 'custom_unit': 'week'}),
        )
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, IntervalTrigger)

    def test_schedule_workflow_passes_end_date_to_trigger(
        self, ctx, scheduler_app, base, table, owner
    ):
        """end_type=end_date 时应将 end_date 传给 CronTrigger"""
        from app.services import workflow_scheduler_service

        future = datetime.now(timezone.utc) + timedelta(days=1)
        end = future + timedelta(days=7)
        schedule = {
            'start_date': future.strftime('%Y-%m-%d'),
            'start_time': future.strftime('%H:%M'),
            'repeat_type': 'daily',
            'end_type': 'end_date',
            'end_date': end.strftime('%Y-%m-%d'),
        }
        workflow = _create_specified_time_workflow(base, table, owner, schedule=schedule)
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job = workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow.id}')
        assert isinstance(job.trigger, CronTrigger)
        assert job.trigger.end_date is not None


class TestUnscheduleWorkflow:
    """测试移除调度任务"""

    def test_unschedule_workflow_removes_existing_job(
        self, ctx, scheduler_app, base, table, owner
    ):
        """unschedule_workflow 应移除已存在的任务"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.schedule_workflow(workflow.id)

        job_id = f'workflow-schedule-{workflow.id}'
        assert workflow_scheduler_service.scheduler.get_job(job_id) is not None

        workflow_scheduler_service.unschedule_workflow(workflow.id)
        assert workflow_scheduler_service.scheduler.get_job(job_id) is None

    def test_unschedule_workflow_silent_when_job_missing(self, scheduler_app):
        """任务不存在时 unschedule_workflow 应静默通过"""
        from app.services import workflow_scheduler_service

        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.unschedule_workflow(uuid.uuid4())


class TestRescheduleAll:
    """测试启动后重新注册所有任务"""

    def test_reschedule_all_registers_active_specified_time_workflows(
        self, ctx, scheduler_app, base, table, owner
    ):
        """reschedule_all 应扫描并注册所有 active 的 specified_time 工作流"""
        from app.services import workflow_scheduler_service

        wf1 = _create_specified_time_workflow(base, table, owner)
        wf2 = _create_specified_time_workflow(base, table, owner)
        # 非 active
        _create_specified_time_workflow(base, table, owner, status=WorkflowStatus.PAUSED)
        # 非 specified_time
        workflow_event = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='事件触发',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'config': {}, 'order': 0}
            ],
        )
        WorkflowService.publish_workflow(workflow_event.id, created_by=owner.id)

        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service.reschedule_all(scheduler_app)

        assert workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{wf1.id}') is not None
        assert workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{wf2.id}') is not None
        assert (
            workflow_scheduler_service.scheduler.get_job(f'workflow-schedule-{workflow_event.id}')
            is None
        )


class TestTriggerWorkflowCallback:
    """测试调度任务回调"""

    def test_trigger_workflow_creates_instance_and_submits_run(
        self, ctx, scheduler_app, base, table, owner
    ):
        """_trigger_workflow 应创建实例并提交到执行器"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()
        mock_engine = MagicMock()
        mock_engine.start_instance.return_value = mock_instance

        with patch(
            'app.services.workflow_execution_engine.workflow_execution_engine', mock_engine
        ):
            workflow_scheduler_service.start_scheduler(scheduler_app)
            workflow_scheduler_service._trigger_workflow(str(workflow.id))

        mock_engine.start_instance.assert_called_once()
        call_args = mock_engine.start_instance.call_args
        assert call_args[0][0].id == workflow.id
        event = call_args[0][1]
        assert event.event_type == 'specified_time'
        assert event.table_id == str(table.id)
        assert event.record_id is None
        assert event.actor_id is None
        assert event.metadata.get('workflow_id') == str(workflow.id)

        mock_engine.executor.submit.assert_called_once()
        submit_args = mock_engine.executor.submit.call_args[0]
        assert submit_args[0] == mock_engine._run_instance
        assert str(submit_args[1]) == str(mock_instance.id)

    def test_trigger_workflow_skips_inactive_workflow(
        self, ctx, scheduler_app, base, table, owner
    ):
        """工作流非 active 时回调直接返回"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        WorkflowService.pause_workflow(workflow.id, user_id=owner.id)
        mock_engine = MagicMock()

        with patch(
            'app.services.workflow_execution_engine.workflow_execution_engine', mock_engine
        ):
            workflow_scheduler_service.start_scheduler(scheduler_app)
            workflow_scheduler_service._trigger_workflow(str(workflow.id))

        mock_engine.start_instance.assert_not_called()

    def test_trigger_workflow_skips_wrong_trigger_type(
        self, ctx, scheduler_app, base, table, owner
    ):
        """触发类型不是 specified_time 时回调直接返回"""
        from app.services import workflow_scheduler_service

        workflow = WorkflowService.create_workflow(
            base_id=base.id,
            table_id=table.id,
            name='事件触发',
            created_by=owner.id,
            trigger_config={'trigger_type': 'record_created', 'filter_config': {}},
            nodes_config=[
                {'node_type': 'trigger', 'name': '触发', 'config': {}, 'order': 0}
            ],
        )
        WorkflowService.publish_workflow(workflow.id, created_by=owner.id)
        mock_engine = MagicMock()

        with patch(
            'app.services.workflow_execution_engine.workflow_execution_engine', mock_engine
        ):
            workflow_scheduler_service.start_scheduler(scheduler_app)
            workflow_scheduler_service._trigger_workflow(str(workflow.id))

        mock_engine.start_instance.assert_not_called()

    def test_trigger_workflow_uses_app_context(self, ctx, scheduler_app, base, table, owner):
        """_trigger_workflow 应在 Flask app 上下文中执行"""
        from app.services import workflow_scheduler_service

        workflow = _create_specified_time_workflow(base, table, owner)
        mock_engine = MagicMock()
        mock_engine.start_instance.return_value = None

        with patch(
            'app.services.workflow_execution_engine.workflow_execution_engine', mock_engine
        ):
            workflow_scheduler_service.start_scheduler(scheduler_app)
            workflow_scheduler_service._trigger_workflow(str(workflow.id))

        mock_engine.start_instance.assert_called_once()


class TestTriggerWorkflowRealEngine:
    """测试调度回调与真实执行引擎集成的无记录触发路径"""

    def test_trigger_workflow_runs_instance_without_record(
        self, ctx, scheduler_app, base, table, owner
    ):
        """_trigger_workflow 应创建无记录实例并异步执行完成"""
        from app.services import workflow_scheduler_service
        from app.services.workflow_execution_engine import workflow_execution_engine

        workflow = _create_specified_time_workflow(base, table, owner)
        workflow_scheduler_service.start_scheduler(scheduler_app)
        workflow_scheduler_service._trigger_workflow(str(workflow.id))

        instance = WorkflowInstance.query.filter_by(workflow_id=workflow.id).first()
        assert instance is not None
        assert instance.trigger_type == 'specified_time'
        assert instance.trigger_record_id is None

        # 等待后台执行完成
        for _ in range(100):
            db.session.refresh(instance)
            if instance.status != WorkflowInstanceStatus.RUNNING:
                break
            time.sleep(0.05)

        assert instance.status == WorkflowInstanceStatus.COMPLETED
