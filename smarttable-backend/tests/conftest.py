"""
Pytest 配置文件
"""
import pytest
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Base, Table, Field, Record, View


@pytest.fixture(scope='session')
def app():
    """创建测试应用实例"""
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """创建测试CLI运行器"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """创建数据库会话"""
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()


@pytest.fixture(scope='function')
def test_user(app, db_session):
    """创建测试用户"""
    with app.app_context():
        user = User(
            email='test@example.com',
            name='测试用户'
        )
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture(scope='function')
def auth_headers(client, test_user):
    """获取认证头"""
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'Test1234!'
    })
    if response.status_code == 200:
        data = response.get_json()
        tokens = data.get('data', {}).get('tokens', {})
        access_token = tokens.get('access_token', data.get('data', {}).get('access_token'))
        if access_token:
            return {'Authorization': f'Bearer {access_token}'}
    return {}


@pytest.fixture(scope='function')
def test_base(app, db_session, test_user):
    """创建测试Base"""
    with app.app_context():
        base = Base(
            name='测试多维表格',
            description='这是一个测试多维表格',
            icon='table',
            color='#6366f1',
            owner_id=test_user.id
        )
        db.session.add(base)
        db.session.commit()
        db.session.refresh(base)
        return base


@pytest.fixture(scope='function')
def test_table(app, db_session, test_base):
    """创建测试表格"""
    with app.app_context():
        table = Table(
            base_id=test_base.id,
            name='测试表格',
            description='这是一个测试表格',
            order=0
        )
        db.session.add(table)
        db.session.commit()
        db.session.refresh(table)
        return table


@pytest.fixture(scope='function')
def test_field(app, db_session, test_table):
    """创建测试字段"""
    from app.models.field import FieldType
    with app.app_context():
        field = Field(
            table_id=test_table.id,
            name='名称',
            type=FieldType.SINGLE_LINE_TEXT.value,
            order=0,
            is_required=True
        )
        db.session.add(field)
        db.session.commit()
        db.session.refresh(field)
        return field


@pytest.fixture(scope='function')
def test_record(app, db_session, test_table, test_field, test_user):
    """创建测试记录"""
    with app.app_context():
        record = Record(
            table_id=test_table.id,
            values={str(test_field.id): '测试值'},
            created_by=test_user.id,
            updated_by=test_user.id
        )
        db.session.add(record)
        db.session.commit()
        db.session.refresh(record)
        return record


@pytest.fixture(scope='function')
def test_view(app, db_session, test_table):
    """创建测试视图"""
    from app.models.view import ViewType
    with app.app_context():
        view = View(
            table_id=test_table.id,
            name='默认视图',
            type=ViewType.TABLE.value,
            order=0,
            is_default=True
        )
        db.session.add(view)
        db.session.commit()
        db.session.refresh(view)
        return view
