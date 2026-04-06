# SmartTable Flask 后端 API 文档

## 概述

本文档描述了 SmartTable 多维表格项目的 Flask 后端 RESTful API 接口。

### 基本信息

- **基础URL**: `http://localhost:5000/api`
- **数据格式**: JSON
- **认证方式**: JWT Bearer Token

### 通用响应格式

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... },
  "timestamp": "2025-04-03T10:30:00Z"
}
```

### 分页响应格式

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

---

## 认证模块

### 用户注册

- **URL**: `POST /auth/register`
- **描述**: 注册新用户账号
- **请求体**:

```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "Password123!",
  "nickname": "用户昵称"
}
```

- **响应**: 201 Created

```json
{
  "code": 201,
  "message": "用户注册成功",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "username": "username",
      "nickname": "用户昵称",
      "created_at": "2025-04-03T10:30:00Z"
    }
  }
}
```

### 用户登录

- **URL**: `POST /auth/login`
- **描述**: 用户登录获取访问令牌
- **请求体**:

```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

- **响应**: 200 OK

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "user": { ... }
  }
}
```

### 刷新令牌

- **URL**: `POST /auth/refresh`
- **描述**: 使用刷新令牌获取新的访问令牌
- **请求体**:

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### 用户登出

- **URL**: `POST /auth/logout`
- **描述**: 注销当前用户的令牌
- **认证**: 需要

### 获取当前用户

- **URL**: `GET /auth/me`
- **描述**: 获取当前登录用户信息
- **认证**: 需要

---

## Base 管理模块

### 创建 Base

- **URL**: `POST /bases`
- **描述**: 创建新的多维表格基础
- **认证**: 需要
- **请求体**:

```json
{
  "name": "项目管理系统",
  "description": "用于管理项目进度",
  "icon": "folder",
  "color": "#6366f1"
}
```

### 获取 Base 列表

- **URL**: `GET /bases`
- **描述**: 获取当前用户的所有 Base
- **认证**: 需要
- **查询参数**:
  - `page`: 页码，默认1
  - `per_page`: 每页数量，默认20
  - `include_archived`: 是否包含已归档，默认false

### 获取 Base 详情

- **URL**: `GET /bases/{base_id}`
- **描述**: 获取指定 Base 的详细信息
- **认证**: 需要

### 更新 Base

- **URL**: `PUT /bases/{base_id}`
- **描述**: 更新 Base 信息
- **认证**: 需要 (Owner/Admin)

### 删除 Base

- **URL**: `DELETE /bases/{base_id}`
- **描述**: 删除 Base
- **认证**: 需要 (Owner)

### 归档/取消归档 Base

- **URL**: `PUT /bases/{base_id}/archive`
- **描述**: 归档或取消归档 Base
- **认证**: 需要 (Owner/Admin)

### 成员管理

#### 添加成员

- **URL**: `POST /bases/{base_id}/members`
- **请求体**:

```json
{
  "user_id": "user-uuid",
  "role": "editor"
}
```

#### 更新成员角色

- **URL**: `PUT /bases/{base_id}/members/{member_id}`
- **请求体**:

```json
{
  "role": "admin"
}
```

#### 移除成员

- **URL**: `DELETE /bases/{base_id}/members/{member_id}`

---

## 表格管理模块

### 创建表格

- **URL**: `POST /tables`
- **描述**: 在指定 Base 中创建新表格
- **认证**: 需要
- **请求体**:

```json
{
  "base_id": "base-uuid",
  "name": "任务列表",
  "description": "项目任务跟踪"
}
```

### 获取表格列表

- **URL**: `GET /bases/{base_id}/tables`
- **描述**: 获取 Base 下的所有表格
- **认证**: 需要

### 获取表格详情

- **URL**: `GET /tables/{table_id}`
- **认证**: 需要

### 更新表格

- **URL**: `PUT /tables/{table_id}`
- **认证**: 需要

### 删除表格

- **URL**: `DELETE /tables/{table_id}`
- **认证**: 需要

### 重新排序表格

- **URL**: `PUT /bases/{base_id}/tables/reorder`
- **请求体**:

```json
{
  "table_orders": [
    {"id": "table-1", "order": 1},
    {"id": "table-2", "order": 2}
  ]
}
```

---

## 字段管理模块

### 创建字段

- **URL**: `POST /tables/{table_id}/fields`
- **认证**: 需要
- **请求体**:

```json
{
  "name": "状态",
  "type": "single_select",
  "is_required": true,
  "options": {
    "choices": [
      {"value": "待处理", "color": "blue"},
      {"value": "进行中", "color": "yellow"},
      {"value": "已完成", "color": "green"}
    ]
  }
}
```

**支持的字段类型**:

- `text`: 文本
- `number`: 数字
- `date`: 日期
- `single_select`: 单选
- `multi_select`: 多选
- `checkbox`: 复选框
- `attachment`: 附件
- `link`: 关联记录
- `formula`: 公式
- `lookup`: 查找引用
- `rollup`: 汇总
- `created_time`: 创建时间
- `last_modified_time`: 最后修改时间
- `created_by`: 创建人
- `last_modified_by`: 最后修改人
- `auto_number`: 自动编号
- `barcode`: 条码
- `button`: 按钮
- `rating`: 评分
- `email`: 邮箱
- `phone`: 电话
- `url`: URL

### 获取字段列表

- **URL**: `GET /tables/{table_id}/fields`
- **认证**: 需要

### 更新字段

- **URL**: `PUT /fields/{field_id}`
- **认证**: 需要

### 删除字段

- **URL**: `DELETE /fields/{field_id}`
- **认证**: 需要

### 重新排序字段

- **URL**: `PUT /tables/{table_id}/fields/reorder`

### 获取字段类型列表

- **URL**: `GET /fields/types`
- **描述**: 获取所有支持的字段类型及其配置

---

## 记录管理模块

### 创建记录

- **URL**: `POST /tables/{table_id}/records`
- **认证**: 需要
- **请求体**:

```json
{
  "values": {
    "field-uuid-1": "任务名称",
    "field-uuid-2": "进行中",
    "field-uuid-3": 100
  }
}
```

### 批量创建记录

- **URL**: `POST /tables/{table_id}/records/batch`
- **认证**: 需要
- **请求体**:

```json
{
  "records": [
    {"values": {"field-1": "数据1"}},
    {"values": {"field-1": "数据2"}}
  ]
}
```

### 获取记录列表

- **URL**: `GET /tables/{table_id}/records`
- **认证**: 需要
- **查询参数**:
  - `page`: 页码
  - `per_page`: 每页数量 (最大100)
  - `search`: 搜索关键词

### 获取记录详情

- **URL**: `GET /records/{record_id}`
- **认证**: 需要

### 更新记录

- **URL**: `PUT /records/{record_id}`
- **认证**: 需要

### 批量更新记录

- **URL**: `PUT /records/batch`
- **认证**: 需要
- **请求体**:

```json
{
  "record_ids": ["record-1", "record-2"],
  "values": {
    "field-uuid": "新值"
  }
}
```

### 删除记录

- **URL**: `DELETE /records/{record_id}`
- **认证**: 需要

### 批量删除记录

- **URL**: `DELETE /records/batch`
- **认证**: 需要
- **请求体**:

```json
{
  "record_ids": ["record-1", "record-2"]
}
```

### 计算公式值

- **URL**: `POST /records/{record_id}/compute`
- **描述**: 计算记录的公式字段值
- **认证**: 需要

---

## 视图管理模块

### 创建视图

- **URL**: `POST /tables/{table_id}/views`
- **认证**: 需要
- **请求体**:

```json
{
  "name": "按状态分组",
  "type": "kanban",
  "config": {
    "group_by_field": "status-field-uuid"
  },
  "filters": [
    {"field_id": "priority", "operator": "equals", "value": "高"}
  ],
  "sorts": [
    {"field_id": "created_at", "direction": "desc"}
  ]
}
```

**支持的视图类型**:

- `grid`: 表格视图
- `gallery`: 画廊视图
- `kanban`: 看板视图
- `gantt`: 甘特图视图
- `calendar`: 日历视图
- `form`: 表单视图

### 获取视图列表

- **URL**: `GET /tables/{table_id}/views`
- **认证**: 需要

### 获取视图详情

- **URL**: `GET /views/{view_id}`
- **认证**: 需要

### 更新视图

- **URL**: `PUT /views/{view_id}`
- **认证**: 需要

### 删除视图

- **URL**: `DELETE /views/{view_id}`
- **认证**: 需要

### 复制视图

- **URL**: `POST /views/{view_id}/duplicate`
- **认证**: 需要

### 重新排序视图

- **URL**: `PUT /tables/{table_id}/views/reorder`

### 获取视图类型列表

- **URL**: `GET /views/types`

---

## 仪表盘管理模块

### 创建仪表盘

- **URL**: `POST /bases/{base_id}/dashboards`
- **认证**: 需要
- **请求体**:

```json
{
  "name": "项目概览",
  "layout": "grid",
  "widgets": [
    {
      "type": "chart",
      "title": "任务状态分布",
      "config": { ... }
    }
  ]
}
```

### 获取仪表盘列表

- **URL**: `GET /bases/{base_id}/dashboards`
- **认证**: 需要

### 获取仪表盘详情

- **URL**: `GET /dashboards/{dashboard_id}`
- **认证**: 需要

### 更新仪表盘

- **URL**: `PUT /dashboards/{dashboard_id}`
- **认证**: 需要

### 删除仪表盘

- **URL**: `DELETE /dashboards/{dashboard_id}`
- **认证**: 需要

---

## 附件管理模块

### 上传文件

- **URL**: `POST /attachments/upload`
- **认证**: 需要
- **Content-Type**: `multipart/form-data`
- **请求体**:
  - `file`: 文件数据
  - `record_id`: 关联记录ID（可选）
  - `field_id`: 关联字段ID（可选）

### 下载文件

- **URL**: `GET /attachments/{attachment_id}/download`
- **认证**: 需要

### 删除附件

- **URL**: `DELETE /attachments/{attachment_id}`
- **认证**: 需要

---

## 导入导出模块

### 导入预览

- **URL**: `POST /import/preview`
- **认证**: 需要
- **Content-Type**: `multipart/form-data`
- **请求体**:
  - `file`: Excel/CSV 文件
  - `table_id`: 目标表格ID

### 执行导入

- **URL**: `POST /import/execute`
- **认证**: 需要

### 导出数据

- **URL**: `POST /export`
- **认证**: 需要
- **请求体**:

```json
{
  "table_id": "table-uuid",
  "format": "xlsx",
  "view_id": "view-uuid",
  "field_ids": ["field-1", "field-2"]
}
```

---

## 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

---

## 权限说明

| 角色 | 权限 |
|------|------|
| owner | 拥有所有权限，包括删除 Base |
| admin | 管理 Base 设置和成员，不能删除 Base |
| editor | 创建、编辑、删除记录和视图 |
| commenter | 查看数据，添加评论 |
| viewer | 仅查看数据 |

---

## 限流说明

- 认证接口: 5 次/分钟
- 普通接口: 100 次/分钟
- 批量操作: 10 次/分钟
