# 数据表单分享链接提交接口实施计划

## 1. 需求概述

设计并实现一个专门用于处理数据表单分享链接提交的新接口，与常规视图数据提交接口区分开，支持无需用户登录即可提交数据的场景。

## 2. 现有系统分析

### 2.1 现有记录创建接口

* **路径**: `/api/tables/<table_id>/records`

* **方法**: POST

* **认证**: 需要 JWT 登录

* **权限**: 需要 EDITOR 角色

* **文件**: `app/routes/records.py`

### 2.2 现有分享系统

* **Base 分享**: `BaseShare` 模型 (`app/models/base_share.py`)

* **仪表盘分享**: `DashboardShare` 模型 (`app/models/dashboard_share.py`)

* **分享服务**: `ShareService` (`app/services/share_service.py`)

### 2.3 关键发现

* 系统已有 Base 分享和仪表盘分享功能

* 缺少专门的"表单分享"功能（允许匿名用户提交数据）

* 需要新建模型来存储表单分享配置

## 3. 设计方案

### 3.1 数据库模型设计

#### 3.1.1 FormShare 模型（新增）

```python
class FormShare(db.Model):
    """表单分享配置表"""
    - id: UUID 主键
    - table_id: 关联的表格 ID
    - share_token: 分享令牌
    - created_by: 创建者用户 ID
    - is_active: 是否激活
    - allow_anonymous: 是否允许匿名提交
    - require_captcha: 是否需要验证码
    - expires_at: 过期时间（可选）
    - max_submissions: 最大提交次数（可选）
    - current_submissions: 当前提交次数
    - allowed_fields: 允许提交的字段列表（JSON）
    - created_at: 创建时间
    - updated_at: 更新时间
```

#### 3.1.2 FormSubmission 模型（新增）

```python
class FormSubmission(db.Model):
    """表单提交记录表"""
    - id: UUID 主键
    - form_share_id: 关联的表单分享 ID
    - record_id: 创建的记录 ID
    - submitter_ip: 提交者 IP
    - submitter_user_agent: 提交者 User-Agent
    - submitter_info: 提交者信息（如邮箱、姓名等，JSON）
    - submitted_at: 提交时间
```

### 3.2 API 端点设计

#### 3.2.1 表单分享管理接口（需认证）

| 方法     | 路径                                   | 描述          |
| ------ | ------------------------------------ | ----------- |
| POST   | `/api/tables/<table_id>/form-shares` | 创建表单分享      |
| GET    | `/api/tables/<table_id>/form-shares` | 获取表格的表单分享列表 |
| GET    | `/api/form-shares/<share_id>`        | 获取表单分享详情    |
| PUT    | `/api/form-shares/<share_id>`        | 更新表单分享配置    |
| DELETE | `/api/form-shares/<share_id>`        | 删除表单分享      |

#### 3.2.2 公开表单提交接口（无需认证）

| 方法   | 路径                                | 描述           |
| ---- | --------------------------------- | ------------ |
| GET  | `/api/form-shares/<token>/schema` | 获取表单结构（字段定义） |
| POST | `/api/form-shares/<token>/submit` | 提交表单数据       |

### 3.3 服务层设计

#### 3.3.1 FormShareService（新增）

```python
class FormShareService:
    - create_form_share(table_id, user_id, config)  # 创建表单分享
    - get_form_share_by_token(token)  # 通过令牌获取
    - validate_form_share(token)  # 验证表单分享有效性
    - submit_form_data(token, data, client_info)  # 提交表单数据
    - get_form_schema(token)  # 获取表单结构
    - update_form_share(share_id, user_id, data)  # 更新配置
    - delete_form_share(share_id, user_id)  # 删除
```

### 3.4 权限控制机制

#### 3.4.1 表单分享创建权限

* 需要表格的 EDITOR 或更高权限

* 需要用户已登录

#### 3.4.2 表单提交权限

* 无需登录（如果 allow\_anonymous=True）

* 检查表单分享是否激活

* 检查表单分享是否过期

* 检查提交次数是否超过限制

* 检查验证码（如果 require\_captcha=True）

### 3.5 数据验证逻辑

#### 3.5.1 表单结构验证

* 验证表格是否存在

* 验证字段是否存在且允许提交

* 验证必填字段

* 验证字段类型和格式

#### 3.5.2 数据格式验证

* 根据字段类型验证数据

* 验证选项字段的值是否在允许范围内

* 验证数字字段的范围

* 验证日期字段的格式

### 3.6 错误处理机制

| 错误场景     | HTTP 状态码 | 错误信息          |
| -------- | -------- | ------------- |
| 表单分享不存在  | 404      | 表单分享不存在       |
| 表单分享未激活  | 403      | 该表单分享已失效      |
| 表单分享已过期  | 403      | 该表单分享已过期      |
| 提交次数已达上限 | 403      | 提交次数已达上限      |
| 数据验证失败   | 400      | 数据验证失败，具体错误信息 |
| 验证码错误    | 400      | 验证码错误或已过期     |
| 服务器内部错误  | 500      | 提交失败，请稍后重试    |

### 3.7 日志记录

#### 3.7.1 需要记录的日志

* 表单分享创建/更新/删除

* 表单提交成功/失败

* 表单验证失败详情

* 异常错误信息

#### 3.7.2 日志内容

* 操作类型

* 表单分享 ID

* 提交者 IP

* 提交者 User-Agent

* 提交数据摘要（脱敏）

* 错误信息（如有）

## 4. 实施步骤

### 步骤 1: 创建数据库迁移脚本

* 创建 `FormShare` 模型

* 创建 `FormSubmission` 模型

* 生成 Alembic 迁移脚本

### 步骤 2: 创建服务层

* 创建 `app/services/form_share_service.py`

* 实现表单分享 CRUD 操作

* 实现表单提交逻辑

* 实现数据验证逻辑

### 步骤 3: 创建路由层

* 创建 `app/routes/form_shares.py`

* 实现管理接口（需认证）

* 实现公开接口（无需认证）

### 步骤 4: 注册路由

* 在应用初始化中注册新路由

### 步骤 5: 添加验证码支持（可选）

* 集成验证码生成和验证

### 步骤 6: 测试

* 单元测试

* 集成测试

## 5. 文件清单

### 5.1 新建文件

1. `app/models/form_share.py` - 表单分享模型
2. `app/models/form_submission.py` - 表单提交记录模型
3. `app/services/form_share_service.py` - 表单分享服务
4. `app/routes/form_shares.py` - 表单分享路由
5. `migrations/versions/xxx_add_form_share_tables.py` - 数据库迁移

### 5.2 修改文件

1. `app/models/__init__.py` - 导出新模型
2. `app/services/__init__.py` - 导出新服务
3. `app/__init__.py` - 注册新路由

## 6. API 详细规范

### 6.1 创建表单分享

```http
POST /api/tables/{table_id}/form-shares
Authorization: Bearer {token}

Request:
{
    "allow_anonymous": true,
    "require_captcha": false,
    "expires_at": 1715500800,
    "max_submissions": 100,
    "allowed_fields": ["field_id_1", "field_id_2"]
}

Response:
{
    "success": true,
    "data": {
        "id": "uuid",
        "share_token": "abc123...",
        "share_url": "http://.../form/abc123...",
        ...
    }
}
```

### 6.2 获取表单结构

```http
GET /api/form-shares/{token}/schema

Response:
{
    "success": true,
    "data": {
        "table_id": "uuid",
        "table_name": "表格名称",
        "fields": [
            {
                "id": "field_id",
                "name": "字段名称",
                "type": "text",
                "required": true,
                "options": {...}
            }
        ]
    }
}
```

### 6.3 提交表单数据

```http
POST /api/form-shares/{token}/submit

Request:
{
    "values": {
        "field_id_1": "值1",
        "field_id_2": "值2"
    },
    "submitter_info": {
        "email": "user@example.com",
        "name": "用户名"
    },
    "captcha": "验证码"
}

Response:
{
    "success": true,
    "data": {
        "record_id": "uuid",
        "submitted_at": "2024-01-01T00:00:00Z"
    },
    "message": "提交成功"
}
```

## 7. 安全考虑

1. **速率限制**: 对表单提交接口实施 IP 级别的速率限制
2. **验证码**: 支持图形验证码防止机器人攻击
3. **字段白名单**: 只允许提交配置的字段，防止注入额外字段
4. **数据脱敏**: 日志中不记录敏感字段值
5. **提交次数限制**: 防止单个表单被滥用

## 8. 与现有系统集成

1. **数据一致性**: 使用现有 `RecordService` 创建记录，确保数据一致性
2. **权限继承**: 复用现有的权限检查机制
3. **日志系统**: 使用现有的 `OperationLog` 记录关键操作

