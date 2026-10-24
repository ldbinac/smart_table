"""验证公式字段计算正确性"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record

app = create_app()
ctx = app.app_context()
ctx.push()

t = Table.query.filter_by(name='perf_test_30000').first()
if not t:
    print("perf_test_30000 not found!")
    ctx.pop()
    sys.exit(1)

fields = Field.query.filter_by(table_id=t.id).order_by(Field.order).all()
print(f"Schema ({len(fields)} fields):")
for f in fields:
    cfg = (f.config or {}).get('formula', '')
    tag = f"  FORMULA: {cfg}" if cfg else ""
    print(f"  {f.name} ({f.type}){tag}")

# 抽样 3 条验证
print(f"\n=== 抽样验证 ===")
from sqlalchemy import func
samples = Record.query.filter_by(table_id=t.id, is_deleted=False).limit(3).all()
for i, rec in enumerate(samples):
    by_name = {}
    for f in fields:
        by_name[f.name] = rec.values.get(str(f.id))

    salary = by_name.get('薪资', 0) or 0
    perf = by_name.get('绩效评分', 0) or 0
    bonus_actual = by_name.get('年终奖')
    bonus_expected = round(salary * perf * 3, 2)
    annual_actual = by_name.get('年薪估算')
    annual_expected = round(salary * 12 + (bonus_actual or 0), 2)

    # IF(绩效>=4.5, 薪资*1.2, 薪资*1.05)
    if perf >= 4.5:
        adjust_expected = round(salary * 1.2, 2)
    else:
        adjust_expected = round(salary * 1.05, 2)
    adjust_actual = by_name.get('调薪建议')

    ok_bonus = abs((bonus_actual or 0) - bonus_expected) < 0.01
    ok_annual = abs((annual_actual or 0) - annual_expected) < 0.01
    ok_adjust = abs((adjust_actual or 0) - adjust_expected) < 0.01

    print(f"\n  Sample #{i+1} (姓名={by_name.get('姓名')}):")
    print(f"    薪资={salary}, 绩效={perf}")
    print(f"    年终奖: actual={bonus_actual} vs expected={bonus_expected} {'✅' if ok_bonus else '❌'}")
    print(f"    年薪估算: actual={annual_actual} vs expected={annual_expected} {'✅' if ok_annual else '❌'}")
    print(f"    调薪建议: actual={adjust_actual} vs expected={adjust_expected} {'✅' if ok_adjust else '❌'}")

ctx.pop()
