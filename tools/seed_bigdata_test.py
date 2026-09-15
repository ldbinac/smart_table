"""
大数据量 / 多字段测试数据生成脚本
================================

目标：
    创建一个由 A、B 两张表组成的多维表格：
      * A 为主表，30 个字段，200 条记录
      * B 为从表，70 个字段，1000 条记录
      * A 与 B 通过「关联字段」建立【双向关联】
    并将数据写入本地 SQLite 测试数据库，使用默认用户作为所有者（可直接打开）。

字段类型覆盖（自动编号 / 单行文本 / 多行文本 / 富文本 / 附件 /
单选 / 多选 / 复选框 / 日期 / 日期时间 / 时长 / 公式 / 数字 / 货币 /
百分比 / 评分 / 条码 / 邮箱 / 电话 / 网址 / 创建人 / 最近修改人 / 协作人）。

用法：
    python seed_bigdata_test.py
    DATABASE_URL=sqlite:///绝对路径/xxx.db python seed_bigdata_test.py

默认数据库：release/Windows/data/smarttable.db
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# 0. 路径 & 数据库环境准备
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

DEFAULT_DB = os.path.normpath(
    os.path.join(BACKEND_DIR, "..", "release", "Windows", "data", "smarttable.db")
)
if not os.environ.get("DATABASE_URL"):
    # 绝对路径 -> sqlite:///D:/xxx/smarttable.db
    url_path = DEFAULT_DB.replace("\\", "/")
    os.environ["DATABASE_URL"] = "sqlite:///" + url_path
    print(f"[配置] 使用默认数据库: {DEFAULT_DB}")
else:
    print(f"[配置] 使用环境变量 DATABASE_URL: {os.environ['DATABASE_URL']}")

from app import create_app, db  # noqa: E402
from app.models.base import Base, BaseMember  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.field import Field, FieldType  # noqa: E402
from app.models.link_relation import LinkRelation, LinkValue  # noqa: E402
from app.services.base_service import BaseService  # noqa: E402
from app.services.table_service import TableService  # noqa: E402
from app.services.field_service import FieldService  # noqa: E402
from app.services.record_service import RecordService  # noqa: E402
from app.services.link_service import LinkService  # noqa: E402

# ---------------------------------------------------------------------------
# 1. 参数
# ---------------------------------------------------------------------------
BASE_NAME = "大数据量压测 Base"
TABLE_A_NAME = "表A（主表）"
TABLE_B_NAME = "表B（从表）"

A_FIELD_COUNT = 30      # 表A 字段总数（含主字段 + 关联字段）
B_FIELD_COUNT = 70      # 表B 字段总数（含主字段 + 反向关联字段）
A_RECORD_COUNT = 200    # 表A 记录数
B_RECORD_COUNT = 1000   # 表B 记录数
LINKS_PER_A = 5         # 每条 A 记录关联多少条 B 记录

# ---------------------------------------------------------------------------
# 2. 字段模板（除主字段、关联字段之外的“各种常见类型”字段）
#    每个模板: (类型, 名称前缀, options, config, 生成值的函数)
#    gen(i, ctx) -> 该字段在“第 i 条记录”中的值
# ---------------------------------------------------------------------------
COLORS = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6"]


def _choices(n, prefix):
    return [
        {"id": str(uuid.uuid4()), "name": f"{prefix}{k + 1}", "color": COLORS[k % len(COLORS)]}
        for k in range(n)
    ]


BASE_DATE = datetime(2024, 1, 1)


def build_field_pool():
    """构造字段类型池（保证多种类型都覆盖到）。"""
    pool = []

    # 1. 单行文本
    pool.append({
        "type": FieldType.SINGLE_LINE_TEXT.value,
        "name": "单行文本",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"单行文本-{i:05d}",
    })
    # 2. 多行文本
    pool.append({
        "type": FieldType.LONG_TEXT.value,
        "name": "多行文本",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"多行文本内容，第 {i} 条。\n这是第二行说明文字，用于压测长文本存储与渲染性能。",
    })
    # 3. 富文本
    pool.append({
        "type": FieldType.RICH_TEXT.value,
        "name": "富文本",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"<p>富文本 <b>第 {i} 条</b></p><ul><li>要点一</li><li>要点二</li></ul>",
    })
    # 4. 自动编号
    pool.append({
        "type": FieldType.AUTO_NUMBER.value,
        "name": "自动编号",
        "options": None,
        "config": {"prefix": "SEQ-", "digitLength": 5, "startNumber": 1},
        # 手动给出值，避免依赖 Redis / 全表扫描计算序列号
        "gen": lambda i, c: f"SEQ-{i:05d}",
    })
    # 5. 数字
    pool.append({
        "type": FieldType.NUMBER.value,
        "name": "数字",
        "options": None,
        "config": {"precision": 2},
        "gen": lambda i, c: round(i * 1.37, 2),
    })
    # 6. 货币
    pool.append({
        "type": FieldType.CURRENCY.value,
        "name": "货币",
        "options": None,
        "config": {"symbol": "¥", "precision": 2},
        "gen": lambda i, c: round(i * 99.99, 2),
    })
    # 7. 百分比
    pool.append({
        "type": FieldType.PERCENT.value,
        "name": "百分比",
        "options": None,
        "config": {"precision": 1},
        "gen": lambda i, c: (i * 7) % 100,
    })
    # 8. 评分
    pool.append({
        "type": FieldType.RATING.value,
        "name": "评分",
        "options": None,
        "config": {"max": 5},
        "gen": lambda i, c: (i % 5) + 1,
    })
    # 9. 日期
    pool.append({
        "type": FieldType.DATE.value,
        "name": "日期",
        "options": None,
        "config": None,
        "gen": lambda i, c: (BASE_DATE + timedelta(days=i)).strftime("%Y-%m-%d"),
    })
    # 10. 日期时间
    pool.append({
        "type": FieldType.DATE_TIME.value,
        "name": "日期时间",
        "options": None,
        "config": None,
        "gen": lambda i, c: (BASE_DATE + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    # 11. 时长
    pool.append({
        "type": FieldType.DURATION.value,
        "name": "时长",
        "options": None,
        "config": {"unit": "minute"},
        "gen": lambda i, c: i * 60,
    })
    # 12. 单选
    single_choices = _choices(6, "选项")
    pool.append({
        "type": FieldType.SINGLE_SELECT.value,
        "name": "单选",
        "options": {"choices": single_choices},
        "config": None,
        "gen": lambda i, c: single_choices[i % len(single_choices)]["id"],
    })
    # 13. 多选
    multi_choices = _choices(8, "标签")
    pool.append({
        "type": FieldType.MULTI_SELECT.value,
        "name": "多选",
        "options": {"choices": multi_choices},
        "config": None,
        "gen": lambda i, c: [
            multi_choices[j % len(multi_choices)]["id"]
            for j in range(1, 4)  # 每条记录选 3 个标签
        ],
    })
    # 14. 复选框
    pool.append({
        "type": FieldType.CHECKBOX.value,
        "name": "复选框",
        "options": None,
        "config": None,
        "gen": lambda i, c: (i % 2 == 0),
    })
    # 15. 附件
    pool.append({
        "type": FieldType.ATTACHMENT.value,
        "name": "附件",
        "options": None,
        "config": None,
        "gen": lambda i, c: [{
            "id": str(uuid.uuid4()),
            "name": f"附件_{i}.pdf",
            "originalName": f"附件_{i}.pdf",
            "size": 1024 * ((i % 50) + 1),
            "mimeType": "application/pdf",
            "type": "document",
            "url": f"https://example.com/files/附件_{i}.pdf",
            "uploadedBy": c["user_id"],
        }],
    })
    # 16. 公式
    pool.append({
        "type": FieldType.FORMULA.value,
        "name": "公式",
        "options": None,
        "config": {"formula": "=2*3", "resultType": "number"},
        # 公式值通常由公式计算得出，这里存入一个代表值用于压测
        "gen": lambda i, c: 6,
    })
    # 17. 条码
    pool.append({
        "type": FieldType.BARCODE.value,
        "name": "条码",
        "options": None,
        "config": {"barcodeType": "CODE128"},
        "gen": lambda i, c: f"BC{i:08d}",
    })
    # 18. 邮箱
    pool.append({
        "type": FieldType.EMAIL.value,
        "name": "邮箱",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"user{i:04d}@example.com",
    })
    # 19. 电话
    pool.append({
        "type": FieldType.PHONE.value,
        "name": "电话",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"138{i:08d}",
    })
    # 20. 网址
    pool.append({
        "type": FieldType.URL.value,
        "name": "网址",
        "options": None,
        "config": None,
        "gen": lambda i, c: f"https://example.com/item/{i}",
    })
    # 21. 创建人
    pool.append({
        "type": FieldType.CREATED_BY.value,
        "name": "创建人",
        "options": None,
        "config": {"autoFill": "created_by"},
        "gen": lambda i, c: c["user_id"],
    })
    # 22. 最近修改人
    pool.append({
        "type": FieldType.LAST_MODIFIED_BY.value,
        "name": "最近修改人",
        "options": None,
        "config": {"autoFill": "updated_by"},
        "gen": lambda i, c: c["user_id"],
    })
    # 23. 协作人
    pool.append({
        "type": FieldType.COLLABORATOR.value,
        "name": "协作人",
        "options": None,
        "config": None,
        "gen": lambda i, c: [c["user_id"]],
    })
    return pool


def allocate_fields(pool, total_extra):
    """
    从字段池中取出 total_extra 个字段定义（循环使用池，保证前若干种类型不重复）。
    返回列表，元素为 (name, type, options, config, gen)
    """
    specs = []
    for idx in range(total_extra):
        tpl = pool[idx % len(pool)]
        # 名称加序号，便于区分重复类型
        suffix = "" if idx < len(pool) else f"_{idx + 1}"
        specs.append({
            "name": f"{tpl['name']}{suffix}",
            "type": tpl["type"],
            "options": tpl["options"],
            "config": tpl["config"],
            "gen": tpl["gen"],
        })
    return specs


# ---------------------------------------------------------------------------
# 3. 清理已存在的同名测试 Base（保证脚本可重复执行）
# ---------------------------------------------------------------------------
def cleanup_existing_base():
    existing = Base.query.filter(Base.name == BASE_NAME).all()
    for b in existing:
        print(f"[清理] 删除已存在的测试 Base: {b.id}")
        BaseService.delete_base(str(b.id))
    db.session.commit()


# ---------------------------------------------------------------------------
# 4. 主流程
# ---------------------------------------------------------------------------
def main():
    app = create_app()
    # 降低 SQLAlchemy 引擎日志噪声，避免海量输出并提升速度
    import logging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

    # 本脚本面向“本地无 Redis”的 SQLite 压测环境。
    # Flask-Caching 默认以 Redis 为后端，cache.delete 会在 Redis 不可用时抛错，
    # 而 link_service.update_link_values 在缓存失效异常时（且有 bug）会返回 None，
    # 导致脚本误判失败。此处将缓存相关方法置为 no-op，确保本地可用。
    try:
        from app.extensions import cache as _cache
        for _m in ("delete", "clear", "get", "set", "add", "inc", "dec", "get_many", "set_many"):
            if hasattr(_cache, _m):
                setattr(_cache, _m, lambda *a, **k: None)
    except Exception:
        pass

    with app.app_context():
        # 确保表结构存在（对已存在数据库为 no-op）
        db.create_all()

        # 4.1 默认用户：取第一个用户；若不存在则创建
        user = User.query.order_by(User.created_at.asc()).first()
        if not user:
            user = User(
                email="admin@example.com",
                name="默认用户",
                password="Admin123!",
                role="owner",
                status="active",
                email_verified=True,
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            print(f"[用户] 新建默认用户: {user.email} ({user.id})")
        else:
            print(f"[用户] 使用默认用户: {user.email} ({user.id})")

        # 4.2 清理历史同名数据
        cleanup_existing_base()

        # 4.3 创建 Base 并自动建立 owner 成员关系
        base = BaseService.create_base(
            {
                "name": BASE_NAME,
                "description": "大数据量 / 多字段压测用多维表格（A↔B 双向关联）",
                "icon": "📊",
                "color": "#6366F1",
            },
            str(user.id),
        )
        print(f"[Base] 已创建: {base.name} ({base.id})")

        # 4.4 创建表 A（主表）与表 B（从表），各带主字段 + 默认视图
        table_a = TableService.create_table(str(base.id), {"name": TABLE_A_NAME})
        table_b = TableService.create_table(str(base.id), {"name": TABLE_B_NAME})
        print(f"[表] A={table_a.name}({table_a.id})  B={table_b.name}({table_b.id})")

        # 4.5 在 A 上创建“关联字段”并建立 A↔B 双向关联
        #     该调用会：在 A 上创建 link_to_record 字段，
        #     在 B 上自动创建反向关联字段，并建立两条双向 link_relation。
        link_result = LinkService.create_link_field(
            str(table_a.id),
            {
                "name": f"关联{TABLE_B_NAME}",
                "target_table_id": str(table_b.id),
                "relationship_type": "one_to_many",
                "bidirectional": True,
            },
            str(user.id),
        )
        if not link_result.get("success"):
            raise RuntimeError(f"创建关联字段失败: {link_result}")
        a_link_field_id = link_result["field"]["id"]
        print(f"[关联] A↔B 双向关联已建立，A 侧关联字段: {a_link_field_id}")

        # 取 A→B 的正向关联关系，用于后续写入关联值
        link_relation = LinkRelation.query.filter_by(
            source_field_id=a_link_field_id
        ).first()
        if not link_relation:
            raise RuntimeError("未找到正向 link_relation")
        print(f"[关联] 正向关系 id={link_relation.id} (双向={link_relation.bidirectional})")

        # 4.6 计算还需要创建的“普通字段”数量
        #     表总字段数 = 1(主字段) + 1(关联字段) + 额外字段
        pool = build_field_pool()
        a_extra = A_FIELD_COUNT - 2   # 主字段 + 关联字段 已占 2
        b_extra = B_FIELD_COUNT - 2   # 主字段 + 反向关联字段 已占 2
        a_specs = allocate_fields(pool, a_extra)
        b_specs = allocate_fields(pool, b_extra)

        # 创建 A 的额外字段
        a_fields = []
        for spec in a_specs:
            res = FieldService.create_field(str(table_a.id), {
                "name": spec["name"],
                "type": spec["type"],
                "options": spec["options"],
                "config": spec["config"],
            }, str(user.id))
            if not res.get("success"):
                raise RuntimeError(f"创建 A 字段失败 {spec['name']}: {res}")
            a_fields.append({"id": res["field"]["id"], "spec": spec})
        # 创建 B 的额外字段
        b_fields = []
        for spec in b_specs:
            res = FieldService.create_field(str(table_b.id), {
                "name": spec["name"],
                "type": spec["type"],
                "options": spec["options"],
                "config": spec["config"],
            }, str(user.id))
            if not res.get("success"):
                raise RuntimeError(f"创建 B 字段失败 {spec['name']}: {res}")
            b_fields.append({"id": res["field"]["id"], "spec": spec})

        print(f"[字段] A 共 {table_a.get_field_count()} 个, B 共 {table_b.get_field_count()} 个")

        ctx = {"user_id": str(user.id), "single_choices": None, "multi_choices": None}
        # 把选项塞进 ctx（gen 函数通过闭包直接使用 spec 内选项，这里仅占位）

        # 4.7 写入 B 表记录（1000 条）
        print(f"[记录] 开始写入 B 表 {B_RECORD_COUNT} 条...")
        b_record_ids = []
        for i in range(1, B_RECORD_COUNT + 1):
            values = {}
            for f in b_fields:
                values[f["id"]] = f["spec"]["gen"](i, ctx)
            rec = RecordService.create_record(str(table_b.id), values, str(user.id))
            b_record_ids.append(str(rec.id))
            if i % 200 == 0:
                print(f"  B 已写入 {i}/{B_RECORD_COUNT}")

        # 4.8 写入 A 表记录（200 条）
        print(f"[记录] 开始写入 A 表 {A_RECORD_COUNT} 条...")
        a_record_ids = []
        for i in range(1, A_RECORD_COUNT + 1):
            values = {}
            for f in a_fields:
                values[f["id"]] = f["spec"]["gen"](i, ctx)
            rec = RecordService.create_record(str(table_a.id), values, str(user.id))
            a_record_ids.append(str(rec.id))
            if i % 50 == 0:
                print(f"  A 已写入 {i}/{A_RECORD_COUNT}")

        # 4.9 建立关联值（双向）
        print(f"[关联] 写入双向关联值（每条 A 关联 {LINKS_PER_A} 条 B）...")
        total_b = len(b_record_ids)
        for idx, a_id in enumerate(a_record_ids):
            targets = [
                b_record_ids[(idx * LINKS_PER_A + k) % total_b]
                for k in range(LINKS_PER_A)
            ]
            # update_link_values 在遇到缓存异常时（上游有 bug）会返回 None，
            # 这里做兼容：返回 None 时通过数据库回查确认关联值是否已落库。
            result = LinkService.update_link_values(
                str(link_relation.id), a_id, targets, str(user.id)
            )
            if result is None or not result[0]:
                # 回查确认：link_values 是否已写入
                existed = LinkValue.query.filter_by(
                    link_relation_id=link_relation.id, source_record_id=a_id
                ).count()
                if existed != len(targets):
                    raise RuntimeError(
                        f"写入关联值失败 A={a_id}: {result}"
                    )
            if (idx + 1) % 50 == 0:
                print(f"  已关联 {idx + 1}/{len(a_record_ids)}")

        # 4.10 汇总
        a_count = RecordService.get_table_records(str(table_a.id), 1, 1)[1]
        b_count = RecordService.get_table_records(str(table_b.id), 1, 1)[1]
        link_value_count = LinkValue.query.filter_by(
            link_relation_id=link_relation.id
        ).count()
        # 反向关系中的关联值条数
        reverse_count = LinkValue.query.join(
            LinkRelation, LinkValue.link_relation_id == LinkRelation.id
        ).filter(
            LinkRelation.source_table_id == table_b.id,
            LinkRelation.target_table_id == table_a.id,
        ).count()

        print("\n==================== 生成完成 ====================")
        print(f"Base        : {base.name} ({base.id})")
        print(f"默认用户     : {user.name} <{user.email}> ({user.id})")
        print(f"表A(主表)    : {table_a.name}  字段数={table_a.get_field_count()}  记录数={a_count}")
        print(f"表B(从表)    : {table_b.name}  字段数={table_b.get_field_count()}  记录数={b_count}")
        print(f"双向关联     : 正向 link_values={link_value_count}  反向 link_values={reverse_count}")
        print("==================================================")
        print("请用默认用户登录后，在 Base 列表中打开「%s」即可查看。" % BASE_NAME)


if __name__ == "__main__":
    main()
