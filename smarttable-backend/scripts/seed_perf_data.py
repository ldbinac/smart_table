"""
批量插入性能测试数据脚本 (v2 — 支持公式字段 + 大表)

为每个规模创建独立的测试表。表 schema 包含 14 个字段：
  - 9 个基础字段（姓名/部门/职位/薪资/入职日期/在职状态/技能标签/绩效评分/备注）
  - 2 个新增基础字段（工龄/预计休年假天数）
  - 3 个公式字段（年终奖/年薪估算/调薪建议），引用 2-3 个源字段

用法:
    python scripts/seed_perf_data.py --scales 500 1000 3000 5000 8000 10000
    python scripts/seed_perf_data.py --scales 30000 50000 70000 100000  # 大表（含公式）
    python scripts/seed_perf_data.py --clean                            # 清所有 perf_*

注意:
    大表（>= 30000）在 SQLite 上单批 500 条 insert，速度约 500-1000 条/秒
    10 万条约需 100-200 秒
"""
import argparse
import sys
import time
import uuid
import random
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.models.table import Table
from app.models.field import Field
from app.models.record import Record
from app.services.formula_service import FormulaService


# ============================================================================
# 大表 schema（14 字段，含 3 个公式字段）
# ============================================================================
# Field def 格式: (name, type, is_primary, options_or_config, formula_expr)
#   formula_expr 非空 → type 自动设为 "formula"，config={'formula': expr}
LARGE_TABLE_SCHEMA = [
    # 基础字段（11 个）
    ("姓名",      "single_line_text", True,  None,          None),
    ("部门",      "single_select",    False, {"options": [
        {"id": "d_dev",   "name": "研发部",   "color": "#409eff"},
        {"id": "d_mkt",   "name": "市场部",   "color": "#67c23a"},
        {"id": "d_hr",    "name": "人力资源", "color": "#e6a23c"},
        {"id": "d_fin",   "name": "财务部",   "color": "#f56c6c"},
        {"id": "d_sales", "name": "销售部",   "color": "#909399"},
    ]}, None),
    ("职位",      "single_line_text", False, None, None),
    ("薪资",      "number",           False, None, None),
    ("入职日期",  "date",             False, None, None),
    ("在职状态",  "checkbox",         False, None, None),
    ("技能标签",  "multi_select",     False, {"options": [
        {"id": "s_py",     "name": "Python",     "color": "#409eff"},
        {"id": "s_js",     "name": "JavaScript", "color": "#f7df1e"},
        {"id": "s_java",   "name": "Java",       "color": "#e76f00"},
        {"id": "s_go",     "name": "Go",         "color": "#00add8"},
        {"id": "s_sql",    "name": "SQL",        "color": "#336791"},
        {"id": "s_design", "name": "设计",       "color": "#e91e63"},
    ]}, None),
    ("绩效评分",  "number",           False, None, None),
    ("工龄",      "number",           False, None, None),   # 新增
    ("年假天数",  "number",           False, None, None),   # 新增
    ("备注",      "long_text",        False, None, None),

    # 公式字段（3 个）
    # 公式 1：年终奖 = 薪资 × 绩效评分 × 3（引用 2 个数字字段）
    ("年终奖",    "formula",          False, None, "{薪资} * {绩效评分} * 3"),
    # 公式 2：年薪估算 = 薪资 × 12 + 年终奖（引用 2 个，含自引用链）
    ("年薪估算",  "formula",          False, None, "{薪资} * 12 + {年终奖}"),
    # 公式 3：调薪建议 = IF(绩效>=4.5, 薪资*1.2, 薪资*1.05)（引用 2 个）
    ("调薪建议",  "formula",          False, None, 'IF({绩效评分} >= 4.5, {薪资} * 1.2, {薪资} * 1.05)'),
]

# 小表 schema（9 字段，原不变）
SMALL_TABLE_SCHEMA = [
    ("姓名",      "single_line_text", True,  None, None),
    ("部门",      "single_select",    False, {"options": [
        {"id": "opt_dev",  "name": "研发部",   "color": "#409eff"},
        {"id": "opt_mkt",  "name": "市场部",   "color": "#67c23a"},
        {"id": "opt_hr",   "name": "人力资源", "color": "#e6a23c"},
        {"id": "opt_fin",  "name": "财务部",   "color": "#f56c6c"},
        {"id": "opt_sales","name": "销售部",   "color": "#909399"},
    ]}, None),
    ("职位",      "single_line_text", False, None, None),
    ("薪资",      "number",           False, None, None),
    ("入职日期",  "date",             False, None, None),
    ("在职状态",  "checkbox",         False, None, None),
    ("技能标签",  "multi_select",     False, {"options": [
        {"id": "s_py",     "name": "Python",     "color": "#409eff"},
        {"id": "s_js",     "name": "JavaScript", "color": "#f7df1e"},
        {"id": "s_java",   "name": "Java",       "color": "#e76f00"},
        {"id": "s_go",     "name": "Go",         "color": "#00add8"},
        {"id": "s_sql",    "name": "SQL",        "color": "#336791"},
        {"id": "s_design", "name": "设计",       "color": "#e91e63"},
    ]}, None),
    ("绩效评分",  "number",           False, None, None),
    ("备注",      "long_text",        False, None, None),
]

FIRST_NAMES = ["张", "李", "王", "刘", "陈", "杨", "赵", "黄", "周", "吴",
               "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "高", "罗"]
LAST_NAMES = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "洋", "艳",
              "勇", "军", "杰", "娟", "涛", "明", "超", "秀英", "霞", "平"]
POSITIONS = ["工程师", "高级工程师", "技术经理", "产品经理", "设计师",
             "分析师", "运营专员", "市场总监", "销售经理", "人力资源师"]
DEPARTMENTS = ["研发部", "市场部", "人力资源", "财务部", "销售部"]
SKILL_POOL = ["Python", "JavaScript", "Java", "Go", "SQL", "设计"]
COMMENTS = [
    "工作态度端正，团队协作良好",
    "具备较强的独立解决问题能力",
    "学习速度快，适应新环境能力强",
    "沟通能力出色，跨部门协作顺畅",
    "技术深度有待提升，建议参加培训",
    "项目交付准时，质量稳定",
    "需要加强文档编写习惯",
    "创新意识强，提出多项改进方案",
    "绩效表现优秀，建议晋升考虑",
    "近期工作状态有所下滑，需关注",
]


def choose_schema(scale: int):
    """>= 30000 条用大表 schema（含公式字段），否则用小表 schema"""
    return LARGE_TABLE_SCHEMA if scale >= 30000 else SMALL_TABLE_SCHEMA


def gen_base_values(field_map: list[tuple[str, str]]):
    """为一条记录生成基础 values（不含公式字段）"""
    values = {}
    now = datetime.now(timezone.utc)

    # 先生成基础变量（公式字段依赖的数值）
    salary = random.randint(8000, 50000)
    perf = round(random.uniform(3.0, 5.0), 1)
    hire_days_ago = random.randint(0, 2000)
    seniority = round(hire_days_ago / 365.25, 1)
    vacation_days = min(22, 5 + int(seniority))

    for fid, fname in field_map:
        if fname == "姓名":
            values[fid] = random.choice(FIRST_NAMES) + random.choice(LAST_NAMES)
        elif fname == "部门":
            values[fid] = random.choice(DEPARTMENTS)
        elif fname == "职位":
            values[fid] = random.choice(POSITIONS)
        elif fname == "薪资":
            values[fid] = salary
        elif fname == "入职日期":
            d = (now - timedelta(days=hire_days_ago)).date()
            values[fid] = d.isoformat()
        elif fname == "在职状态":
            values[fid] = random.random() > 0.15
        elif fname == "技能标签":
            n = random.randint(1, 4)
            chosen = random.sample(SKILL_POOL, n)
            values[fid] = [{"id": f"s_{s.lower().replace(' ', '_')}", "name": s} for s in chosen]
        elif fname == "绩效评分":
            values[fid] = perf
        elif fname == "工龄":
            values[fid] = seniority
        elif fname == "年假天数":
            values[fid] = vacation_days
        elif fname == "备注":
            values[fid] = random.choice(COMMENTS)
        # 公式字段先不填 — 后面统一计算
    return values


def _simple_eval(expr: str, name_to_value: dict) -> float | str | None:
    """
    极简公式求值：支持 {name} 替换、+ - * /、括号、IF(cond, a, b)、比较符 >= > < <= ==
    name_to_value: {字段名: 值}  — 注意这里是字段名→值
    """
    # 1. 替换所有 {字段名}
    def replace_field(m):
        name = m.group(1)
        val = name_to_value.get(name)
        if val is None:
            return '0'
        return str(val) if not isinstance(val, str) else f'"{val}"'

    import re as _re
    substituted = _re.sub(r'\{([^}]+)\}', replace_field, expr)

    # 2. 处理 IF(cond, a, b) — 简化版，只支持单层
    def eval_if(m):
        inner = m.group(1)
        # 简单拆分 cond, a, b — 处理嵌套可能不准，但我们的公式是扁平的
        parts = _split_top_level_commas(inner)
        if len(parts) != 3:
            return '0'
        cond, a, b = parts
        cond = cond.strip()
        a = a.strip()
        b = b.strip()
        try:
            cond_result = _eval_comparison(cond)
            return a if cond_result else b
        except Exception:
            return '0'

    substituted = _re.sub(r'IF\((.+?)\)', eval_if, substituted)

    # 3. 直接 eval 算术表达式（安全，因为是我们自己生成的）
    try:
        # 处理比较结果可能剩 True/False
        result = eval(substituted, {"__builtins__": {}})
        if isinstance(result, (int, float)):
            return round(float(result), 2)
        return result
    except Exception as e:
        return 0


def _split_top_level_commas(s: str) -> list[str]:
    """按顶层逗号拆分（括号内的逗号不算）"""
    parts = []
    depth = 0
    buf = ""
    for c in s:
        if c == '(':
            depth += 1
            buf += c
        elif c == ')':
            depth -= 1
            buf += c
        elif c == ',' and depth == 0:
            parts.append(buf)
            buf = ""
        else:
            buf += c
    parts.append(buf)
    return parts


def _eval_comparison(expr: str) -> bool:
    """求值简单比较表达式，如 '4.5 >= 4.5'"""
    for op in ['>=', '<=', '==', '!=', '>', '<']:
        if op in expr:
            left, right = expr.split(op, 1)
            try:
                lv = float(left.strip())
                rv = float(right.strip())
            except ValueError:
                return False
            if op == '>=': return lv >= rv
            if op == '<=': return lv <= rv
            if op == '==': return lv == rv
            if op == '!=': return lv != rv
            if op == '>':  return lv > rv
            if op == '<':  return lv < rv
    # 没比较符，当 truthy
    try:
        return float(expr.strip()) != 0
    except ValueError:
        return bool(expr.strip())


# ============================================================================
# 表创建
# ============================================================================
def create_perf_table(app, scale: int, base_id: uuid.UUID) -> tuple[uuid.UUID, list[tuple[str, str]], list[tuple[str, str, str]]]:
    """
    创建/复用性能测试表。
    返回 (table_id, field_map, formula_field_list)
      field_map: [(field_id, field_name), ...] — 含公式字段
      formula_field_list: [(field_id, field_name, formula_expr), ...] — 仅公式字段
    """
    schema = choose_schema(scale)
    table_name = f"perf_test_{scale}"

    with app.app_context():
        existing = Table.query.filter_by(name=table_name).first()
        if existing:
            rec_count = Record.query.filter_by(table_id=existing.id).delete()
            # 也删旧 fields（schema 可能变了）
            old_fields = Field.query.filter_by(table_id=existing.id).all()
            for f in old_fields:
                db.session.delete(f)
            db.session.commit()
            print(f"  复用表 {table_name}（已清空旧 {rec_count} 条记录 + {len(old_fields)} 个旧字段）")
        else:
            table = Table(
                id=uuid.uuid4(),
                base_id=base_id,
                name=table_name,
                description=f"性能测试表 - {scale} 条记录（自动生成，含 {len(schema)} 字段）",
            )
            db.session.add(table)
            db.session.flush()
            table_id = table.id

        # 如果是复用，table_id 还没设
        if existing:
            table_id = existing.id

        # 创建 fields
        field_map = []
        formula_fields = []
        for idx, (fname, ftype, is_pri, opts, formula_expr) in enumerate(schema):
            fid = uuid.uuid4()
            if formula_expr:
                ftype = "formula"
                config = {"formula": formula_expr}
                opts = None
                formula_fields.append((str(fid), fname, formula_expr))
            else:
                config = {}

            field = Field(
                id=fid,
                table_id=table_id,
                name=fname,
                type=ftype,
                order=idx,
                is_primary=is_pri,
                is_required=is_pri,
                options=opts if opts else {},
                config=config,
            )
            db.session.add(field)
            field_map.append((str(fid), fname))

        db.session.commit()
        print(f"  已创建表 {table_name}（{len(field_map)} 字段，含 {len(formula_fields)} 公式）")
        return table_id, field_map, formula_fields


# ============================================================================
# 批量插入
# ============================================================================
def bulk_insert_records(app, table_id, field_map, formula_fields, scale, user_id):
    """每 500 条一批 bulk_insert_mappings"""
    batch_size = 500 if scale < 50000 else 200  # 大表减小批次防 SQLite 锁超时
    total = 0
    start = time.time()

    with app.app_context():
        for offset in range(0, scale, batch_size):
            n = min(batch_size, scale - offset)
            mappings = []
            for _ in range(n):
                now = datetime.now(timezone.utc)
                # 基础值
                values = gen_base_values(field_map)
                # 公式计算：需要 name→value 映射
                name_to_val = {}
                for fid, fname in field_map:
                    if fid in values:
                        name_to_val[fname] = values[fid]
                # 计算每个公式字段，写入 values
                for ffid, fname, expr in formula_fields:
                    res = _simple_eval(expr, name_to_val)
                    values[ffid] = res if res is not None else 0
                    # 更新 name_to_val 以便后续公式引用（如 年薪估算 引用 年终奖）
                    name_to_val[fname] = values[ffid]

                mappings.append({
                    "id": uuid.uuid4(),
                    "table_id": table_id,
                    "values": values,
                    "is_deleted": False,
                    "created_by": user_id,
                    "updated_by": user_id,
                    "created_at": now,
                    "updated_at": now,
                })
            db.session.bulk_insert_mappings(Record, mappings)
            db.session.commit()
            total += n
            if total % 10000 == 0 or total == scale:
                elapsed = time.time() - start
                rate = total / elapsed if elapsed > 0 else 0
                print(f"    已插入 {total}/{scale}（{rate:.0f} 条/秒）")

    elapsed = time.time() - start
    rate = scale / elapsed if elapsed > 0 else 0
    print(f"  ✅ {scale} 条完成，耗时 {elapsed:.1f}s（{rate:.0f} 条/秒）")
    return elapsed


# ============================================================================
# 清理
# ============================================================================
def clean_all_perf_tables(app, base_id):
    with app.app_context():
        tables = Table.query.filter(Table.name.like("perf_test_%")).all()
        if not tables:
            print("没有找到 perf_test_* 表")
            return
        for t in tables:
            Record.query.filter_by(table_id=t.id).delete()
            Field.query.filter_by(table_id=t.id).delete()
            db.session.delete(t)
            print(f"  已删除 {t.name}")
        db.session.commit()
        print(f"✅ 清理完成，共 {len(tables)} 张表")


# ============================================================================
# main
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="批量插入性能测试数据 v2")
    parser.add_argument("--scales", nargs="+", type=int,
                        default=[500, 1000, 3000, 5000, 8000, 10000],
                        help="记录数规模")
    parser.add_argument("--clean", action="store_true", help="清理所有 perf_test_* 表后退出")
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        from app.models.base import Base
        from app.models.user import User
        base = Base.query.first()
        user = User.query.first()
        if not base or not user:
            print("❌ 需要至少有一个 base 和一个 user")
            sys.exit(1)
        base_id = base.id
        user_id = user.id

        if args.clean:
            clean_all_perf_tables(app, base_id)
            return

        # 预创建 FormulaService 验证（但实际用我们自己的 _simple_eval）
        print(f"📊 开始生成性能测试数据 v2")
        print(f"   规模: {args.scales}")
        big_scales = [s for s in args.scales if s >= 30000]
        small_scales = [s for s in args.scales if s < 30000]
        if big_scales:
            print(f"   ⚠️  大表（{big_scales}）含 14 字段 + 3 个公式字段")
        if small_scales:
            print(f"   小表（{small_scales}）含 9 字段\n")

        results = {}
        for scale in args.scales:
            schema = choose_schema(scale)
            tag = "大表+公式" if scale >= 30000 else "小表"
            print(f"── 处理 {scale:,} 条记录（{tag}，{len(schema)} 字段）──")
            table_id, field_map, formula_fields = create_perf_table(app, scale, base_id)
            elapsed = bulk_insert_records(app, table_id, field_map, formula_fields, scale, user_id)
            results[scale] = elapsed
            print()

        print("=" * 60)
        print("📋 汇总")
        print("=" * 60)
        total_records = 0
        for scale, elapsed in results.items():
            rate = scale / elapsed if elapsed > 0 else 0
            tag = "⭐公式" if scale >= 30000 else ""
            print(f"  perf_test_{scale:>6,}: {scale:>6,} 条 | {elapsed:>7.1f}s | {rate:>5.0f} 条/秒 {tag}")
            total_records += scale
        print(f"\n  总计: {len(results)} 张表, {total_records:,} 条记录")


if __name__ == "__main__":
    main()
