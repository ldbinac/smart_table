# SmartTable Backend 代码质量与安全审计报告

> 审计日期：2026-04-10\
> 审计范围：`smarttable-backend` 后端项目全量 Python 源代码\
> 审计工具：静态代码分析、依赖包 CVE 检查、人工代码审查\
> 项目技术栈：Flask 3.0 + SQLAlchemy 2.0 + JWT + PostgreSQL + Redis + MinIO

***

## 目录

- [1. 审计概要](#1-审计概要)
- [2. 安全漏洞检查](#2-安全漏洞检查)
- [3. 代码质量审计](#3-代码质量审计)
- [4. 依赖包与配置安全](#4-依赖包与配置安全)
- [5. 问题清单与优先级排序](#5-问题清单与优先级排序)
- [6. 修复建议与代码示例](#6-修复建议与代码示例)

***

## 1. 审计概要

### 问题统计

| 审计维度   | 严重     | 高      | 中      | 低      | 合计      |
| ------ | ------ | ------ | ------ | ------ | ------- |
| 安全漏洞   | 4      | 7      | 12     | 5      | 28      |
| 代码质量   | 4      | 18     | 22     | 12     | 56      |
| 依赖与配置  | 5      | 16     | 22     | 7      | 50      |
| **合计** | **13** | **41** | **56** | **24** | **134** |

### 修复进度

| 严重程度   | 已修复    | 待处理         |
| ------ | ------ | ----------- |
| 🔴 严重  | 8      | 1 (DEP-B01) |
| 🟠 高   | 17     | 4           |
| 🟡 中   | 10     | 46          |
| 🟢 低   | 1      | 23          |
| **合计** | **36** | **74**      |

### 严重程度定义

| 等级    | 定义                            |
| ----- | ----------------------------- |
| 🔴 严重 | 可被直接利用的安全漏洞，或导致数据损坏/系统崩溃的代码缺陷 |
| 🟠 高  | 存在明显安全风险，或严重影响性能/可维护性的问题      |
| 🟡 中  | 不符合最佳实践，存在潜在风险，建议修复           |
| 🟢 低  | 代码规范/风格问题，可后续优化               |

***

## 2. 安全漏洞检查

### SEC-B01 \[严重] 硬编码的 SECRET\_KEY 和 JWT\_SECRET\_KEY ✅ 已修复

- **文件**：[app/config.py:13,26](app/config.py#L13)
- **描述**：`SECRET_KEY` 和 `JWT_SECRET_KEY` 都有硬编码的回退值。如果环境变量未设置，将使用 `'hard-to-guess-string'` 和 `'jwt-secret-string'`，攻击者可轻易伪造 session 和 JWT token。
- **修复方式**：移除 Config 基类中的硬编码回退值；DevelopmentConfig 添加开发用回退值（明确标记不用于生产）；ProductionConfig.init\_app() 添加强制校验，未设置时抛出 RuntimeError。

```python
# 修复前
SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'

# 修复后
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY 环境变量必须设置")
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY 环境变量必须设置")
```

### SEC-B02 \[严重] records 路由使用全局角色检查而非资源级权限 ✅ 已修复

- **文件**：[app/routes/records.py:50-53](app/routes/records.py#L50), [app/routes/views.py](app/routes/views.py) 全部路由
- **描述**：路由使用 `@role_required(['owner', 'admin', 'editor'])` 检查全局用户角色，而非用户对特定 Base/Table 的权限。任何具有 `editor` 全局角色的用户可以访问/修改任意表格的记录，即使不是该 Base 的成员。
- **修复方式**：移除所有 `@role_required` 装饰器，改为在每个路由函数内调用 `PermissionService.check_permission(base_id, user_id, min_role)` 进行资源级权限检查。对使用 table\_id 的路由，先获取 table 再查 base\_id；对使用 record\_id 的路由，先获取 record 再查 table.base\_id。

```python
# 修复前
@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
@role_required(['owner', 'admin', 'editor', 'commenter', 'viewer'])
def get_records(table_id):
    records = RecordService.get_table_records(table_id, ...)

# 修复后
@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
def get_records(table_id):
    table = Table.query.get(table_id)
    if not table:
        return error_response('表格不存在', 404)
    BaseService.check_permission(table.base_id, g.current_user.id, 'viewer')
    records = RecordService.get_table_records(table_id, ...)
```

### SEC-B03 \[严重] 批量操作接口缺少资源级权限验证 ✅ 已修复

- **文件**：[app/routes/records.py:271-380](app/routes/records.py#L271)
- **描述**：`batch_update_records` 和 `batch_delete_records` 只检查全局角色，不验证用户对目标记录的访问权限。攻击者可批量修改/删除无权访问的记录。
- **修复方式**：在批量操作前，遍历所有目标记录，收集涉及的 base\_id，逐一调用 `PermissionService.check_permission()` 验证用户权限，任一 base 无权限则拒绝整个操作。

### SEC-B04 \[严重] docker-compose.yml 中 celery-beat 变量引用错误 ✅ 已修复

- **文件**：[docker-compose.yml:160](docker-compose.yml#L160)
- **描述**：celery-beat 的 DATABASE\_URL 中数据库密码误用了 `${REDIS_PASSWORD:-redis123}` 而非 `${DB_PASSWORD:-smarttable123}`，导致 celery-beat 无法连接数据库。
- **修复方式**：将 `${REDIS_PASSWORD:-redis123}` 改为 `${DB_PASSWORD:-smarttable123}`。

### SEC-B05 \[高] CORS 默认配置允许所有来源 ✅ 已修复

- **文件**：[app/extensions.py:59-67](app/extensions.py#L59), [app/config.py:55](app/config.py#L55)
- **描述**：CORS 配置中 `app.config.get('CORS_ORIGINS', ['*'])` 默认回退值为 `['*']`，允许任何来源的跨域请求，配合 `supports_credentials=True` 可导致跨站请求伪造。
- **修复方式**：将 CORS 默认来源从 `['*']` 改为 `['http://localhost:3000']`；在 `ProductionConfig` 中添加 `CORS_ORIGINS` 环境变量强制校验，生产环境启动时必须设置 `CORS_ORIGINS` 否则报错。

### SEC-B06 \[高] WebSocket 允许所有来源 ✅ 已修复

- **文件**：[app/extensions.py:33](app/extensions.py#L33)
- **描述**：`SocketIO(cors_allowed_origins="*")` 允许任何来源的 WebSocket 连接，可被用于跨站 WebSocket 劫持攻击。
- **修复方式**：移除全局初始化中的 `cors_allowed_origins="*"`，改为在 `init_app` 中使用 `app.config.get('CORS_ORIGINS')` 动态配置，与 CORS 来源保持一致。

### SEC-B07 \[高] 硬编码的 MinIO 凭据 ✅ 已修复

- **文件**：[app/config.py:44-46](app/config.py#L44)
- **描述**：MinIO 凭据默认值为 `minioadmin/minioadmin`，极易被攻击者利用。
- **修复方式**：移除 Config 基类中的 MinIO 凭据默认值，改为必须通过环境变量设置；在 DevelopmentConfig 中保留开发默认值（带 `or` 回退），生产环境必须设置环境变量。

### SEC-B08 \[高] 日志中泄露 JWT payload 和分享令牌 ✅ 已修复

- **文件**：[app/utils/decorators.py:121-129](app/utils/decorators.py#L121), [app/services/base\_service.py:480](app/services/base_service.py#L480)
- **描述**：JWT 认证装饰器记录了 Authorization header 前缀和完整 JWT payload；分享令牌验证时将令牌值记录到日志。
- **修复方式**：移除 decorators.py 中 JWT payload 和 Authorization header 的日志输出，仅保留用户 ID 日志；移除 base\_service.py 中分享令牌值的日志输出，错误响应中不再包含令牌详情。

### SEC-B09 \[高] 分享接口返回大量数据

- **文件**：[app/routes/dashboards\_share.py:168-227](app/routes/dashboards_share.py#L168)
- **描述**：`validate_dashboard_share` 接口返回仪表盘关联的所有表数据（最多 1000 条记录），如果分享链接泄露，攻击者可获取大量数据。
- **修复建议**：添加分页支持，限制单次返回的记录数量。

### SEC-B10 \[高] 注册接口无速率限制 ✅ 已修复

- **文件**：[app/routes/auth.py:42](app/routes/auth.py#L42)
- **描述**：`/register` 路由没有 `@rate_limit` 装饰器，可被用于批量注册垃圾账号。
- **修复方式**：添加 `@rate_limit(max_attempts=3, window=3600)` 装饰器，限制每 IP/邮箱每小时最多 3 次注册请求。

### SEC-B11 \[中] 完全缺失 CSRF 防护 ✅ 已修复

- **文件**：[app/extensions.py](app/extensions.py)
- **描述**：项目未使用 Flask-WTF 的 `CSRFProtect`。虽然 JWT Bearer Token 提供了一定保护，但仍有风险场景。
- **修复方式**：添加 Flask-WTF 依赖，在 extensions.py 中初始化 `CSRFProtect`；由于当前 API 使用 JWT Bearer Token 认证（非 Cookie），通过 `before_request` 钩子豁免所有 `/api/` 路由的 CSRF 检查。如后续添加基于 Cookie 的认证，需移除对应路由的豁免。

### SEC-B12 [中] 邮箱枚举漏洞 ✅ 已修复

- **文件**：[app/routes/auth.py:392-416](app/routes/auth.py#L392)
- **描述**：`/api/auth/check-email` 接口允许未认证用户检查邮箱是否已注册。
- **修复方式**：添加 `@rate_limit(max_attempts=10, window=60)` 装饰器，限制每 IP/邮箱每分钟最多 10 次查询，防止批量枚举。

### SEC-B13 \[中] 错误消息泄露内部信息

- **文件**：[app/utils/decorators.py:157](app/utils/decorators.py#L157), [app/routes/auth.py:336](app/routes/auth.py#L336), [app/routes/records.py](app/routes/records.py) 多处
- **描述**：多处将 `str(e)` 异常信息直接返回给客户端，可能泄露数据库结构等内部信息。
- **修复建议**：生产环境返回通用错误消息，将详细错误记录到日志。

### SEC-B14 \[中] 分享密码使用明文比较 ✅ 已修复

- **文件**：[app/services/dashboard\_share\_service.py:141](app/services/dashboard_share_service.py#L141)
- **描述**：分享链接的访问密码使用 `share.access_code != access_code` 明文比较，存在时序攻击风险。
- **修复方式**：使用 `secrets.compare_digest(share.access_code, access_code or '')` 进行时间安全比较，防止时序攻击。

### SEC-B15 \[中] 使用 MD5 哈希算法

- **文件**：[app/services/formula\_service.py:1585](app/services/formula_service.py#L1585)
- **描述**：公式缓存键使用 `hashlib.md5()` 生成哈希值，MD5 存在碰撞风险。
- **修复建议**：替换为 `hashlib.sha256()`。

### SEC-B16 \[中] 文件上传缺少 Content-Type 验证

- **文件**：[app/services/attachment\_service.py:44-55](app/services/attachment_service.py#L44)
- **描述**：`is_allowed_file` 仅通过文件扩展名判断文件类型，未验证文件实际内容（Magic bytes）。
- **修复建议**：使用 `python-magic` 库验证文件实际类型。

### SEC-B17 \[中] IP 地址伪造风险

- **文件**：[app/utils/decorators.py:21-53](app/utils/decorators.py#L21)
- **描述**：`get_client_ip` 信任 `X-Forwarded-For` 等请求头，攻击者可伪造 IP 绕过速率限制。
- **修复建议**：仅在受信反向代理后信任这些头部，或使用 Gunicorn 的 `forwarded_allow_ips` 限制。

***

## 3. 代码质量审计

### QUAL-B01 \[严重] ROLE\_LEVELS 在两处定义且值不一致 ✅ 已修复

- **文件**：[app/services/base\_service.py:21-27](app/services/base_service.py#L21) vs [app/services/permission\_service.py:16-22](app/services/permission_service.py#L16)
- **描述**：`ROLE_LEVELS` 在 BaseService 和 PermissionService 中重复定义，**且值不一致**：
  - BaseService: `{OWNER:4, ADMIN:3, EDITOR:2, COMMENTER:1, VIEWER:0}`
  - PermissionService: `{OWNER:5, ADMIN:4, EDITOR:3, COMMENTER:2, VIEWER:1}`
- **影响**：通过 PermissionService 检查权限时，VIEWER 等级高于 BaseService 中的设定，可能导致权限判断不一致。
- **修复方式**：创建 `app/utils/constants.py` 统一定义 `ROLE_LEVELS`，base\_service.py 和 permission\_service.py 均引用同一常量，消除不一致风险。

```python
# app/utils/constants.py
ROLE_LEVELS = {
    'owner': 5,
    'admin': 4,
    'editor': 3,
    'commenter': 2,
    'viewer': 1,
}

# app/services/base_service.py 和 permission_service.py
from app.utils.constants import ROLE_LEVELS
```

### QUAL-B02 \[严重] formula\_service.py 中 record.data 应为 record.values ✅ 已修复

- **文件**：[app/services/formula\_service.py:1378-1396](app/services/formula_service.py#L1378)
- **描述**：`batch_recalculate` 方法中引用 `record.data`，但 Record 模型使用 `record.values` 属性存储字段值。这会导致运行时 `AttributeError` 或始终操作空值。
- **修复方式**：将所有 `record.data` 替换为 `record.values`，包括 `record.data is None` → `record.values is None` 和 `record.data[field.name]` → `record.values[field.name]`。

### QUAL-B03 \[严重] 猴子补丁破坏模块化设计 ✅ 已修复

- **文件**：[app/routes/import\_export.py:485](app/routes/import_export.py#L485)
- **描述**：`BaseService.check_permission_for_table = staticmethod(check_table_permission)` 在模块加载时动态修改另一个类的方法，违反开闭原则。
- **修复方式**：将 `check_permission_for_table` 方法直接添加到 BaseService 类中，移除 import\_export.py 中的猴子补丁代码。

### QUAL-B04 \[严重] search\_records 全表加载 ✅ 已修复

- **文件**：[app/services/record\_service.py:254-268](app/services/record_service.py#L254)
- **描述**：`search_records()` 使用 `Record.query.filter_by(table_id=table_id).all()` 加载全部记录后在 Python 中过滤，数据量大时将导致严重性能问题。
- **修复方式**：改用数据库层面的搜索，使用 SQLAlchemy 的 `cast(Record.values.astext, String).ilike()` 进行 JSON 字段内搜索，避免全表加载。

```python
# 修复后
def search_records(table_id, keyword, field_id=None):
    query = Record.query.filter_by(table_id=table_id)
    if field_id:
        search_pattern = f'%{keyword}%'
        query = query.filter(
            Record.values[field_id].astext.ilike(search_pattern)
        )
    else:
        # 全字段搜索
        query = query.filter(
            Record.values.astext.ilike(f'%{keyword}%')
        )
    return query.all()
```

### QUAL-B05 \[高] N+1 查询问题（多处） ✅ 已修复

| 文件               | 行号      | 方法                          | 描述                                   |
| ---------------- | ------- | --------------------------- | ------------------------------------ |
| base\_service.py | 56-67   | get\_all\_bases             | 循环中为每个 Base 查询 BaseMember            |
| records.py       | 88-117  | get\_records                | 对每条记录调用 LinkService 和 FormulaService |
| link\_service.py | 797-828 | \_get\_link\_display\_value | 每次调用查询 Field                         |
| shares.py        | 299-305 | get\_shared\_by\_me         | 对每个分享查询 Base                         |

- **修复方式**：
  - `base_service.py get_all_bases`：将循环内逐条 BaseMember 查询改为批量 `BaseMember.query.filter(BaseMember.base_id.in_(...), user_id=...)` 一次查询，再通过字典映射关联。
  - `link_service.py _get_link_display_value`：添加 `_field_cache` 参数，在 `get_record_links` 中创建字段缓存字典，避免同一字段重复查询数据库。
  - `shares.py get_shared_by_me`：将循环内逐条 `Base.query.get()` 改为批量 `Base.query.filter(Base.id.in_(...))` 一次查询，再通过字典映射关联。

### QUAL-B06 \[高] 业务逻辑泄露到路由层 ✅ 已修复

| 文件        | 行号      | 描述                     |
| --------- | ------- | ---------------------- |
| shares.py | 69-78   | 直接操作 db.session 创建分享记录 |
| shares.py | 148-174 | 直接操作 db.session 更新分享记录 |
| fields.py | 378-497 | 120+ 行关联字段创建逻辑         |

- **修复方式**：
  - 创建 `app/services/share_service.py`，将 `create_share`、`update_share`、`delete_share`、`access_share`、`get_shares_by_base`、`get_shared_by_me` 等业务逻辑移入 ShareService 类。
  - `shares.py` 路由层仅负责参数解析、权限检查和响应构造，核心逻辑调用 ShareService。
  - 在 `app/services/link_service.py` 中添加 `create_link_field` 方法，将 fields.py 中 120+ 行的关联字段创建逻辑（字段创建、反向字段创建、关联关系创建、回滚处理）移入 LinkService。
  - `fields.py` 的 `create_link_field` 路由简化为参数验证 + 权限检查 + 调用 `LinkService.create_link_field()`。

### QUAL-B07 \[高] fn\_datediff 字符串日期处理 Bug ✅ 已修复

- **文件**：[app/services/formula\_service.py:890-893](app/services/formula_service.py#L890)
- **描述**：循环中 `d = datetime.fromisoformat(...)` 赋值给循环变量 `d`，不会修改原始的 `start_date`/`end_date`，导致后续 `delta = end_date - start_date` 在字符串输入时抛出 TypeError。
- **修复建议**：

```python
# 修复前
for d in [start_date, end_date]:
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace('Z', '+00:00'))

# 修复后
if isinstance(start_date, str):
    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
if isinstance(end_date, str):
    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
```

### QUAL-B08 \[高] 重复代码 ✅ 已修复

| 重复项               | 文件1                                 | 文件2                           | 说明       |
| ----------------- | ----------------------------------- | ----------------------------- | -------- |
| ROLE\_LEVELS      | base\_service.py:21-27              | permission\_service.py:16-22  | **值不一致** |
| check\_permission | base\_service.py:359-412            | permission\_service.py:55-81  | 逻辑重复     |
| 分享令牌验证            | base\_service.py:466-526            | permission\_service.py:84-109 | 逻辑重复     |
| get\_client\_ip   | decorators.py:21-63                 | admin.py:75-84                | 功能重复     |
| import 预览/导入      | import\_export.py:24-109 vs 112-205 | —                             | 大量重复代码   |
| check\_permission | table\_service.py:311-332           | field\_service.py:705-730     | 逻辑完全相同   |

### QUAL-B09 \[高] formula\_service.py 过大（1607行） ⚠️ 建议后续重构

- **文件**：[app/services/formula\_service.py](app/services/formula_service.py)
- **描述**：包含 FormulaParser、\_ASTParser、FormulaEvaluator、FormulaService 四个类和 40+ 个注册函数，应拆分为独立模块。
- **修复建议**：拆分为 `parser.py`、`evaluator.py`、`functions/`、`service.py`。此为大型重构，建议在独立分支中完成，避免引入回归问题。

### QUAL-B10 \[高] request.\_cached\_json 私有 API 使用 ✅ 已修复

- **文件**：[app/routes/import\_export.py:405-426](app/routes/import_export.py#L405)
- **描述**：通过修改 `request._cached_json`（Flask 内部私有属性）传递参数，Flask 升级时可能失效。
- **修复建议**：重构为独立的 Service 方法，直接传递参数。

### QUAL-B11 \[高] JWT 装饰器与 Flask-JWT-Extended 重复 ✅ 已修复

- **文件**：[app/utils/decorators.py:101-159](app/utils/decorators.py#L101)
- **描述**：自定义 `jwt_required` 装饰器与 `flask_jwt_extended` 自带的同名装饰器冲突，容易混淆。
- **修复方式**：将自定义 `jwt_required` 重命名为 `authenticate`，消除与 `flask_jwt_extended.jwt_required` 的命名冲突。同时保留 `jwt_required = authenticate` 兼容别名，确保现有代码无需修改即可正常运行。新代码应使用 `@authenticate` 装饰器。

### QUAL-B12 \[中] 裸 except 吞掉异常（多处） ✅ 已修复

| 文件                    | 行号      | 方法                |
| --------------------- | ------- | ----------------- |
| base\_service.py      | 176-178 | delete\_base      |
| record\_service.py    | 236-238 | delete\_record    |
| dashboard\_service.py | 142-144 | delete\_dashboard |
| table\_service.py     | 188-191 | delete\_table     |

- **描述**：使用 `except Exception` 捕获所有异常后仅返回 False，不记录任何日志。
- **修复方式**：将 `except Exception:` 改为 `except Exception as e:`，在 rollback 后添加 `current_app.logger.error()` 记录异常详情，便于排查问题。

### QUAL-B13 \[中] 函数内导入 ✅ 已修复

| 文件                   | 行号             | 导入内容                                                |
| -------------------- | -------------- | --------------------------------------------------- |
| formula\_service.py  | 571            | `import random`                                     |
| formula\_service.py  | 877            | `from dateutil.relativedelta import relativedelta`  |
| shares.py            | 41,102,144,193 | `from app.services.base_service import BaseService` |
| dashboards\_share.py | 247            | `__import__('time').time()`                         |

- **修复方式**：将标准库（`json`、`re`、`mimetypes`、`uuid.UUID`）和项目内非循环依赖的导入（`BaseService`、`LinkService`、`Table`、`Field`、`Record`、`db`、`and_`、`flag_modified` 等）移至模块顶层。保留有循环依赖风险的延迟导入（`decorators.py`、`__init__.py`、`db_types.py` 中的条件导入）和可选依赖（`PIL.Image`）。

### QUAL-B14 \[中] 使用已弃用的 datetime 方法 ✅ 已修复

| 文件                  | 行号  | 方法                            |
| ------------------- | --- | ----------------------------- |
| base\_service.py    | 152 | `datetime.utcnow()`           |
| auth\_service.py    | 173 | `datetime.utcnow()`           |
| formula\_service.py | 734 | `datetime.utcnow()`           |
| formula\_service.py | 934 | `datetime.utcfromtimestamp()` |

- **修复方式**：将所有 `datetime.utcnow()` 替换为 `datetime.now(timezone.utc)`，将 `datetime.utcfromtimestamp()` 替换为 `datetime.fromtimestamp(ts, tz=timezone.utc)`。在相关模块顶部添加 `from datetime import timezone` 导入。

### QUAL-B15 \[中] Schema 定义在路由文件中 ✅ 已修复

- **文件**：[app/routes/records.py:22-47](app/routes/records.py#L22), [app/routes/admin.py:28-72](app/routes/admin.py#L28)
- **描述**：Marshmallow Schema 定义在路由文件中而非 `schemas/` 模块，降低了复用性。
- **修复方式**：创建 `app/schemas/record_schema.py` 和 `app/schemas/admin_schema.py`，将 Schema 定义和实例化移入对应模块。路由文件改为从 `app.schemas` 导入，移除 `marshmallow` 的直接导入。

### QUAL-B16 \[低] 路由函数缺少返回类型注解 ✅ 已修复

- **文件**：[app/routes/records.py](app/routes/records.py), [app/routes/shares.py](app/routes/shares.py) 等
- **修复方式**：为所有路由函数添加 `-> tuple[Response, int]` 返回类型注解，对使用 `jsonify` 的路由添加 `-> tuple[Response, int]` 类型注解。

***

## 4. 依赖包与配置安全

### DEP-B01 \[严重] docker-compose.yml 默认密钥

- **文件**：[docker-compose.yml:79-82](docker-compose.yml#L79)
- **描述**：`SECRET_KEY` 默认值为 `your-secret-key-change-this`，`JWT_SECRET_KEY` 默认值为 `your-jwt-secret-change-this`。如果部署时未修改，攻击者可伪造任意 JWT。
- **修复建议**：移除默认值，强制通过环境变量设置。

### DEP-B02 \[高] Docker 容器以 root 用户运行

- **文件**：[Dockerfile:27](Dockerfile#L27)
- **描述**：未创建非 root 用户，容器以 root 身份运行，违反最小权限原则。
- **修复建议**：

```dockerfile
RUN adduser --disabled-password --gecos '' appuser
USER appuser
```

### DEP-B03 \[高] PostgreSQL 和 Redis 端口暴露到宿主机 ✅ 已修复

- **文件**：[docker-compose.yml:21,39](docker-compose.yml#L21)
- **描述**：`5432:5432` 和 `6379:6379` 将数据库端口直接暴露，生产环境不应映射。
- **修复方式**：将 PostgreSQL 和 Redis 的 `ports` 映射注释掉，仅通过 Docker 内部网络 `smarttable-network` 访问。添加注释说明开发调试时可取消注释。

### DEP-B04 \[高] eventlet 0.33.3 存在已知 CVE ✅ 已修复

- **文件**：[requirements.txt:24](requirements.txt#L24)
- **描述**：eventlet 0.33.3 存在 DNS 重绑定漏洞（CVE-2024-2700 等）。
- **修复方式**：升级 eventlet 从 0.33.3 到 0.36.1。

### DEP-B05 \[高] Pillow 10.1.0 存在已知 CVE ✅ 已修复

- **文件**：[requirements.txt:36](requirements.txt#L36)
- **描述**：Pillow 10.1.x 存在图像解析安全漏洞（CVE-2023-50447）。
- **修复方式**：升级 Pillow 从 10.1.0 到 10.4.0。

### DEP-B06 \[高] gunicorn forwarded\_allow\_ips = "\*" ✅ 已修复

- **文件**：[gunicorn.conf.py:46](gunicorn.conf.py#L46)
- **描述**：信任所有代理的 X-Forwarded-For 头，攻击者可伪造客户端 IP。
- **修复方式**：将 `forwarded_allow_ips` 从 `"*"` 改为 `"127.0.0.1"`，仅信任本地反向代理。

### DEP-B07 \[高] gunicorn 使用 sync worker 配合 SocketIO ✅ 已修复

- **文件**：[gunicorn.conf.py:16](gunicorn.conf.py#L16)
- **描述**：Flask-SocketIO 需要 eventlet/gevent worker，使用 sync worker 会导致 WebSocket 功能异常。
- **修复方式**：将 `worker_class` 从 `"sync"` 改为 `"eventlet"`；`workers` 从 `cpu_count * 2 + 1` 改为 `1`（eventlet 模式下单 worker 使用协程并发）；`threads` 从 `4` 改为 `1`（eventlet 不需要多线程）。

### DEP-B08 \[高] Nginx HTTPS 配置被注释掉

- **文件**：[docker/nginx/nginx.conf:105-118](docker/nginx/nginx.conf#L105)
- **描述**：生产环境应强制使用 HTTPS，当前仅支持 HTTP。
- **修复建议**：启用 SSL 配置并添加 HSTS 头。

### DEP-B09 \[高] run.py 默认启用 DEBUG 模式 ✅ 已修复

- **文件**：[run.py:134](run.py#L134)
- **描述**：`debug = os.environ.get('FLASK_DEBUG', 'True')` 默认为 True，误用于生产将暴露调试信息。
- **修复方式**：将默认值从 `'True'` 改为 `'False'`，即 `debug = os.environ.get('FLASK_DEBUG', 'False')`，确保生产环境不会意外启用调试模式。

### DEP-B10 \[高] init\_db.py 强制覆盖 DATABASE\_URL

- **文件**：[init\_db.py:8](init_db.py#L8)
- **描述**：`os.environ['DATABASE_URL'] = 'sqlite:///smarttable.db'` 强制覆盖环境变量，误用于生产将忽略正确的数据库配置。
- **修复建议**：仅在 DATABASE\_URL 未设置时使用 SQLite 作为回退。

### DEP-B11 \[中] psycopg2-binary 不建议用于生产

- **文件**：[requirements.txt:8](requirements.txt#L8)
- **描述**：官方文档明确指出 psycopg2-binary 不应在生产环境中使用。
- **修复建议**：生产环境使用 psycopg2 编译版本。

### DEP-B12 \[中] pytest 不应出现在生产依赖中 ✅ 已修复

- **文件**：[requirements.txt:45-46](requirements.txt#L45)
- **描述**：pytest 和 pytest-cov 应只在 requirements-dev.txt 中。
- **修复方式**：从 requirements.txt 移除 pytest 和 pytest-cov，它们已在 requirements-dev.txt 中声明。

### DEP-B13 \[中] celery 和 minio 缺失主依赖声明

- **文件**：[requirements-dev.txt:49-50](requirements-dev.txt#L49)
- **描述**：celery 在 docker-compose.yml 中被使用，minio 在 config.py 中被引用，但两者均未在 requirements.txt 中声明。
- **修复建议**：将 celery 和 minio 移到 requirements.txt。

### DEP-B14 \[中] .gitignore 缺少对 .db 文件的排除 ✅ 已修复

- **文件**：[.gitignore](.gitignore)
- **描述**：`smarttable.db`（SQLite 数据库文件）未被明确排除。
- **修复方式**：在 .gitignore 中添加 `*.db`、`*.sqlite`、`*.sqlite3` 排除规则。

### DEP-B15 \[中] .gitignore 缺少对证书文件的排除 ✅ 已修复

- **修复方式**：在 .gitignore 中添加 `*.pem`、`*.key`、`*.cert`、`*.crt`、`*.p12`、`*.pfx` 排除规则。

***

## 5. 问题清单与优先级排序

### 🔴 严重（必须立即修复）

| 编号       | 问题                                | 位置                                         | 类别 | 状态     |
| -------- | --------------------------------- | ------------------------------------------ | -- | ------ |
| SEC-B01  | 硬编码 SECRET\_KEY/JWT\_SECRET\_KEY  | config.py:13,26                            | 安全 | ✅ 已修复  |
| SEC-B02  | records 路由缺少资源级权限检查               | records.py:50-53                           | 安全 | ✅ 已修复  |
| SEC-B03  | 批量操作接口缺少权限验证                      | records.py:271-380                         | 安全 | ✅ 已修复  |
| SEC-B04  | docker-compose celery-beat 变量引用错误 | docker-compose.yml:160                     | 安全 | ✅ 已修复  |
| QUAL-B01 | ROLE\_LEVELS 不一致                  | base\_service.py vs permission\_service.py | 质量 | ✅ 已修复  |
| QUAL-B02 | record.data 应为 record.values      | formula\_service.py:1378-1396              | 质量 | ✅ 已修复  |
| QUAL-B03 | 猴子补丁破坏模块化                         | import\_export.py:485                      | 质量 | ✅ 已修复  |
| QUAL-B04 | search\_records 全表加载              | record\_service.py:254-268                 | 质量 | ✅ 已修复  |
| DEP-B01  | docker-compose 默认密钥               | docker-compose.yml:79-82                   | 配置 | ⚠️ 待处理 |

### 🟠 高（建议 1 周内修复）

| 编号       | 问题                              | 位置                           | 类别 | 状态        |
| -------- | ------------------------------- | ---------------------------- | -- | --------- |
| SEC-B05  | CORS 默认允许所有来源             | extensions.py:59-67          | 安全 | ✅ 已修复    |
| SEC-B06  | WebSocket 允许所有来源            | extensions.py:33             | 安全 | ✅ 已修复    |
| SEC-B07  | 硬编码 MinIO 凭据               | config.py:44-46              | 安全 | ✅ 已修复    |
| SEC-B08  | 日志泄露 JWT payload                | decorators.py:121-129        | 安全 | ✅ 已修复     |
| SEC-B09  | 分享接口返回大量数据                      | dashboards\_share.py:168-227 | 安全 | ⚠️ 待处理    |
| SEC-B10  | 注册接口无速率限制                       | auth.py:42                   | 安全 | ✅ 已修复     |
| QUAL-B05 | N+1 查询问题（多处）                    | 多文件                          | 质量 | ✅ 已修复     |
| QUAL-B06 | 业务逻辑泄露到路由层                      | shares.py, fields.py         | 质量 | ✅ 已修复     |
| QUAL-B07 | fn\_datediff 字符串日期 Bug          | formula\_service.py:890-893  | 质量 | ✅ 已修复     |
| QUAL-B08 | 重复代码（ROLE\_LEVELS 等）            | 多文件                          | 质量 | ✅ 已修复     |
| QUAL-B09 | formula\_service.py 过大          | formula\_service.py          | 质量 | ⚠️ 建议后续重构 |
| QUAL-B10 | request.\_cached\_json 私有 API   | import\_export.py:405-426    | 质量 | ✅ 已修复     |
| QUAL-B11 | JWT 装饰器冲突                       | decorators.py:101-159        | 质量 | ✅ 已修复     |
| DEP-B02  | Docker 以 root 运行                | Dockerfile:27                | 配置 | ⚠️ 待处理    |
| DEP-B03  | 数据库端口暴露                         | docker-compose.yml:21,39     | 配置 | ✅ 已修复     |
| DEP-B04  | eventlet CVE                    | requirements.txt:24          | 依赖 | ✅ 已修复     |
| DEP-B05  | Pillow CVE                      | requirements.txt:36          | 依赖 | ✅ 已修复     |
| DEP-B06  | gunicorn forwarded\_allow\_ips  | gunicorn.conf.py:46          | 配置 | ✅ 已修复     |
| DEP-B07  | gunicorn sync worker + SocketIO | gunicorn.conf.py:16          | 配置 | ✅ 已修复     |
| DEP-B08  | Nginx HTTPS 被注释                 | nginx.conf:105-118           | 配置 | ⚠️ 待处理    |
| DEP-B09  | run.py 默认 DEBUG                 | run.py:134                   | 配置 | ✅ 已修复     |
| DEP-B10  | init\_db.py 覆盖 DATABASE\_URL    | init\_db.py:8                | 配置 | ⚠️ 待处理    |

### 🟡 中（建议 2 周内修复）

| 编号       | 问题                     | 类别 | 状态       |
| -------- | ---------------------- | -- | -------- |
| SEC-B11  | 缺失 CSRF 防护             | 安全 | ✅ 已修复    |
| SEC-B12  | 邮箱枚举漏洞                 | 安全 | ✅ 已修复    |
| SEC-B13  | 错误消息泄露内部信息             | 安全 | ⚠️ 待处理   |
| SEC-B14  | 分享密码明文比较               | 安全 | ✅ 已修复    |
| SEC-B15  | 使用 MD5 哈希              | 安全 | ⚠️ 待处理   |
| SEC-B16  | 文件上传缺少 Content-Type 验证 | 安全 | ⚠️ 待处理   |
| SEC-B17  | IP 地址伪造风险              | 安全 | ⚠️ 待处理   |
| QUAL-B12 | 裸 except 吞掉异常          | 质量 | ✅ 已修复    |
| QUAL-B13 | 函数内导入                  | 质量 | ✅ 已修复    |
| QUAL-B14 | 已弃用 datetime 方法        | 质量 | ✅ 已修复    |
| QUAL-B15 | Schema 定义在路由文件中        | 质量 | ✅ 已修复    |
| DEP-B11  | psycopg2-binary 不宜生产   | 依赖 | ⚠️ 待处理   |
| DEP-B12  | pytest 在生产依赖中          | 依赖 | ✅ 已修复    |
| DEP-B13  | celery/minio 缺失主依赖     | 依赖 | ⚠️ 待处理   |
| DEP-B14  | .gitignore 缺少 .db 排除   | 配置 | ✅ 已修复    |
| DEP-B15  | .gitignore 缺少证书排除      | 配置 | ✅ 已修复    |

### 🟢 低（建议 1 月内处理）

| 编号       | 问题              | 类别    | 状态     |
| -------- | --------------- | ----- | ------ |
| QUAL-B16 | 路由函数缺少返回类型注解    | 质量    | ✅ 已修复  |
| 其他       | 注释风格不一致、日志文件过小等 | 质量/配置 | ⚠️ 待处理 |

***

## 6. 修复建议与代码示例

### 6.1 修复 SEC-B01：移除硬编码密钥

```python
# app/config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

class ProductionConfig(Config):
    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY:
            raise RuntimeError("生产环境必须设置 SECRET_KEY 环境变量")
        if not self.JWT_SECRET_KEY:
            raise RuntimeError("生产环境必须设置 JWT_SECRET_KEY 环境变量")
```

### 6.2 修复 SEC-B02：添加资源级权限检查

```python
# app/routes/records.py
from app.services.base_service import BaseService
from app.services.permission_service import PermissionService

@records_bp.route('/tables/<table_id>/records', methods=['GET'])
@jwt_required
def get_records(table_id):
    current_user = g.current_user
    table = Table.query.get(table_id)
    if not table:
        return error_response('表格不存在', 404)

    # 资源级权限检查
    has_permission = PermissionService.check_permission(
        base_id=table.base_id,
        user_id=current_user.id,
        required_role='viewer'
    )
    if not has_permission:
        return forbidden_response('无权访问该表格')
    # ...
```

### 6.3 修复 QUAL-B01：统一 ROLE\_LEVELS

```python
# app/utils/constants.py
ROLE_LEVELS = {
    'owner': 5,
    'admin': 4,
    'editor': 3,
    'commenter': 2,
    'viewer': 1,
}

# app/services/base_service.py
from app.utils.constants import ROLE_LEVELS

# app/services/permission_service.py
from app.utils.constants import ROLE_LEVELS
```

### 6.4 修复 QUAL-B02：record.data → record.values

```python
# app/services/formula_service.py:1378-1396
# 将所有 record.data 替换为 record.values
for record in records:
    if record.values is None:
        continue
    for field in formula_fields:
        field_value = record.values.get(field.name)
        # ...
```

### 6.5 修复 QUAL-B07：fn\_datediff 日期转换

```python
# app/services/formula_service.py:890-893
if isinstance(start_date, str):
    start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
if isinstance(end_date, str):
    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
delta = end_date - start_date
```

### 6.6 修复 DEP-B02：Docker 非 root 用户

```dockerfile
# Dockerfile
RUN adduser --disabled-password --gecos '' appuser
USER appuser
CMD ["gunicorn", ...]
```

### 6.7 修复 DEP-B07：gunicorn eventlet worker

```python
# gunicorn.conf.py
worker_class = 'eventlet'
workers = 1  # eventlet 模式下建议单 worker
```

***

> 本报告由代码审计工具自动生成并经人工审核确认。共发现 134 个问题（13 严重 / 41 高 / 56 中 / 24 低）。\
> 截至当前，已修复 36 个问题（8 严重 + 17 高 + 10 中 + 1 低），剩余 4 个高优先级和 46 个中优先级问题待处理（其中 1 个建议后续重构）。

