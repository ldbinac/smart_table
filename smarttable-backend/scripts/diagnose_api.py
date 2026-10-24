"""直接查 DB 确认 API 会返回什么"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.table import Table
from app.models.base import Base
from app.models.user import User
from app.services.table_service import TableService
from app.services.base_service import BaseService

app = create_app()
ctx = app.app_context()
ctx.push()

admin = User.query.filter_by(email='ldengbin@126.com').first()
base = Base.query.first()

# 模拟前端调的 API
tables = TableService.get_all_tables(str(base.id))
print(f"TableService.get_all_tables(base_id={base.id}) returned {len(tables)} tables:")
for t in tables:
    is_perf = "PERF " if t.name.startswith("perf_test_") else "     "
    print(f"  {is_perf} id={t.id} name={t.name} base_id={t.base_id}")

# 权限检查
perm = BaseService.check_permission(str(base.id), str(admin.id), 'viewer')
print(f"\nBaseService.check_permission: {perm}")

# 检查 Table 有没有 is_deleted 过滤
print(f"\nTable columns: {[c.name for c in Table.__table__.columns]}")
ctx.pop()
