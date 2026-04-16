"""
SmartTable Flask 应用入口文件
用于启动开发服务器
"""
import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()

config_name = os.environ.get('FLASK_ENV', 'development')


def parse_args():
    parser = argparse.ArgumentParser(description='SmartTable Server')
    parser.add_argument('--enable-realtime', '-r', action='store_true',
                        default=os.environ.get('ENABLE_REALTIME', '').lower() == 'true',
                        help='Enable real-time collaboration via SocketIO')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('init-db', help='Initialize database tables')

    create_admin_parser = subparsers.add_parser('create-admin', help='Create admin user')
    create_admin_parser.add_argument('email', help='Admin email')
    create_admin_parser.add_argument('password', help='Admin password')
    create_admin_parser.add_argument('name', help='Admin name')

    subparsers.add_parser('shell', help='Start interactive shell')

    args, _ = parser.parse_known_args()
    return args


args = parse_args()
enable_realtime = args.enable_realtime

from app import create_app
app = create_app(config_name, enable_realtime=enable_realtime)


def init_db():
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
    with app.app_context():
        from app.extensions import db
        from app.models.user import User, UserRole, UserStatus

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f'User with email {email} already exists!')
            return

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
    with app.app_context():
        from app.extensions import db
        from app.models import (
            User, Base, BaseMember, Table, Field,
            Record, View, Dashboard, Attachment
        )

        import code

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

        code.interact(local=context)


if __name__ == '__main__':
    if args.command == 'init-db':
        init_db()
        sys.exit(0)
    elif args.command == 'create-admin':
        create_admin(args.email, args.password, args.name)
        sys.exit(0)
    elif args.command == 'shell':
        shell()
        sys.exit(0)

    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f'Starting SmartTable server...')
    print(f'Environment: {config_name}')
    print(f'Host: {host}')
    print(f'Port: {port}')
    print(f'Debug: {debug}')
    print(f'Real-time collaboration: {"enabled" if enable_realtime else "disabled"}')
    print(f'API Documentation: http://{host}:{port}/api/')

    if enable_realtime:
        from app.extensions import socketio
        socketio.run(app, host=host, port=port, debug=debug)
    else:
        app.run(host=host, port=port, debug=debug)
