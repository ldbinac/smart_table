# Flask 后端实施规范

## 项目背景

当前 SmartTable 多维表格项目采用纯前端架构，所有数据通过 Dexie 库存储在浏览器的 IndexedDB 中。本项目旨在使用 Python Flask 技术生态实现管理端，将数据存储从 IndexedDB 迁移至后端数据库，通过 RESTful API 接口实现数据的增删改查操作。

## 核心目标

1. 设计并实现 RESTful API 接口，处理表格数据的 CRUD 操作
2. 建立 Flask 后端服务，实现数据验证、权限控制和错误处理
3. 配置 PostgreSQL 数据库，设计合理的数据模型映射多维表格结构
4. 修改前端代码，将 IndexedDB 操作替换为对后端 API 的异步请求
5. 确保数据传输安全性，实现身份认证和数据加密
6. 建立数据备份与恢复机制
7. 完成全面的单元测试和集成测试

---

## 一、技术架构

### 1.1 技术栈选型

| 层级 | 技术选型 | 版本 | 说明 |
|------|----------|------|------|
| **Web 框架** | Flask | 3.0.x | 核心应用框架 |
| **ORM** | SQLAlchemy | 2.0.x | 数据库 ORM |
| **数据库** | PostgreSQL | 16.x | 主数据库 |
| **迁移工具** | Alembic | 1.12.x | 数据库迁移 |
| **认证** | Flask-JWT-Extended | 4.6.x | JWT Token 认证 |
| **数据验证** | Marshmallow | 3.20.x | 数据序列化/验证 |
| **API 文档** | Flasgger | 0.9.x | Swagger 文档 |
| **WebSocket** | Flask-SocketIO | 5.3.x | 实时协作 |
| **任务队列** | Celery | 5.3.x | 异步任务 |
| **缓存** | Redis | 7.x | 数据缓存 |
| **文件存储** | MinIO | 最新 | 对象存储 |
| **WSGI 服务器** | Gunicorn | 21.x | 生产环境服务器 |
| **容器化** | Docker | 最新 | 容器化部署 |

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         前端层 (Vue 3 + TypeScript)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Pinia     │  │  Composables │  │   Axios     │  │   Dexie    │    │
│  │  状态管理   │  │  数据请求   │  │  HTTP 客户端 │  │  离线缓存  │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘    │
│         │                │                │                             │
│         └────────────────┴────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP/HTTPS
┌─────────────────────────────────────────────────────────────────────────┐
│                            网关层 (Nginx)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  负载均衡 │ SSL 终止 │ 静态资源 │ 反向代理 │ 请求限流              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Flask 应用层                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Blueprints │  │  Services   │  │  Middleware │  │ Validators  │    │
│  │   路由模块   │  │   业务逻辑   │  │   中间件    │  │   数据验证   │    │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └─────────────┘    │
│         │                │                                              │
│  ┌──────▼────────────────▼──────┐  ┌─────────────────────────────┐     │
│  │      SQLAlchemy ORM           │  │      Flask-SocketIO         │     │
│  │      数据访问层                │  │      实时协作通信           │     │
│  └──────────────────────────────┘  └─────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL     │      │     Redis       │      │     MinIO       │
│   主数据库        │      │   缓存/会话      │      │   对象存储       │
│                  │      │                  │      │                 │
│ • 用户认证数据    │      │ • Session 存储   │      │ • 附件文件       │
│ • Base/Table     │      │ • API 缓存       │      │ • 缩略图         │
│ • Field/Record   │      │ • 任务队列       │      │ • 备份文件       │
│ • View/Dashboard │      │                  │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## 二、功能需求

### 2.1 用户认证模块

#### 2.1.1 用户注册
- 用户名、邮箱、密码注册
- 密码强度验证（至少8位，包含大小写字母和数字）
- 邮箱格式验证和唯一性检查
- 注册成功后自动登录

#### 2.1.2 用户登录
- 邮箱+密码登录
- JWT Token 认证
- Token 刷新机制
- 登录失败次数限制（5次后锁定15分钟）

#### 2.1.3 用户管理
- 获取当前用户信息
- 更新用户信息（昵称、头像）
- 修改密码
- 退出登录

### 2.2 Base 管理模块

#### 2.2.1 Base CRUD
- 创建 Base（名称、描述、图标、颜色）
- 获取用户的所有 Base 列表
- 获取单个 Base 详情
- 更新 Base 信息
- 删除 Base（级联删除关联数据）
- 收藏/取消收藏 Base

#### 2.2.2 Base 成员管理
- 添加成员（邮箱邀请）
- 移除成员
- 修改成员角色（owner/member/viewer）
- 获取成员列表

### 2.3 Table 管理模块

#### 2.3.1 Table CRUD
- 创建 Table（名称、描述）
- 获取 Base 下的所有 Table
- 获取单个 Table 详情
- 更新 Table 信息
- 删除 Table（级联删除）
- Table 排序（拖拽调整顺序）

#### 2.3.2 Table 统计
- 实时记录数统计
- 字段数统计

### 2.4 Field 管理模块

#### 2.4.1 Field CRUD
- 创建 Field（支持 22 种字段类型）
- 获取 Table 下的所有 Field
- 更新 Field（名称、类型、选项）
- 删除 Field
- 字段排序

#### 2.4.2 字段类型支持
| 字段类型 | 说明 | 额外配置 |
|----------|------|----------|
| TEXT | 文本 | 最大长度 |
| NUMBER | 数字 | 精度、小数位 |
| DATE | 日期 | 格式 |
| SINGLE_SELECT | 单选 | 选项列表 |
| MULTI_SELECT | 多选 | 选项列表 |
| CHECKBOX | 复选框 | - |
| MEMBER | 成员 | - |
| PHONE | 电话 | - |
| EMAIL | 邮箱 | - |
| URL | 链接 | - |
| ATTACHMENT | 附件 | - |
| FORMULA | 公式 | 公式表达式 |
| LINK | 链接 | - |
| LOOKUP | 查找 | 关联字段 |
| CREATED_BY | 创建人 | 系统字段 |
| CREATED_TIME | 创建时间 | 系统字段 |
| UPDATED_BY | 更新人 | 系统字段 |
| UPDATED_TIME | 更新时间 | 系统字段 |
| AUTO_NUMBER | 自动编号 | 格式 |
| RATING | 评分 | 最大值 |
| PROGRESS | 进度 | 最大值 |

### 2.5 Record 管理模块

#### 2.5.1 Record CRUD
- 创建 Record
- 获取 Table 下的所有 Record（分页、筛选、排序）
- 获取单个 Record
- 更新 Record
- 删除 Record
- 批量创建 Record
- 批量更新 Record
- 批量删除 Record

#### 2.5.2 高级查询
- 分页查询（page, page_size）
- 筛选（多字段组合）
- 排序（多字段排序）
- 全文搜索

#### 2.5.3 公式计算
- 公式字段自动计算
- 公式结果缓存
- 批量公式重算

### 2.6 View 管理模块

#### 2.6.1 View CRUD
- 创建 View（支持 6 种视图类型）
- 获取 Table 下的所有 View
- 更新 View
- 删除 View
- 设置默认视图

#### 2.6.2 视图类型
| 视图类型 | 说明 |
|----------|------|
| TABLE | 表格视图 |
| KANBAN | 看板视图 |
| CALENDAR | 日历视图 |
| GANTT | 甘特图视图 |
| FORM | 表单视图 |
| GALLERY | 画廊视图 |

#### 2.6.3 视图配置
- 筛选条件配置
- 排序配置
- 分组配置
- 隐藏字段
- 冻结字段
- 行高设置

### 2.7 Dashboard 管理模块

#### 2.7.1 Dashboard CRUD
- 创建 Dashboard
- 获取 Base 下的所有 Dashboard
- 更新 Dashboard
- 删除 Dashboard

#### 2.7.2 Widget 管理
- 添加 Widget
- 更新 Widget 配置
- 删除 Widget
- Widget 拖拽布局

### 2.8 附件管理模块

#### 2.8.1 文件上传
- 单文件上传
- 批量文件上传
- 分片上传（支持大文件）
- 缩略图生成

#### 2.8.2 文件管理
- 获取文件列表
- 下载文件
- 删除文件
- 获取文件信息

### 2.9 数据导入导出模块

#### 2.9.1 导入功能
- Excel 导入（.xlsx, .xls）
- CSV 导入
- JSON 导入
- 导入预览
- 字段映射

#### 2.9.2 导出功能
- Excel 导出
- CSV 导出
- JSON 导出

---

## 三、API 设计规范

### 3.1 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| POST | /api/auth/refresh | 刷新 Token |
| POST | /api/auth/logout | 退出登录 |
| GET | /api/auth/me | 获取当前用户 |

### 3.2 Base 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/bases | 获取所有 Base |
| POST | /api/bases | 创建 Base |
| GET | /api/bases/:id | 获取单个 Base |
| PUT | /api/bases/:id | 更新 Base |
| DELETE | /api/bases/:id | 删除 Base |
| POST | /api/bases/:id/star | 收藏/取消收藏 |
| GET | /api/bases/:id/members | 获取成员列表 |
| POST | /api/bases/:id/members | 添加成员 |
| DELETE | /api/bases/:id/members/:userId | 移除成员 |

### 3.3 Table 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/bases/:baseId/tables | 获取所有 Table |
| POST | /api/bases/:baseId/tables | 创建 Table |
| GET | /api/tables/:id | 获取单个 Table |
| PUT | /api/tables/:id | 更新 Table |
| DELETE | /api/tables/:id | 删除 Table |
| POST | /api/bases/:baseId/tables/reorder | 批量排序 |

### 3.4 Field 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tables/:tableId/fields | 获取所有 Field |
| POST | /api/tables/:tableId/fields | 创建 Field |
| PUT | /api/fields/:id | 更新 Field |
| DELETE | /api/fields/:id | 删除 Field |
| POST | /api/fields/reorder | 批量排序 |

### 3.5 Record 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tables/:tableId/records | 获取所有 Record |
| POST | /api/tables/:tableId/records | 创建 Record |
| GET | /api/records/:id | 获取单个 Record |
| PUT | /api/records/:id | 更新 Record |
| DELETE | /api/records/:id | 删除 Record |
| POST | /api/tables/:tableId/records/batch | 批量操作 |

### 3.6 View 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tables/:tableId/views | 获取所有 View |
| POST | /api/tables/:tableId/views | 创建 View |
| GET | /api/views/:id | 获取单个 View |
| PUT | /api/views/:id | 更新 View |
| DELETE | /api/views/:id | 删除 View |
| POST | /api/views/:id/set-default | 设置默认 |

### 3.7 Dashboard 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/bases/:baseId/dashboards | 获取所有 Dashboard |
| POST | /api/bases/:baseId/dashboards | 创建 Dashboard |
| GET | /api/dashboards/:id | 获取单个 Dashboard |
| PUT | /api/dashboards/:id | 更新 Dashboard |
| DELETE | /api/dashboards/:id | 删除 Dashboard |

### 3.8 附件接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/attachments/upload | 上传文件 |
| GET | /api/attachments/:id | 获取文件信息 |
| GET | /api/attachments/:id/download | 下载文件 |
| DELETE | /api/attachments/:id | 删除文件 |

### 3.9 导入导出接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/import | 导入数据 |
| GET | /api/import/:taskId | 获取导入进度 |
| POST | /api/export | 导出数据 |
| GET | /api/export/:taskId | 下载导出文件 |

### 3.10 统一响应格式

```json
// 成功响应
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2026-04-03T10:00:00Z"
}

// 错误响应
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  },
  "timestamp": "2026-04-03T10:00:00Z"
}

// 分页响应
{
  "success": true,
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  },
  "timestamp": "2026-04-03T10:00:00Z"
}
```

---

## 四、数据模型设计

### 4.1 用户表 (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| email | VARCHAR(255) | 邮箱，唯一 |
| password | VARCHAR(255) | 密码哈希 |
| name | VARCHAR(255) | 用户名 |
| avatar | VARCHAR(500) | 头像 URL |
| role | ENUM | 角色 |
| status | ENUM | 状态 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.2 Base 表 (bases)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 名称 |
| description | TEXT | 描述 |
| icon | VARCHAR(100) | 图标 |
| color | VARCHAR(50) | 颜色 |
| is_starred | BOOLEAN | 是否收藏 |
| owner_id | UUID | 所有者 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.3 Base 成员表 (base_members)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| base_id | UUID | Base ID |
| user_id | UUID | 用户 ID |
| role | ENUM | 角色 |
| created_at | TIMESTAMP | 创建时间 |

### 4.4 Table 表 (tables)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 名称 |
| description | TEXT | 描述 |
| primary_field_id | UUID | 主字段 ID |
| record_count | INTEGER | 记录数 |
| order | INTEGER | 排序 |
| is_starred | BOOLEAN | 是否收藏 |
| base_id | UUID | Base ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.5 Field 表 (fields)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 名称 |
| type | ENUM | 字段类型 |
| options | JSON | 选项配置 |
| is_primary | BOOLEAN | 是否主字段 |
| is_system | BOOLEAN | 是否系统字段 |
| is_required | BOOLEAN | 是否必填 |
| is_visible | BOOLEAN | 是否可见 |
| default_value | JSON | 默认值 |
| description | TEXT | 描述 |
| order | INTEGER | 排序 |
| table_id | UUID | Table ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.6 Record 表 (records)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| values | JSON | 字段值 |
| table_id | UUID | Table ID |
| created_by_id | UUID | 创建人 ID |
| updated_by_id | UUID | 更新人 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.7 View 表 (views)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 名称 |
| type | ENUM | 视图类型 |
| config | JSON | 视图配置 |
| filters | JSON | 筛选条件 |
| sorts | JSON | 排序配置 |
| group_bys | JSON | 分组配置 |
| hidden_fields | JSON | 隐藏字段 |
| frozen_fields | JSON | 冻结字段 |
| row_height | ENUM | 行高 |
| is_default | BOOLEAN | 是否默认 |
| order | INTEGER | 排序 |
| table_id | UUID | Table ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.8 Dashboard 表 (dashboards)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(255) | 名称 |
| description | VARCHAR(500) | 描述 |
| widgets | JSON | Widget 配置 |
| layout | JSON | 布局配置 |
| layout_type | ENUM | 布局类型 |
| grid_columns | INTEGER | 网格列数 |
| refresh_config | JSON | 刷新配置 |
| is_starred | BOOLEAN | 是否收藏 |
| order | INTEGER | 排序 |
| base_id | UUID | Base ID |
| created_by_id | UUID | 创建人 ID |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 4.9 Attachment 表 (attachments)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(500) | 文件名 |
| original_name | VARCHAR(500) | 原始文件名 |
| size | BIGINT | 文件大小 |
| type | VARCHAR(100) | MIME 类型 |
| file_type | VARCHAR(50) | 文件类型 |
| extension | VARCHAR(20) | 扩展名 |
| storage_key | VARCHAR(500) | 存储键 |
| thumbnail_key | VARCHAR(500) | 缩略图键 |
| record_id | UUID | Record ID |
| field_id | UUID | Field ID |
| table_id | UUID | Table ID |
| base_id | UUID | Base ID |
| created_by_id | UUID | 创建人 ID |
| created_at | TIMESTAMP | 创建时间 |

---

## 五、安全性设计

### 5.1 认证机制

- JWT Token 认证
- Access Token 有效期 30 分钟
- Refresh Token 有效期 7 天
- Token 存储在 HttpOnly Cookie 中
- CSRF 保护

### 5.2 授权机制

- 基于角色的访问控制 (RBAC)
- Base 级别权限：owner、member、viewer
- API 级别权限检查
- 字段级别数据过滤

### 5.3 数据安全

- HTTPS 强制
- 密码 BCrypt 加密
- SQL 注入防护
- XSS 防护
- 输入数据验证

### 5.4 限流保护

- 全局限流：1000 请求/分钟
- 登录限流：5 次/15 分钟
- 上传限流：100 文件/小时

---

## 六、部署架构

### 6.1 开发环境

- Flask 开发服务器
- SQLite 数据库
- 本地 Redis

### 6.2 生产环境

- Gunicorn + Gevent
- PostgreSQL 数据库
- Redis 缓存
- MinIO 对象存储
- Nginx 反向代理
- Docker 容器化

### 6.3 高可用架构

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  负载均衡   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  Flask App  │ │  Flask App  │ │  Flask App  │
    │  Instance 1 │ │  Instance 2 │ │  Instance 3 │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ PostgreSQL   │ │    Redis    │ │    MinIO    │
    │   Primary    │ │   Cluster   │ │   Cluster   │
    └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 七、测试要求

### 7.1 单元测试

- 覆盖率 ≥ 80%
- 每个 Service 方法测试
- 数据验证测试
- 公式计算测试

### 7.2 集成测试

- API 接口测试
- 数据库操作测试
- 认证流程测试
- 文件上传下载测试

### 7.3 性能测试

- API 响应时间 < 200ms
- 并发支持 1000 用户
- 大数据量测试（10万+ 记录）

---

## 八、里程碑与工期

| 阶段 | 工期 | 交付物 |
|------|------|--------|
| 阶段一 | 1 周 | Flask 基础框架、数据库模型、用户认证 |
| 阶段二 | 2 周 | Base/Table/Field CRUD API |
| 阶段三 | 1.5 周 | Record CRUD API、批量操作 |
| 阶段四 | 1 周 | View/Dashboard API |
| 阶段五 | 1 周 | 附件管理、导入导出 |
| 阶段六 | 0.5 周 | 前端对接、测试 |
| 阶段七 | 0.5 周 | 部署上线 |

**总计预计工期：7 周**
