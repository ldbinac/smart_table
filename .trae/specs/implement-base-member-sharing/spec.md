# Base 成员管理与分享链接功能规格说明

## Why

当前 SmartTable 系统缺少 Base 级别的成员管理和分享功能，用户无法协作管理多维表格。需要实现完整的成员权限管理、分享链接生成与访问控制机制，以支持团队协作场景。

## What Changes

### 新增功能模块

- **成员管理**：Base 所有者可添加/移除成员、调整成员角色权限
- **分享链接**：生成带权限控制的分享链接，支持"可编辑"和"仅查看"两种权限
- **权限验证**：通过分享链接访问时的权限验证与控制
- **首页菜单**：新增"我分享的"和"分享给我的"菜单项

### 数据库变更

- **新增 base_members 表**：存储 Base 成员关系和角色
- **新增 base_shares 表**：存储分享链接和权限配置

### 后端 API 变更

- **新增成员管理接口**：添加成员、更新角色、移除成员、获取成员列表
- **新增分享链接接口**：创建分享、获取分享列表、删除分享
- **新增分享访问接口**：通过分享链接访问 Base 的验证和授权

### 前端页面变更

- **首页导航**：新增"我分享的"和"分享给我的"菜单项
- **成员管理页面**：Base 详情中增加成员管理 Tab
- **分享对话框**：生成和管理分享链接的 UI

## Impact

### 受影响的后端文件

- `smarttable-backend/models.py` - 新增 Member 和 Share 模型
- `smarttable-backend/routes/base_routes.py` - 新增成员和分享路由
- `smarttable-backend/routes/share_routes.py` - 新增分享访问路由
- `smarttable-backend/auth.py` - 增强权限验证逻辑

### 受影响的前端文件

- `smart-table/src/views/Home.vue` - 新增菜单项
- `smart-table/src/views/BaseDetail.vue` - 新增成员管理 Tab
- `smart-table/src/components/ShareDialog.vue` - 新增分享对话框组件
- `smart-table/src/stores/baseStore.ts` - 新增成员和分享相关 store

## ADDED Requirements

### Requirement: 成员管理功能

系统 SHALL 提供 Base 成员管理功能，允许 Base 所有者管理成员和权限。

#### Scenario: 查看成员列表
- **WHEN** Base 所有者或管理员打开 Base 详情
- **THEN** 可查看当前所有成员列表，包括头像、昵称、角色、加入时间

#### Scenario: 添加成员
- **WHEN** Base 所有者点击"添加成员"
- **THEN** 可通过用户邮箱或用户名搜索并添加用户
- **AND** 可为新成员设置角色（admin、editor、commenter、viewer）

#### Scenario: 更新成员角色
- **WHEN** Base 所有者或管理员修改成员角色
- **THEN** 成员权限立即生效
- **AND** 不能修改所有者的角色

#### Scenario: 移除成员
- **WHEN** Base 所有者移除成员
- **THEN** 该成员失去对该 Base 的所有访问权限

### Requirement: 分享链接功能

系统 SHALL 提供安全的分享链接生成和管理机制。

#### Scenario: 创建分享链接
- **WHEN** Base 所有者或管理员创建分享
- **THEN** 生成唯一的分享链接（UUID）
- **AND** 可设置权限级别（edit 或 view）
- **AND** 可设置有效期（可选）

#### Scenario: 查看分享列表
- **WHEN** 用户查看 Base 的分享列表
- **THEN** 显示所有活跃的分享链接
- **AND** 显示每个分享的权限、创建时间、访问次数

#### Scenario: 删除分享链接
- **WHEN** 用户删除分享链接
- **THEN** 该链接立即失效
- **AND** 无法再通过该链接访问 Base

### Requirement: 分享链接访问控制

系统 SHALL 对通过分享链接的访问进行权限验证和控制。

#### Scenario: 未登录用户访问
- **WHEN** 未登录用户访问分享链接
- **THEN** 提示需要登录
- **AND** 登录后自动跳转到分享的 Base

#### Scenario: 登录用户访问
- **WHEN** 登录用户访问分享链接
- **THEN** 验证分享链接有效性
- **AND** 授予对应的访问权限（编辑或仅查看）
- **AND** 在 Base 列表中自动添加该 Base

#### Scenario: 权限控制
- **WHEN** 用户通过分享链接访问 Base
- **THEN** 编辑权限用户可修改记录和视图
- **AND** 仅查看用户只能查看数据，不能修改

### Requirement: 首页菜单扩展

系统 SHALL 在首页提供"我分享的"和"分享给我的"菜单项。

#### Scenario: 我分享的
- **WHEN** 用户点击"我分享的"菜单
- **THEN** 展示该用户创建的所有分享记录
- **AND** 显示每个分享对应的 Base 信息、权限、访问次数
- **AND** 点击可跳转到对应 Base

#### Scenario: 分享给我的
- **WHEN** 用户点击"分享给我的"菜单
- **THEN** 展示其他用户分享给该用户的所有 Base
- **AND** 显示 Base 信息、分享者、权限级别
- **AND** 点击可跳转到对应 Base，并保持正确的权限控制

### Requirement: 数据库模型

#### base_members 表
系统 SHALL 创建 base_members 表存储成员关系：
- id: UUID 主键
- base_id: 外键关联 bases 表
- user_id: 外键关联 users 表
- role: 角色（owner/admin/editor/commenter/viewer）
- created_at: 创建时间
- created_by: 添加该成员的用户 ID
- UNIQUE(base_id, user_id)

#### base_shares 表
系统 SHALL 创建 base_shares 表存储分享信息：
- id: UUID 主键
- share_token: 唯一分享令牌（UUID）
- base_id: 外键关联 bases 表
- created_by: 创建分享的用户 ID
- permission: 权限级别（edit/view）
- expires_at: 过期时间（可选）
- access_count: 访问次数
- created_at: 创建时间

## MODIFIED Requirements

### Requirement: Base 权限验证

系统 SHALL 在所有 Base 操作前验证用户权限：
- **读取 Base**：用户是成员或有有效分享链接
- **写入 Base**：用户角色为 editor 及以上
- **管理成员**：用户角色为 owner 或 admin
- **删除 Base**：用户角色为 owner

## REMOVED Requirements

无
