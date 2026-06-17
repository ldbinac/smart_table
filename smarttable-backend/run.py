"""
SmartTable Flask 应用入口文件
用于启动开发服务器或打包后的独立运行
"""
import argparse
import os
import sys
import time
import webbrowser
import threading
import code
from dotenv import load_dotenv
from pathlib import Path

# ⚠️ 必须在导入 app 模块之前加载 .env 配置文件
# 否则 config.py 读取环境变量时 DATABASE_URL 等值尚未设置
#
# 查找路径规则（由 getattr(sys, 'frozen', False) 区分打包/开发模式）：
# - 打包模式（EXE）：以 EXE 所在目录为基准
# - 开发模式：以项目根目录（run.py 的父目录的父目录）为基准
#
# 加载优先级（从高到低）：
#   1. {base_dir}/config/.env  （用户配置，最高优先级）
#   2. {base_dir}/.env         （项目根目录 / EXE 根目录）
#   3. smarttable-backend/.env  （开发环境，最低优先级）
_load_env_base = (
    Path(sys.executable).parent
    if getattr(sys, 'frozen', False)
    else Path(__file__).parent.parent
)
_load_env_result = None
_env_loaded = False
for _env_path in [
    _load_env_base / 'config' / '.env',
    _load_env_base / '.env',
    Path(__file__).parent / '.env',
]:
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
        _env_loaded = True
        _load_env_result = _env_path
        break
if not _env_loaded:
    load_dotenv()

config_name = os.environ.get('FLASK_ENV', 'development')

from app import create_app
from app.extensions import db, socketio
from app.models import (
    User, Base, BaseMember, Table, Field,
    Record, View, Dashboard, Attachment
)
from app.models.user import User as UserModel, UserRole, UserStatus
from app.static_serving import configure_static_serving
from app.redis_manager import RedisManager


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


# 当被 Eventlet WSGI Server 作为模块导入时，跳过 CLI 参数解析
# 避免外部导入时的 argparse 参数污染
_is_module_import = __name__ != '__main__'

if not _is_module_import:
    args = parse_args()
else:
    args = argparse.Namespace(enable_realtime=os.environ.get('ENABLE_REALTIME', '').lower() == 'true', command=None)

enable_realtime = args.enable_realtime

from app import create_app
app = create_app(config_name, enable_realtime=enable_realtime)

# 打包模式集成：全局 Redis 管理器实例
redis_manager = None


def initialize_packaging_mode(app_instance, realtime_enabled=False):
    """
    初始化打包模式的特殊配置

    在 PyInstaller 打包后的环境中，此函数负责：
    1. 配置前端静态文件服务（将 Vue 构建产物嵌入）
    2. 自动启动 Redis 服务（如果需要）

    Args:
        app_instance: Flask 应用实例
        realtime_enabled: 是否启用实时协作功能
    """
    global redis_manager

    # 配置前端静态文件托管（始终启用，即使 dist 不存在也会注册友好错误页面）
    configure_static_serving(app_instance)

    # 尝试自动启动 Redis（可选，失败不影响核心功能）
    if True:  # 默认总是尝试启动 Redis
        try:
            redis_port = int(os.environ.get('REDIS_PORT', 6379))
            redis_host = os.environ.get('REDIS_HOST', 'localhost')

            redis_manager = RedisManager(port=redis_port, host=redis_host)

            if redis_manager.start():
                print(f'[Packaging] ✓ Redis auto-started on {redis_host}:{redis_port}')
            else:
                print('[Packaging] ⚠️ Redis failed to start - running in degraded mode')
                print('[Packaging]   (Caching and real-time features may be limited)')
                redis_manager = None

        except Exception as e:
            print(f'[Packaging] ⚠️ Redis initialization error: {e}')
            print('[Packaging]   Continuing without Redis...')
            redis_manager = None


def init_db():
    with app.app_context():
        print('Creating database tables...')
        db.create_all()
        print('Database tables created successfully!')


def create_admin(email: str, password: str, name: str):
    with app.app_context():
        existing_user = UserModel.query.filter_by(email=email).first()
        if existing_user:
            print(f'User with email {email} already exists!')
            return

        admin = UserModel(
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


def ensure_default_admin_exists():
    """
    确保默认管理员账号存在

    如果数据库中没有 ADMIN 角色的用户，则自动创建默认管理员：
    - 账号：root
    - 邮箱：ldengbin@126.com
    - 密码：LDengBin@126.com

    并将管理员信息打印到控制台（醒目格式）
    """
    with app.app_context():
        # 检查是否已有管理员用户
        admin_count = UserModel.query.filter_by(role=UserRole.ADMIN).count()
        
        if admin_count > 0:
            print('\n' + '='*60)
            print('✅ 管理员账号检查完成')
            print(f'   数据库中已有 {admin_count} 个管理员账号')
            print('='*60 + '\n')
            return

        # 创建默认管理员
        default_admin_email = 'ldengbin@126.com'
        default_admin_password = 'LDengBin@126.com'
        default_admin_name = 'root'

        print('\n' + '='*60)
        print('⚠️  未检测到管理员账号')
        print('   正在自动创建默认管理员...')
        print('='*60)

        try:
            admin = UserModel(
                email=default_admin_email,
                password=default_admin_password,
                name=default_admin_name,
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                email_verified=True
            )

            db.session.add(admin)
            db.session.commit()

            # 醒目格式输出管理员信息
            print('\n' + '█'*60)
            print('█' + ' '*58 + '█')
            print('█' + '  ✅ 默认管理员账号已自动创建'.center(52) + '█')
            print('█' + ' '*58 + '█')
            print('█'*60)
            print(f'█  账号 (Account):  {default_admin_name:<34} █')
            print(f'█  邮箱 (Email):    {default_admin_email:<34} █')
            print(f'█  密码 (Password): {default_admin_password:<34} █')
            print('█'*60)
            print('█  ⚠️  请登录后立即修改默认密码！'.center(56) + '█')
            print('█'*60 + '\n')

        except Exception as e:
            print(f'\n❌ 自动创建管理员失败: {e}')
            print('   请手动执行: python run.py create-admin <email> <password> <name>\n')


def open_browser_after_delay(url: str, delay_seconds: float = 2.0):
    """
    在延迟后自动打开浏览器访问指定 URL
    
    Args:
        url: 要访问的 URL（如 http://localhost:5000）
        delay_seconds: 延迟秒数（等待服务启动完成）
    """
    def _open():
        time.sleep(delay_seconds)
        print(f'\n🌐 正在打开浏览器访问: {url}')
        
        try:
            # 尝试使用系统默认浏览器
            webbrowser.open(url, new=2)  # new=2 表示新标签页（如果支持）
            print(f'✅ 浏览器已启动')
        except Exception as e:
            print(f'⚠️ 自动打开浏览器失败: {e}')
            print(f'   请手动在浏览器中访问: {url}\n')
    
    # 在后台线程中执行，不阻塞主进程
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def shell():
    with app.app_context():
        context = {
            'app': app,
            'db': db,
            'User': UserModel,
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



# 确保数据目录存在
data_dir = os.environ.get('DATA_DIR', 'data')
os.makedirs(data_dir, exist_ok=True)
print(f'[Init] Data directory: {os.path.abspath(data_dir)}')

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
    
    # 检测是否为 PyInstaller 打包环境
    is_packaged = getattr(sys, 'frozen', False)
    if is_packaged:
        print(f'[Packaging] Running in packaged mode (PyInstaller)')
        print(f'Frontend URL: http://{host}:{port}/')
        # 初始化打包模式（静态文件服务 + Redis 管理）
        initialize_packaging_mode(app, realtime_enabled=enable_realtime)
    else:
        print(f'[Development] Running in development mode')
        print(f'Frontend URL: http://localhost:3000 (Vite dev server)')


    # ===== 初始化数据库表结构（确保所有表存在）=====
    print('[Init] Checking database schema...')
    try:
        init_db()
    except Exception as e:
        print(f'[Init] ⚠️ Database init warning: {e}')
        print('[Init]   (If this is a fresh install, tables will be created on first use)')

    # 确保默认管理员账号存在（自动创建）
    ensure_default_admin_exists()

    if is_packaged:
        # 自动打开浏览器访问服务地址
        host1 = os.environ.get('FLASK_HOST', 'localhost')
        if host1 == '0.0.0.0':
            host1 = 'localhost'
        service_url = f'http://{host1}:{port}'
        open_browser_after_delay(service_url, delay_seconds=2.0)

    try:
        # 检查 SocketIO 是否真正初始化成功
        # （extensions.py 中可能因异常而禁用了 REALTIME_ENABLED）
        realtime_enabled = enable_realtime and app.config.get('REALTIME_ENABLED', False)

        if realtime_enabled and hasattr(socketio, 'eio') and socketio.eio is not None:
            print(f'[Server] Starting with SocketIO real-time support...')
            socketio.run(app, host=host, port=port, debug=debug)
        else:
            if enable_realtime and not app.config.get('REALTIME_ENABLED', False):
                print('[Server] ⚠️ Real-time collaboration was disabled due to initialization error')
                print('[Server]   Running in standard mode (without WebSocket support)')
            elif enable_realtime:
                print('[Server] ⚠️ SocketIO object not properly initialized')
                print('[Server]   Running in standard mode')
            app.run(host=host, port=port, debug=debug)
    finally:
        # 确保退出时清理 Redis 进程
        if redis_manager and redis_manager.is_running():
            print('\n[Packaging] Stopping Redis...')
            redis_manager.stop()
