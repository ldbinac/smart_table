"""
WorkflowRecordTimeScanner 单元测试
测试周期扫描逻辑：时间窗口匹配、一次性触发、过滤条件、日期字段处理。
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Base,
    Table,
    Field,
    Record,
    Workflow,
    WorkflowStatus,
    WorkflowTriggerType,
)
from app.models.field import FieldType
from app.models.workflow import WorkflowTrigger
from app.models.workflow_record_time_trigger import WorkflowRecordTimeTrigger
from app.services.workflow_service import WorkflowService


@pytest.fixture(scope='function')
def scanner_app():
    """为每个扫描器测试创建独立应用实例"""
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
def ctx(scanner_app):
    """每次测试提供应用上下文"""
    with scanner_app.app_context():
        yield


def _setup_workflow_with_date_field(field_type='date_time'):
    """创建工作流+表格+日期/日期时间字段+触发器的辅助函数"""
    user = User(name='test', email='test@example.com', password_hash='x')
    db.session.add(user)
    db.session.flush()

    base = Base(name='测试基础', owner_id=user.id)
    db.session.add(base)
    db.session.flush()

    table = Table(base_id=base.id, name='测试表格', order=0)
    db.session.add(table)
    db.session.flush()

    field = Field(
        table_id=table.id,
        name='截止时间' if field_type == 'date_time' else '截止日期',
        type=field_type,
        order=0,
    )
    db.session.add(field)
    db.session.flush()

    workflow = Workflow(
        base_id=base.id,
        table_id=table.id,
        name='到期提醒',
        status=WorkflowStatus.ACTIVE,
        created_by=user.id,
    )
    db.session.add(workflow)
    db.session.flush()

    trigger = WorkflowTrigger(
        workflow_id=workflow.id,
        trigger_type=WorkflowTriggerType.RECORD_TIME_REACHED,
        filter_config={'time_field_id': str(field.id)},
        field_ids=[],
    )
    db.session.add(trigger)
    db.session.commit()

    return workflow, trigger, field, table


class TestScanWorkflow:
    """scan_workflow 核心逻辑测试"""

    def test_date_time_field_matching(self, ctx):
        """日期时间字段：记录时间已到达（<= now）应匹配"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        # 创建一条记录，时间字段值在 30 秒前（已到达）
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count >= 1

    def test_date_time_field_past_record_matches(self, ctx):
        """日期时间字段：过去时间的记录也应触发（修复后语义：时间已到达即触发）"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        # 创建一条记录，时间字段值在 2 小时前（过去时间，按新语义应触发）
        past = now - timedelta(hours=2)
        record = Record(
            table_id=table.id,
            values={str(field.id): past.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count == 1

    def test_date_time_field_future_record_not_matches(self, ctx):
        """日期时间字段：未来时间的记录不应触发"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        # 创建一条记录，时间字段值在 1 小时后（未来时间，不应触发）
        future = now + timedelta(hours=1)
        record = Record(
            table_id=table.id,
            values={str(field.id): future.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count == 0

    def test_date_field_matching(self, ctx):
        """日期字段：记录日期等于本地今天应匹配"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date')

        # 使用本地时区的今天，避免 UTC 时差导致测试在凌晨失败
        today_local = datetime.now().astimezone().date()
        record = Record(
            table_id=table.id,
            values={str(field.id): today_local.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count >= 1

    def test_date_field_future_not_matching(self, ctx):
        """日期字段：未来日期的记录不应触发"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date')

        tomorrow = (datetime.now().astimezone() + timedelta(days=1)).date()
        record = Record(
            table_id=table.id,
            values={str(field.id): tomorrow.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count == 0

    def test_one_time_trigger(self, ctx):
        """一次性触发：已触发记录不应再次触发"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.flush()

        # 写入追踪记录
        tracking = WorkflowRecordTimeTrigger(
            workflow_id=workflow.id,
            record_id=record.id,
            field_id=field.id,
            triggered_at=now,
        )
        db.session.add(tracking)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            count = scan_workflow(trigger)

        assert count == 0

    def test_soft_deleted_record_not_triggered(self, ctx):
        """软删除记录不应触发"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
            is_deleted=True,
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            count = scan_workflow(trigger)

        assert count == 0

    def test_filter_conditions_applied(self, ctx):
        """触发过滤条件应正确应用"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        # 添加一个"状态"字段用于过滤
        status_field = Field(
            table_id=table.id,
            name='状态',
            type=FieldType.SINGLE_LINE_TEXT.value,
            order=1,
        )
        db.session.add(status_field)
        db.session.flush()

        # 更新触发器，添加过滤条件
        trigger.filter_config = {
            'time_field_id': str(field.id),
            'conditions': [
                {'field_id': str(status_field.id), 'operator': 'equals', 'value': '进行中'},
            ],
            'conjunction': 'and',
        }
        db.session.commit()

        now = datetime.now(timezone.utc)

        # 记录A：满足过滤条件
        record_a = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat(), str(status_field.id): '进行中'},
        )
        # 记录B：不满足过滤条件
        record_b = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat(), str(status_field.id): '已完成'},
        )
        db.session.add_all([record_a, record_b])
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_instance = MagicMock(id=uuid.uuid4())
            mock_engine.start_instance.return_value = mock_instance
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count == 1


class TestScanWorkflowRobustness:
    """scan_workflow 健壮性测试：事务隔离、并发、监控统计"""

    def test_tracking_committed_before_instance(self, ctx):
        """追踪记录应在启动实例前独立提交，避免实例失败导致重复触发"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        # 模拟 start_instance 抛异常
        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.side_effect = RuntimeError('模拟启动失败')
            count = scan_workflow(trigger)

        # 实例启动失败，count=0
        assert count == 0

        # 关键断言：追踪记录应已提交（防止下次扫描重复触发）
        from app.models.workflow_record_time_trigger import WorkflowRecordTimeTrigger
        tracking = WorkflowRecordTimeTrigger.query.filter_by(
            workflow_id=workflow.id,
            record_id=record.id,
        ).first()
        assert tracking is not None, '追踪记录应已提交，防止重复触发'

        # 再次扫描不应重复触发
        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine2:
            mock_engine2.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine2.executor = MagicMock()
            count2 = scan_workflow(trigger)
        assert count2 == 0, '已追踪的记录不应重复触发'

    def test_executor_submit_failure_doesnt_rollback_tracking(self, ctx):
        """executor.submit 失败不应回滚已提交的追踪记录"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor.submit.side_effect = RuntimeError('线程池满')
            count = scan_workflow(trigger)

        # submit 失败但 start_instance 成功，仍计入触发数
        assert count == 1

        # 追踪记录应已提交
        from app.models.workflow_record_time_trigger import WorkflowRecordTimeTrigger
        tracking = WorkflowRecordTimeTrigger.query.filter_by(
            workflow_id=workflow.id,
            record_id=record.id,
        ).first()
        assert tracking is not None

    def test_scan_stats_recorded(self, ctx):
        """scan_all 应记录扫描统计"""
        from app.services.workflow_record_time_scanner import scan_all, get_scan_stats

        # 执行一次扫描
        scan_all()

        stats = get_scan_stats()
        assert stats['last_scan_at'] is not None
        assert stats['scanned_workflows'] == 0  # 无 active 工作流
        assert stats['triggered_instances'] == 0
        assert stats['errors'] == 0

    def test_scan_stats_with_active_workflow(self, ctx):
        """有 active 工作流时统计应正确"""
        from app.services.workflow_record_time_scanner import scan_all, get_scan_stats

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            scan_all()

        stats = get_scan_stats()
        assert stats['scanned_workflows'] == 1
        assert stats['triggered_instances'] >= 1
        assert stats['errors'] == 0

    def test_status_as_string_works(self, ctx):
        """workflow.status 为字符串时应正常工作（SQLite 兼容）"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')

        # 模拟 SQLite 返回字符串 status
        with patch.object(type(workflow), 'status', new_callable=lambda: 'active'):
            now = datetime.now(timezone.utc)
            record = Record(
                table_id=table.id,
                values={str(field.id): now.isoformat()},
            )
            db.session.add(record)
            db.session.commit()

            with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
                mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
                mock_engine.executor = MagicMock()
                count = scan_workflow(trigger)

            assert count >= 1, 'status 为字符串时应正常触发'

    def test_paused_workflow_skipped(self, ctx):
        """paused 状态的工作流不应被扫描"""
        from app.services.workflow_record_time_scanner import scan_workflow

        workflow, trigger, field, table = _setup_workflow_with_date_field('date_time')
        workflow.status = WorkflowStatus.PAUSED
        db.session.commit()

        now = datetime.now(timezone.utc)
        record = Record(
            table_id=table.id,
            values={str(field.id): now.isoformat()},
        )
        db.session.add(record)
        db.session.commit()

        with patch('app.services.workflow_execution_engine.workflow_execution_engine') as mock_engine:
            mock_engine.start_instance.return_value = MagicMock(id=uuid.uuid4())
            mock_engine.executor = MagicMock()
            count = scan_workflow(trigger)

        assert count == 0
