"""端到端验证 env.py transactional_ddl=True 修复"""
import tempfile, os, sys, shutil

tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, 'test.db')
# 设置环境变量让 DATABASE_URL 指向临时 db
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
os.environ['FLASK_ENV'] = 'development'

backend = r'd:\_dev\fs_table\smart-table-spec\smarttable-backend'
sys.path.insert(0, backend)
os.chdir(backend)

from alembic.config import Config as _AC
from alembic.script import ScriptDirectory as _SD
cfg = _AC()
cfg.set_main_option('script_location', backend + '\\migrations')
sd = _SD.from_config(cfg)
HEADS = sd.get_heads()
BASELINE = '20260718_0016'
print(f'\nmigration heads: {HEADS}')
print(f'baseline: {BASELINE}')

def check_version(expected):
    from sqlalchemy import create_engine, text
    eng = create_engine(f'sqlite:///{db_path}', future=True)
    with eng.connect() as conn:
        try:
            rows = conn.execute(text('SELECT version_num FROM alembic_version')).fetchall()
            actual = set(r[0] for r in rows)
        except Exception as e:
            print(f'  [CHECK] table missing: {e}')
            return False
    heads = set(expected)
    if actual == heads:
        print(f'  [CHECK] OK alembic_version={actual}')
        return True
    print(f'  [CHECK] MISMATCH actual={actual} expected={heads}')
    return False

all_ok = True

# ===== 场景 1: 全新库 =====
print('\n=== Scenario 1: fresh db ===')
if os.path.exists(db_path): os.remove(db_path)
from run import app, run_migrations
with app.app_context():
    run_migrations()
ok = check_version(HEADS)
if not ok: all_ok = False

# ===== 场景 2: 旧库模拟 (stamp 假版本 -> upgrade heads) =====
print('\n=== Scenario 2: old db simulation ===')
if os.path.exists(db_path): os.remove(db_path)

from flask_migrate import stamp, upgrade
from app.extensions import db

with app.app_context():
    db.create_all()
    # 伪造一个 baseline 之前的版本号
    with db.engine.begin() as conn:
        conn.execute(db.text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32))"))
        conn.execute(db.text("DELETE FROM alembic_version"))
        conn.execute(db.text("INSERT INTO alembic_version VALUES ('20260718_0015')"))
    print(f'  faked alembic_version=20260718_0015 (pre-baseline)')

check_version({'20260718_0015'})

# 先 stamp baseline，再 upgrade heads
with app.app_context():
    stamp(directory=backend + '\\migrations', revision=BASELINE)
    print(f'  stamped baseline={BASELINE}')
    upgrade(directory=backend + '\\migrations', revision='heads')
    print(f'  upgraded to heads')

ok = check_version(HEADS)
if not ok: all_ok = False

# ===== 场景 3: 已是最新库 =====
print('\n=== Scenario 3: already latest ===')
back_dir = os.path.dirname(db_path)
before_baks = len([f for f in os.listdir(back_dir) if '.bak.' in f]) if os.path.isdir(back_dir) else 0

with app.app_context():
    run_migrations()

after_baks = len([f for f in os.listdir(back_dir) if '.bak.' in f]) if os.path.isdir(back_dir) else 0
print(f'  backup count before={before_baks} after={after_baks}')
if after_baks != before_baks:
    print('  BUG: should not backup when already latest')
    all_ok = False
ok = check_version(HEADS)
if not ok: all_ok = False

print('\n' + '=' * 50)
if all_ok:
    print('ALL SCENARIOS PASSED! env.py transactional_ddl=True fix verified')
else:
    print('SOME SCENARIOS FAILED')
print('=' * 50)

shutil.rmtree(tmp)
