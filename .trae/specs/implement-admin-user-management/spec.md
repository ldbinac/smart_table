# 超管用户管理系统规范

## Why

当前系统已具备基础的用户认证和权限体系，但缺少面向超级管理员的用户管理功能。需要实现完整的后台管理系统，包括用户管理、系统配置、操作日志、角色权限分配等功能，以满足系统管理和安全审计需求。

## What Changes

* **新增用户管理功能**：用户列表、新增用户、编辑用户、禁用/启用用户、重置密码

* **新增超管特有功能**：系统配置管理、操作日志查看、角色权限分配

* **新增多维表成员管理**：全局用户成员管理界面

* **增强权限系统**：实现超管权限装饰器和路由守卫

* **安全审计功能**：记录所有管理操作日志

### 主要变更点

1. **后端新增**：

   * 用户管理 API 路由（/admin/users）

   * 系统配置管理 API

   * 操作日志记录与查询 API

   * 超管权限装饰器

   * 用户管理前端服务

2. **前端新增**：

   * 用户管理页面（列表、新增、编辑）

   * 系统配置页面

   * 操作日志页面

   * 角色权限管理组件

3. **数据库变更**：

   * 新增操作日志表

   * 新增系统配置表

**BREAKING**: 无破坏性变更，所有新功能向后兼容

## Impact

* **Affected specs**:

  * 用户认证系统（扩展）

  * 权限管理系统（增强）

  * 基础数据管理（新增超管视角）

* **Affected code**:

  * 后端：`app/routes/admin.py`, `app/services/admin_service.py`, `app/models/log.py`

  * 前端：`src/views/admin/`, `src/services/api/adminApiService.ts`, `src/stores/adminStore.ts`

## ADDED Requirements

### Requirement: 用户信息管理

系统 SHALL 提供完整的用户信息查询、新增、编辑、删除功能

#### Scenario: 管理员查看用户列表

* **WHEN** 管理员访问用户管理页面

* **THEN** 系统显示用户列表，包含邮箱、姓名、角色、状态、注册时间等信息

* **AND** 支持分页、搜索、筛选（按角色、状态）

#### Scenario: 新增用户

* **WHEN** 管理员点击"新增用户"

* **THEN** 系统显示用户信息表单

* **AND** 管理员填写邮箱、密码、姓名、角色

* **THEN** 系统创建用户并发送通知邮件（可选）

#### Scenario: 编辑用户资料

* **WHEN** 管理员选择编辑用户

* **THEN** 系统显示用户当前信息

* **AND** 管理员可修改姓名、邮箱、角色、状态

* **THEN** 系统保存更改并记录操作日志

#### Scenario: 禁用/启用用户账号

* **WHEN** 管理员禁用用户账号

* **THEN** 系统更新用户状态为 SUSPENDED

* **AND** 用户无法再登录系统

* **AND** 系统记录操作日志

#### Scenario: 重置用户密码

* **WHEN** 管理员重置用户密码

* **THEN** 系统生成临时密码

* **AND** 临时密码发送给用户（邮件或站内消息）

* **AND** 用户首次登录需修改密码

### Requirement: 系统配置管理

系统 SHALL 提供系统级别的配置管理功能

#### Scenario: 查看系统配置

* **WHEN** 管理员访问系统配置页面

* **THEN** 系统显示所有可配置项

* **AND** 配置项按类别分组（基础配置、安全配置、邮件配置等）

#### Scenario: 修改系统配置

* **WHEN** 管理员修改配置项

* **THEN** 系统验证配置值有效性

* **AND** 保存配置到数据库

* **AND** 记录操作日志

### Requirement: 操作日志查看

系统 SHALL 记录并展示所有管理操作日志

#### Scenario: 查看操作日志

* **WHEN** 管理员访问操作日志页面

* **THEN** 系统显示操作日志列表

* **AND** 包含操作人、操作时间、操作类型、操作对象、IP 地址

* **AND** 支持按时间范围、操作人、操作类型筛选

#### Scenario: 导出操作日志

* **WHEN** 管理员导出操作日志

* **THEN** 系统生成 CSV 或 Excel 文件

* **AND** 包含筛选条件下的所有日志记录

### Requirement: 角色权限分配

系统 SHALL 提供角色和权限的分配管理

#### Scenario: 分配用户角色

* **WHEN** 管理员分配用户角色

* **THEN** 系统显示可选角色列表（OWNER, ADMIN, WORKSPACE\_ADMIN, EDITOR, COMMENTER, VIEWER）

* **AND** 管理员选择角色并确认

* **THEN** 系统更新用户角色并记录日志

#### Scenario: 管理 Base 成员

* **WHEN** 管理员管理多维表成员

* **THEN** 系统显示 Base 的成员列表

* **AND** 管理员可添加/移除成员、修改成员角色

* **THEN** 系统更新成员关系并记录日志

### Requirement: 超管权限校验

系统 SHALL 实现严格的超管权限校验机制

#### Scenario: 访问管理页面

* **WHEN** 用户访问管理员专属页面

* **THEN** 系统检查用户角色是否为 ADMIN 或 WORKSPACE\_ADMIN

* **AND** 非管理员用户被重定向到 403 页面

#### Scenario: 执行管理操作

* **WHEN** 用户调用管理员 API

* **THEN** 系统验证用户令牌和角色

* **AND** 权限不足返回 403 错误

## MODIFIED Requirements

### Requirement: 用户模型扩展

在 User 模型中增加密码相关字段：

* `must_change_password`: Boolean，标记用户首次登录是否需要修改密码

* `password_changed_at`: DateTime，记录密码最后修改时间

### Requirement: AuthService 增强

AuthService 需要增加以下方法：

* `create_user()`: 管理员创建用户

* `suspend_user()`: 禁用用户账号

* `activate_user()`: 启用用户账号

* `reset_password()`: 重置用户密码

* `get_all_users()`: 获取所有用户列表（分页）

### Requirement: 权限装饰器

增强 `admin_required` 装饰器，支持：

* 记录所有管理操作到日志

* 支持更细粒度的权限控制（如：用户管理权限、系统配置权限）

## REMOVED Requirements

无

## Security Considerations

1. **密码安全**：

   * 管理员重置的密码必须为临时密码，首次登录强制修改

   * 密码策略：最少 8 位，包含大小写字母、数字、特殊字符

2. **操作审计**：

   * 所有管理操作必须记录日志

   * 日志包含：操作人、时间、IP、操作类型、操作对象、变更内容

3. **权限隔离**：

   * 超管功能必须有权限装饰器保护

   * 前端路由必须有守卫保护

4. **数据安全**：

   * 敏感操作（如删除用户）需要二次确认

   * 批量操作需要限制数量

## API Design

### 用户管理 API

```
GET    /api/admin/users              # 获取用户列表（分页、筛选）
POST   /api/admin/users              # 创建用户
GET    /api/admin/users/:id          # 获取用户详情
PUT    /api/admin/users/:id          # 更新用户信息
DELETE /api/admin/users/:id          # 删除用户
PUT    /api/admin/users/:id/status   # 更新用户状态（禁用/启用）
POST   /api/admin/users/:id/reset-password  # 重置用户密码
```

### 系统配置 API

```
GET    /api/admin/settings           # 获取系统配置
PUT    /api/admin/settings           # 更新系统配置
```

### 操作日志 API

```
GET    /api/admin/operation-logs     # 获取操作日志列表（分页、筛选）
GET    /api/admin/operation-logs/export  # 导出操作日志
```

### 权限管理 API

```
GET    /api/admin/roles              # 获取所有角色
GET    /api/admin/permissions        # 获取所有权限
POST   /api/admin/users/:id/roles    # 分配用户角色
```

