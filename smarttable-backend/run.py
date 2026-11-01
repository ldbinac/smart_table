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
#   0. 进程环境变量（docker run -e / 系统环境变量，始终最高——.env 文件不会覆盖已注入的变量）
#   1. {base_dir}/config/.env  （用户配置，文件中最高优先级）
#   2. {base_dir}/.env         （项目根目录 / EXE 根目录）
#   3. smarttable-backend/.env  （开发环境，最低优先级）
# 命中第一个存在的文件即停止（break），加载时 override=False：
# 仅填充尚未定义的变量，保证外部注入（如 docker run -e DATABASE_URL=...）不被文件默认值覆盖
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
        load_dotenv(_env_path, override=False)
        _env_loaded = True
        _load_env_result = _env_path
        break
if not _env_loaded:
    load_dotenv()

# 安全兜底：未显式设置 FLASK_ENV 时默认按生产环境运行，
# 避免误以 development（DEBUG 开启 + 已知回退密钥）暴露到公网。
# 本地开发请在 smarttable-backend/.env 中设置 FLASK_ENV=development
config_name = os.environ.get('FLASK_ENV', 'production')

from app import create_app
from app.extensions import db, socketio
from app.models import (
    User, Base, BaseMember, Table, Field,
    Record, View, Dashboard, Attachment
)
from app.models.user import User as UserModel, UserRole, UserStatus
from app.services.auth_service import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD
from app.static_serving import configure_static_serving
from app.redis_manager import RedisManager


def parse_args():
    parser = argparse.ArgumentParser(description='SmartTable Server')
    parser.add_argument('--enable-realtime', '-r', action='store_true',
                        default=os.environ.get('ENABLE_REALTIME', '').lower() == 'true',
                        help='Enable real-time collaboration via SocketIO')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('init-db', help='Initialize database tables')

    subparsers.add_parser('migrate', help='Run database migrations (upgrade to latest version)')

    subparsers.add_parser('ensure-admin', help='Ensure default admin exists (auto-create if missing)')

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
        # 兜底自修复：db.create_all 只创建缺失的表、不会补齐既有表缺失的可空列，
        # 因此这里也补齐一次，确保 dashboard_shares.title 等列存在。
        repair_schema_columns()


def repair_schema_columns():
    """
    数据库结构自修复（幂等，可重复执行）

    问题背景：
    旧版本通过 db.create_all() 创建数据库，未记录 alembic_version。
    这类库的 schema 可能早于引入 Alembic 迁移之前的状态，导致部分迁移脚本
    （如 20260718_0014 为 dashboard_shares 增加 title/description 字段）
    在「标记基线 -> upgrade」流程中被跳过，从而出现部分机器上
    dashboard_shares 表缺失 title 字段、删除仪表盘时因级联查询该列失败的问题。

    本函数遍历所有模型，确保模型中定义的可空列在数据库表中均存在；
    若缺失则补齐。已存在的列不会重复添加，因此对正常数据库是空操作。
    """
    from sqlalchemy import inspect as sa_inspect, text

    bind = db.engine
    dialect = bind.dialect
    preparer = dialect.identifier_preparer
    inspector = sa_inspect(bind)
    existing_tables = set(inspector.get_table_names())

    repaired = 0
    for mapper in db.Model.registry.mappers:
        model = mapper.class_
        table = getattr(model, '__table__', None)
        if table is None or table.name not in existing_tables:
            continue
        try:
            existing_cols = {c['name'] for c in inspector.get_columns(table.name)}
        except Exception as e:
            print(f'[Repair] ⚠️ 读取表 {table.name} 列信息失败，跳过: {e}')
            continue

        for col in table.columns:
            # 仅补齐缺失的「可空」列，避免对非空表添加 NOT NULL 列导致失败
            if col.name in existing_cols or not col.nullable:
                continue
            try:
                col_type = col.type.compile(dialect=dialect)
                table_name = preparer.quote(table.name)
                col_name = preparer.quote(col.name)
                sql = text(
                    f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}'
                )
                with bind.begin() as conn:
                    conn.execute(sql)
                repaired += 1
                print(f'[Repair] ✅ 已为表 {table.name} 补齐缺失列: {col.name}')
            except Exception as e:
                print(f'[Repair] ⚠️ 为表 {table.name} 补齐列 {col.name} 失败: {e}')

    if repaired:
        print(f'[Repair] 共补齐 {repaired} 个缺失列')


def _backup_database(db_path: str) -> str:
    """
    备份 SQLite 数据库文件（包括 WAL/SHM 辅助文件）。

    返回备份文件的完整路径（.db 文件）；若原库不存在则返回空字符串。
    """
    import shutil as _shutil
    from datetime import datetime as _dt
    db_file = os.path.abspath(db_path)
    if not os.path.exists(db_file):
        return ''
    timestamp = _dt.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.dirname(db_file)
    backup_name = os.path.basename(db_file) + f'.bak.{timestamp}'
    backup_path = os.path.join(backup_dir, backup_name)
    _shutil.copy2(db_file, backup_path)
    # 同时备份 WAL / SHM 辅助文件（若存在）
    for suffix in ('-wal', '-shm'):
        src = db_file + suffix
        if os.path.exists(src):
            _shutil.copy2(src, backup_path + suffix)
    return backup_path


def _capture_row_counts() -> dict:
    """
    快照看每张表的行数快照，用于迁移前后对比。

    返回 {表名: 行数} 字典；查询失败的表会被跳过（不中断）。
    """
    from sqlalchemy import text as _text
    counts = {}
    with db.engine.connect() as conn:
        tables = [r[0] for r in conn.execute(
            _text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        )]
        for t in tables:
            try:
                cnt = conn.execute(_text(f'SELECT COUNT(*) FROM "{t}"')).scalar() or 0
                counts[t] = cnt
            except Exception:
                pass
    return counts


def _print_row_count_diff(before: dict, after: dict):
    """打印迁移前后行数变化，只输出有差异的表。"""
    all_tables = sorted(set(list(before.keys()) + list(after.keys())))
    changed = []
    for t in all_tables:
        b = before.get(t, 0)
        a = after.get(t, 0)
        if b != a:
            changed.append((t, b, a))
    if not changed:
        print('[Migrate] 📊 数据完整性: 所有表行数无变化 ✅')
        return
    print(f'[Migrate] 📊 数据完整性: {len(changed)} 张表行数有变化')
    for t, b, a in changed:
        if b > 0 and a == 0:
            marker = '❌ 数据被清空!'
        elif b == 0 and a > 0:
            marker = '📈 新增数据'
        elif b > a:
            marker = f'⚠️ 数据减少 {b - a} 行'
        else:
            marker = f'📈 新增 {a - b} 行'
        print(f'  {t:35s} {b:>6d} → {a:>6d}  {marker}')


def run_migrations():
    """
    运行数据库迁移到最新版本（带自动备份 + 数据完整性校验）

    安全加固：
    1. 迁移前自动备份数据库文件（.db + WAL/SHM → .db.bak.YYYYMMDD_HHMMSS）
    2. 迁移前后对比每张表的行数，检测数据丢失
    3. 迁移失败时打印备份恢复指引，不再盲目回退到 init_db()

    支持三种运行环境：
    - 源码开发：migrations/ 位于 run.py 同级目录
    - Docker 部署：migrations/ 位于 /app/migrations
    - PyInstaller 打包：migrations/ 位于 sys._MEIPASS/migrations

    兼容性处理：
    - 全新数据库：直接执行全部迁移。
    - 已有数据库但未记录 alembic_version（旧部署）：先标记到引入迁移前的
      基线版本（baseline），再执行后续新增迁移，避免重复创建已存在的表。
    """
    from flask_migrate import upgrade, stamp
    from sqlalchemy import inspect
    from pathlib import Path

    # 引入 Alembic 之前的最后一个 schema 版本（baseline）
    # 该值必须等于当前 head 迁移脚本的 down_revision
    BASELINE_REVISION = '20260718_0016'

    is_packaged = getattr(sys, 'frozen', False)
    if is_packaged:
        migrations_dir = Path(sys._MEIPASS) / 'migrations'
    else:
        migrations_dir = Path(__file__).parent / 'migrations'

    print(f'[Migrate] 迁移目录: {migrations_dir}')

    if not migrations_dir.exists():
        print('[Migrate] ⚠️ 未找到迁移目录，回退到 db.create_all()')
        init_db()
        return

    with app.app_context():
        # ===== 安全加固第 1 步：升级前自动备份 =====
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        db_path = db_uri.replace('sqlite:///', '')
        if db_path and os.path.exists(db_path):
            try:
                backup_path = _backup_database(db_path)
                if backup_path:
                    print(f'[Migrate] 💾 升级前自动备份: {backup_path}')
            except Exception as be:
                print(f'[Migrate] ⚠️ 自动备份失败（不影响迁移）: {be}')
        else:
            print(f'[Migrate] ℹ️ 数据库文件不存在（全新部署），跳过备份')

        # ===== 安全加固第 2 步：迁移前行数快照 =====
        try:
            counts_before = _capture_row_counts()
            total_before = sum(counts_before.values())
            tables_with_data = [t for t, c in counts_before.items() if c > 0]
            print(f'[Migrate] 📊 迁移前快照: {len(counts_before)} 张表, '
                  f'{len(tables_with_data)} 张有数据, 共 {total_before} 行')
        except Exception as e:
            print(f'[Migrate] ⚠️ 迁移前快照失败: {e}')
            counts_before = {}

        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            has_alembic_version = 'alembic_version' in existing_tables

            if not has_alembic_version and not existing_tables:
                # 全新数据库：不重放历史迁移链。
                # 部分表（如 dashboard_shares）从未进入迁移脚本，仅由
                # db.create_all() 创建，SQLite 方言下重放链会在对不存在的表
                # 反射列时抛 NoSuchTableError。按当前模型建全表后标记到最新
                # 版本，与迁移最终态等价且 schema 更完整、可重复执行。
                print('[Migrate] 检测到全新数据库，按当前模型建表并标记最新版本...')
                db.create_all()
                # 多层迁移目录会产生多个分支 head，stamp heads 将所有 head 一并标记
                stamp(directory=str(migrations_dir), revision='heads')
                repair_schema_columns()
                print('[Migrate] ✅ 数据库初始化完成')
                return

            if not has_alembic_version:
                print(f'[Migrate] 检测到旧数据库（无 alembic_version），先标记基线版本 {BASELINE_REVISION}...')
                stamp(directory=str(migrations_dir), revision=BASELINE_REVISION)
                print(f'[Migrate] ✅ 已标记当前版本为 {BASELINE_REVISION}')

            # 注意：**不能**在这里调 db.create_all()！
            # db.create_all() 会按 HEAD 模型定义建所有表（包括完整列集），
            # 这会让 Alembic 的 batch_alter_table 迁移脚本反射到一个"已经是新结构"的表，
            # 从而在重建表时清空核心业务数据（tables/records/fields/views）。
            # 正确做法：让 Alembic 迁移链自然处理表创建。
            # 某些旧库可能缺少个别表（如 workflow_nodes）导致个别迁移脚本抛异常，
            # 但这种失败不会清空已有数据（repair_schema_columns 会继续补齐列），
            # 数据完整性优先级远高于迁移链的 100% 覆盖度。

            # 多层迁移目录会产生多个分支 head（各产品版本层各一个），
            # 必须用 heads 而非 head，否则多 head 场景下 Alembic 会报错
            upgrade(directory=str(migrations_dir), revision='heads')
            # 自修复：补齐因历史迁移被跳过而缺失的模型列（如 dashboard_shares.title）
            repair_schema_columns()
            print('[Migrate] ✅ 数据库迁移完成')

            # ===== 安全加固第 3 步：迁移后行数对比 =====
            try:
                counts_after = _capture_row_counts()
                _print_row_count_diff(counts_before, counts_after)
            except Exception as e:
                print(f'[Migrate] ⚠️ 迁移后快照失败: {e}')

        except Exception as e:
            print(f'[Migrate] ❌ 数据库迁移失败: {e}')
            # 即使迁移失败，也尝试补齐模型列（应对旧库结构漂移），
            # 避免 dashboard_shares 等表缺 title 列导致删除仪表盘失败。
            try:
                repair_schema_columns()
            except Exception as repair_err:
                print(f'[Migrate] ⚠️ 自修复也失败: {repair_err}')

            # ===== 安全加固第 4 步：失败后打印恢复指引 =====
            try:
                counts_after = _capture_row_counts()
                _print_row_count_diff(counts_before, counts_after)
            except Exception:
                pass

            if db_path and os.path.exists(db_path):
                print(f'\n{"=" * 60}')
                print(f'  ⚠️ 数据库迁移失败！请按以下步骤恢复：')
                print(f'  1. 查看备份文件（位于数据目录）:')
                print(f'     {os.path.dirname(db_path)}')
                print(f'  2. 将 .bak 后缀的文件重命名为 smarttable.db 恢复旧数据')
                print(f'  3. 联系开发者并提供错误日志')
                print(f'{"=" * 60}\n')
            raise


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

    如果数据库中没有 ADMIN 角色的用户，则自动创建默认管理员
    （邮箱与密码统一由 app.services.auth_service 的常量定义）。

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

        # 创建默认管理员（凭据统一由 app.services.auth_service 维护，
        # 登录流程据此检测密码是否已修改并提醒）
        default_admin_email = DEFAULT_ADMIN_EMAIL
        default_admin_password = DEFAULT_ADMIN_PASSWORD
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
            print('█'*2)
            print('█  自动创建的默认管理员账号请关注微信公众号后回复“SmartTable”关键词获取账号密码信息')
            # print(f'█  账号 (Account):  {default_admin_name:<34} █')
            # print(f'█  邮箱 (Email):    {default_admin_email:<34} █')
            # print(f'█  密码 (Password): {default_admin_password:<34} █')
            print('█'*2)
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
    elif args.command == 'migrate':
        run_migrations()
        sys.exit(0)
    elif args.command == 'ensure-admin':
        ensure_default_admin_exists()
        sys.exit(0)
    elif args.command == 'create-admin':
        create_admin(args.email, args.password, args.name)
        sys.exit(0)
    elif args.command == 'shell':
        shell()
        sys.exit(0)

    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', '5000'))
    # 安全兜底：未显式设置 FLASK_DEBUG 时默认关闭调试模式，
    # 避免误开启 Werkzeug debugger（RCE 级交互式控制台）
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # 检测是否为 PyInstaller 打包环境
    is_packaged = getattr(sys, 'frozen', False)
    if is_packaged:
        # 打包环境强制关闭调试模式/重载器，避免子进程重复打开浏览器
        debug = False

    # ===== DEBUG 模式安全校验 =====
    # 生产环境（FLASK_ENV=production）禁止开启 DEBUG，否则 Werkzeug debugger 暴露完整交互式控制台
    if config_name == 'production' and debug:
        print('❌ ERROR: DEBUG 模式在生产环境下被禁止！')
        print('   请设置 FLASK_DEBUG=false 或移除 FLASK_DEBUG 环境变量。')
        print('   FLASK_ENV=production 时 Werkzeug debugger 会暴露 RCE 级别的交互式 Python 控制台。')
        sys.exit(1)

    print(f'Starting SmartTable server...')
    print(f'Environment: {config_name}')
    print(f'Host: {host}')
    print(f'Port: {port}')
    print(f'Debug: {debug}')
    print(f'Real-time collaboration: {"enabled" if enable_realtime else "disabled"}')
    print(f'API Documentation: http://{host}:{port}/api/')

    if is_packaged:
        print(f'[Packaging] Running in packaged mode (PyInstaller)')
        print(f'Frontend URL: http://{host}:{port}/')
        # 初始化打包模式（静态文件服务 + Redis 管理）
        initialize_packaging_mode(app, realtime_enabled=enable_realtime)
    else:
        print(f'[Development] Running in development mode')
        print(f'Frontend URL: http://localhost:3000 (Vite dev server)')


    # ===== 自动运行数据库迁移（升级到最新版本）=====
    print('[Init] Checking database schema...')
    try:
        run_migrations()
    except Exception as e:
        # run_migrations 内部已经：
        #   1. 升级前自动备份了 DB 文件
        #   2. 升级失败时尝试了 repair_schema_columns()
        #   3. 打印了恢复指引（备份位置 + 恢复步骤）
        # 因此这里不再盲目 fallback 到 init_db()——
        # init_db() 只做 db.create_all()，既不能修复已 stamp 但未 upgrade 完的
        # 迁移状态，也不能恢复已丢失的数据。贸然调用反而可能掩盖问题。
        # 服务继续启动，若核心表可用则大部分功能不受影响。
        print(f'[Init] ⚠️ 数据库迁移失败，服务继续启动...')
        print(f'[Init]   详细错误和恢复指引见上方 [Migrate] 日志')
        print(f'[Init]   如需强制初始化空库，请手动运行: SmartTable.exe init-db')

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

        # 注意：flask-socketio 5.x 的 SocketIO 类未暴露 eio 属性（eio 位于
        # 内部 server 对象上，且初始化失败时 server 为 None），hasattr(socketio, 'eio')
        # 恒为 False，会把已成功初始化的 SocketIO 误判为失败而退回 Werkzeug
        # （不支持 WebSocket 升级，实时协作全部断连）。改用 server 属性判断。
        if realtime_enabled and getattr(socketio, 'server', None) is not None:
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
