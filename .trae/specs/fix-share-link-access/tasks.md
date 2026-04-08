# Tasks

## 第一阶段：后端 API 修改

- [x] **Task 1**: 修改 Base 详情接口支持 share_token
  - [x] Subtask 1.1: 修改 `smarttable-backend/app/routes/bases.py` 中的 `get_base` 路由，支持从查询参数或请求头获取 share_token
  - [x] Subtask 1.2: 在 `smarttable-backend/app/services/base_service.py` 中添加通过 share_token 验证权限并自动添加成员的方法
  - [x] Subtask 1.3: 在 `get_base` 路由中集成 share_token 验证逻辑：如果用户不是成员但提供了有效的 share_token，自动添加用户为成员

## 第二阶段：前端 API Service 修改

- [x] **Task 2**: 修改前端 API Service 支持 shareToken 参数
  - [x] Subtask 2.1: 修改 `smart-table/src/services/api/baseApiService.ts` 中的 `getBase` 方法，增加可选的 `shareToken` 参数
  - [x] Subtask 2.2: 确保 shareToken 通过查询参数或请求头传递给后端

## 第三阶段：前端 Store 修改

- [x] **Task 3**: 修改 baseStore 支持 shareToken 参数
  - [x] Subtask 3.1: 修改 `smart-table/src/stores/baseStore.ts` 中的 `fetchBase` 方法，增加可选的 `shareToken` 参数
  - [x] Subtask 3.2: 将 shareToken 传递给 `baseApiService.getBase`

## 第四阶段：验证测试

- [x] **Task 4**: 验证分享链接访问功能
  - [x] Subtask 4.1: 创建分享链接
  - [x] Subtask 4.2: 通过分享链接访问并点击"进入多维表格"
  - [x] Subtask 4.3: 验证 Base 页面能正常加载，不再返回 403 错误
  - [x] Subtask 4.4: 验证用户被自动添加为 Base 成员

# Task Dependencies

- Task 1 是后端基础，必须先完成
- Task 2 和 Task 3 可以并行开发，都依赖于 Task 1 的接口定义
- Task 4 依赖于所有开发任务完成
