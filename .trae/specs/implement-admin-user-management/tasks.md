# Tasks

## Phase 1: 数据库模型和基础服务

- [x] Task 1: 创建数据库模型
  - [x] SubTask 1.1: 创建 OperationLog 模型（操作日志）
  - [x] SubTask 1.2: 创建 SystemConfig 模型（系统配置）
  - [x] SubTask 1.3: 扩展 User 模型（添加密码相关字段）
  - [x] SubTask 1.4: 创建数据库迁移脚本

- [x] Task 2: 实现后端服务层
  - [x] SubTask 2.1: 创建 AdminService 基础服务类
  - [x] SubTask 2.2: 实现用户管理方法（CRUD、状态管理、密码重置）
  - [x] SubTask 2.3: 实现操作日志记录方法
  - [x] SubTask 2.4: 实现系统配置管理方法

## Phase 2: 后端 API 路由

- [x] Task 3: 实现用户管理 API
  - [x] SubTask 3.1: 创建 admin.py 路由文件
  - [x] SubTask 3.2: 实现 GET /api/admin/users（用户列表）
  - [x] SubTask 3.3: 实现 POST /api/admin/users（创建用户）
  - [x] SubTask 3.4: 实现 GET/PUT/DELETE /api/admin/users/:id
  - [x] SubTask 3.5: 实现 PUT /api/admin/users/:id/status（状态管理）
  - [x] SubTask 3.6: 实现 POST /api/admin/users/:id/reset-password（重置密码）

- [x] Task 4: 实现系统管理 API
  - [x] SubTask 4.1: 实现 GET/PUT /api/admin/settings（系统配置）
  - [x] SubTask 4.2: 实现 GET /api/admin/operation-logs（操作日志）
  - [x] SubTask 4.3: 实现 GET /api/admin/operation-logs/export（导出日志）
  - [x] SubTask 4.4: 实现 GET /api/admin/roles（角色列表）

## Phase 3: 权限和安全

- [x] Task 5: 增强权限系统
  - [x] SubTask 5.1: 增强 admin_required 装饰器（支持日志记录）
  - [x] SubTask 5.2: 创建 operation_log 装饰器（自动记录操作）
  - [x] SubTask 5.3: 实现 IP 地址获取工具
  - [x] SubTask 5.4: 实现请求信息捕获工具

## Phase 4: 前端服务层

- [x] Task 6: 创建前端 API 服务
  - [x] SubTask 6.1: 创建 adminApiService.ts
  - [x] SubTask 6.2: 实现用户管理 API 调用方法
  - [x] SubTask 6.3: 实现系统配置 API 调用方法
  - [x] SubTask 6.4: 实现操作日志 API 调用方法

- [x] Task 7: 创建前端状态管理
  - [x] SubTask 7.1: 创建 adminStore.ts
  - [x] SubTask 7.2: 实现用户管理状态
  - [x] SubTask 7.3: 实现系统配置状态
  - [x] SubTask 7.4: 实现操作日志状态

## Phase 5: 前端页面和组件

- [x] Task 8: 创建用户管理页面
  - [x] SubTask 8.1: 创建 UserManagement.vue（用户列表页面）
  - [x] SubTask 8.2: 创建 UserDialog.vue（新增/编辑用户对话框）
  - [x] SubTask 8.3: 创建 ResetPasswordDialog.vue（重置密码对话框）
  - [x] SubTask 8.4: 实现用户列表表格（分页、搜索、筛选）

- [x] Task 9: 创建系统管理页面
  - [x] SubTask 9.1: 创建 SystemSettings.vue（系统配置页面）
  - [x] SubTask 9.2: 创建 OperationLogs.vue（操作日志页面）
  - [x] SubTask 9.3: 创建 ConfigSection.vue（配置分组组件）

- [x] Task 10: 路由和权限守卫
  - [x] SubTask 10.1: 添加管理员路由配置
  - [x] SubTask 10.2: 实现 adminGuard 路由守卫
  - [x] SubTask 10.3: 在路由中应用权限守卫
  - [x] SubTask 10.4: 创建 403 无权访问页面

## Phase 6: 集成和测试

- [x] Task 11: 系统集成
  - [x] SubTask 11.1: 在应用初始化中注册 admin 路由
  - [x] SubTask 11.2: 在导航菜单中添加管理员入口
  - [x] SubTask 11.3: 实现管理员菜单权限控制
  - [x] SubTask 11.4: 集成到现有认证流程

- [x] Task 12: 测试和文档
  - [x] SubTask 12.1: 编写后端 API 单元测试
  - [x] SubTask 12.2: 编写服务层单元测试
  - [x] SubTask 12.3: 测试前端功能
  - [x] SubTask 12.4: 编写 API 文档
  - [x] SubTask 12.5: 编写用户使用说明

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 2]
- [Task 5] depends on [Task 2]
- [Task 6] depends on [Task 3]
- [Task 7] depends on [Task 6]
- [Task 8] depends on [Task 6, Task 7]
- [Task 9] depends on [Task 6, Task 7]
- [Task 10] depends on [Task 8, Task 9]
- [Task 11] depends on [Task 10]
- [Task 12] depends on [Task 11]

# Implementation Notes

1. **优先级**：
   - Phase 1-3（后端）优先实现
   - Phase 4-5（前端）随后实现
   - Phase 6（集成测试）最后完成

2. **并行开发**：
   - Task 1 和 Task 2 可部分并行
   - Task 6 和 Task 7 可并行
   - Task 8 和 Task 9 可并行

3. **关键点**：
   - 权限装饰器必须严格测试
   - 操作日志必须记录完整
   - 密码重置流程必须安全
