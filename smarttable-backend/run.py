"""
SmartTable Flask 应用入口文件
用于启动开发服务器
"""
import os
import sys

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取环境配置
config_name = os.environ.get('FLASK_ENV', 'development')

# 创建应用
from app import create_app
app = create_app(config_name)


def init_db():
    """初始化数据库"""
    with app.app_context():
        from app.extensions import db
        from app.models import (
            User, Base, BaseMember, Table, Field,
            Record, View, Dashboard, Attachment
        )
        
        print('Creating database tables...')
        db.create_all()
        print('Database tables created successfully!')


def create_admin(email: str, password: str, name: str):
    """
    创建管理员用户
    
    Args:
        email: 邮箱地址
        password: 密码
        name: 用户姓名
    """
    with app.app_context():
        from app.extensions import db
        from app.models.user import User, UserRole, UserStatus
        
        # 检查用户是否已存在
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f'User with email {email} already exists!')
            return
        
        # 创建管理员用户
        admin = User(
            email=email,
            password=password,
            name=name,
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f'Admin user created successfully!')
        print(f'Email: {email}')
        print(f'Name: {name}')


def shell():
    """启动交互式 Shell"""
    with app.app_context():
        from app.extensions import db
        from app.models import (
            User, Base, BaseMember, Table, Field,
            Record, View, Dashboard, Attachment
        )
        
        # 导入常用的模块
        import code
        
        # 设置上下文变量
        context = {
            'app': app,
            'db': db,
            'User': User,
            'Base': Base,
            'BaseMember': BaseMember,
            'Table': Table,
            'Field': Field,
            'Record': Record,
            'View': View,
            'Dashboard': Dashboard,
            'Attachment': Attachment
        }
        
        # 启动交互式 Shell
        code.interact(local=context)


if __name__ == '__main__':
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'init-db':
            init_db()
            sys.exit(0)
        
        elif command == 'create-admin':
            if len(sys.argv) < 5:
                print('Usage: python run.py create-admin <email> <password> <name>')
                sys.exit(1)
            create_admin(sys.argv[2], sys.argv[3], sys.argv[4])
            sys.exit(0)
        
        elif command == 'shell':
            shell()
            sys.exit(0)
        
        else:
            print(f'Unknown command: {command}')
            print('Available commands:')
            print('  init-db          - Initialize database tables')
            print('  create-admin     - Create admin user')
            print('  shell            - Start interactive shell')
            sys.exit(1)
    
    # 启动开发服务器
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f'Starting SmartTable server...')
    print(f'Environment: {config_name}')
    print(f'Host: {host}')
    print(f'Port: {port}')
    print(f'Debug: {debug}')
    print(f'API Documentation: http://{host}:{port}/api/')
    
    app.run(host=host, port=port, debug=debug)
