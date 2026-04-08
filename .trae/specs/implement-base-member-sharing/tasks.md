# Tasks

## 第一阶段：后端数据库和模型

- [x] **Task 1**: 创建数据库模型 - BaseMember 和 BaseShare
  - [x] Subtask 1.1: 在 `models.py` 中定义 BaseMember 模型
  - [x] Subtask 1.2: 在 `models.py` 中定义 BaseShare 模型
  - [x] Subtask 1.3: 创建数据库迁移脚本
  - [x] Subtask 1.4: 执行迁移创建表

- [x] **Task 2**: 实现成员管理后端 API
  - [x] Subtask 2.1: 实现获取 Base 成员列表接口 `GET /bases/{base_id}/members`
  - [x] Subtask 2.2: 实现添加成员接口 `POST /bases/{base_id}/members`
  - [x] Subtask 2.3: 实现更新成员角色接口 `PUT /bases/{base_id}/members/{member_id}`
  - [x] Subtask 2.4: 实现移除成员接口 `DELETE /bases/{base_id}/members/{member_id}`
  - [x] Subtask 2.5: 添加权限验证装饰器

- [x] **Task 3**: 实现分享链接后端 API
  - [x] Subtask 3.1: 实现创建分享接口 `POST /bases/{base_id}/shares`
  - [x] Subtask 3.2: 实现获取分享列表接口 `GET /bases/{base_id}/shares`
  - [x] Subtask 3.3: 实现删除分享接口 `DELETE /shares/{share_id}`
  - [x] Subtask 3.4: 实现分享访问接口 `GET /share/{share_token}`

## 第二阶段：后端权限验证

- [x] **Task 4**: 增强权限验证逻辑
  - [x] Subtask 4.1: 实现 Base 访问权限验证函数
  - [x] Subtask 4.2: 实现分享链接权限验证
  - [x] Subtask 4.3: 在现有 Base 接口中添加权限检查
  - [x] Subtask 4.4: 实现"我分享的"和"分享给我的"数据查询接口

## 第三阶段：前端状态管理

- [x] **Task 5**: 实现前端 Store
  - [x] Subtask 5.1: 在 baseStore 中添加成员管理相关 state 和 actions
  - [x] Subtask 5.2: 在 baseStore 中添加分享管理相关 state 和 actions
  - [x] Subtask 5.3: 实现分享链接访问的权限缓存

## 第四阶段：前端 UI 组件

- [x] **Task 6**: 首页菜单扩展
  - [x] Subtask 6.1: 在 Home.vue 中添加"我分享的"菜单项
  - [x] Subtask 6.2: 在 Home.vue 中添加"分享给我的"菜单项
  - [x] Subtask 6.3: 实现两个菜单的数据加载逻辑
  - [x] Subtask 6.4: 实现菜单项点击跳转

- [x] **Task 7**: 成员管理 UI
  - [x] Subtask 7.1: 在 BaseDetail.vue 中添加成员管理 Tab
  - [x] Subtask 7.2: 创建 MemberList 组件展示成员列表
  - [x] Subtask 7.3: 创建 AddMemberDialog 组件
  - [x] Subtask 7.4: 实现成员角色选择和更新 UI
  - [x] Subtask 7.5: 实现移除成员确认对话框

- [x] **Task 8**: 分享功能 UI
  - [x] Subtask 8.1: 创建 ShareDialog 组件
  - [x] Subtask 8.2: 实现分享链接生成和展示
  - [x] Subtask 8.3: 实现分享权限选择（编辑/查看）
  - [x] Subtask 8.4: 实现分享列表展示和管理
  - [x] Subtask 8.5: 实现一键复制链接功能

## 第五阶段：集成测试和优化

- [x] **Task 9**: 集成测试
  - [x] Subtask 9.1: 测试成员管理完整流程
  - [x] Subtask 9.2: 测试分享链接生成和访问
  - [x] Subtask 9.3: 测试权限控制有效性
  - [x] Subtask 9.4: 测试首页菜单数据加载

- [ ] **Task 10**: 优化和文档
  - [ ] Subtask 10.1: 性能优化（缓存、批量查询）
  - [ ] Subtask 10.2: 错误处理增强
  - [ ] Subtask 10.3: 编写 API 使用文档
  - [ ] Subtask 10.4: 编写用户操作指南

# Task Dependencies

- Task 1 是其他所有任务的基础，必须最先完成
- Task 2 和 Task 3 可以并行开发
- Task 4 依赖于 Task 2 和 Task 3 完成
- Task 5 可以在 Task 2、Task 3 进行到一半时开始（接口定义完成后）
- Task 6、Task 7、Task 8 依赖于 Task 4 和 Task 5 完成
- Task 9 依赖于所有开发任务完成
- Task 10 是最后的优化和文档工作
