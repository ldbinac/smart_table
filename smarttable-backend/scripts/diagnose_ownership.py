"""诊断 ownership 关系 v2"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db

app = create_app()
ctx = app.app_context()
ctx.push()

from app.models.table import Table
from app.models.base import Base
from app.models.record import Record

# 看所有 tables 属于哪个 base
bases = Base.query.all()
print(f"Bases ({len(bases)}):")
for b in bases:
    print(f"  id={b.id} name={b.name}")

tables = Table.query.all()
print(f"\nAll Tables ({len(tables)}):")
for t in tables:
    recs = Record.query.filter_by(table_id=t.id, is_deleted=False).count()
    is_perf = "⚠️ PERF" if t.name.startswith("perf_test_") else "   "
    print(f"  {is_perf} {t.name:15s} | base_id={t.base_id} | {recs} records")

# 关键问题：前端是按 base 分组显示 table？还是独立显示？
# 直接调用 list_tables API 看返回
print("\n=== 模拟前端 list_tables API ===")
from app.routes.tables import bp as tables_bp
from flask import request

# 直接查 service 层
from app.services.table_service import TableService
service = TableService()

# 用 admin user
from app.models.user import User
admin = User.query.filter_by(email='ldengbin@126.com').first()
result = service.list_tables(admin.id, None)
print(f"list_tables result type: {type(result)}")
if isinstance(result, tuple):
    print(f"  tuple len={len(result)}")
    for i, r in enumerate(result):
        if isinstance(r, list):
            print(f"  [{i}] list of {len(r)} items")
            for item in r[:3]:
                print(f"      {getattr(item, 'name', item)}")
        else:
            print(f"  [{i}] {type(r).__name__} = {str(r)[:100]}")

ctx.pop()
