# 多维表格功能实现计划

## 项目概述
基于 Vue 3 + TypeScript + Pinia + Flask 的智能表格系统，采用前后端分离架构

## 已完成功能

### SubTask 2.1.3: 实现多维表格重命名功能 ✅
**状态**: 已完成

**实现方式**:
- Base.vue 侧边栏表格列表支持右键菜单和内联编辑
- 调用 tableStore.updateTable() 更新表格名称
- 后端 API 已支持

**涉及文件**:
- `src/views/Base.vue`
- `src/stores/tableStore.ts`

---

### SubTask 2.1.4: 实现多维表格删除功能 ✅
**状态**: 已完成

**实现方式**:
- Base.vue 侧边栏表格列表支持删除选项
- 添加确认对话框
- 调用 tableStore.deleteTable() 删除表格
- 后端 API 已支持级联删除

**涉及文件**:
- `src/views/Base.vue`
- `src/stores/tableStore.ts`

---

### SubTask 2.1.5: 实现多维表格收藏功能 ✅
**状态**: 已完成

**实现方式**:
- 后端 Base 模型已包含 is_starred 字段
- 前端 Base.vue 中已添加收藏/取消收藏 UI
- 首页 Home.vue 中收藏的多维表排在前面
- API: `POST /api/bases/{id}/star` / `DELETE /api/bases/{id}/star`

**涉及文件**:
- `src/views/Base.vue`
- `src/views/Home.vue`
- `src/stores/baseStore.ts`
- `smarttable-backend/app/routes/bases.py`

---

### SubTask 2.1.6: 实现多维表格搜索功能 ✅
**状态**: 已完成

**实现方式**:
- Home.vue 首页添加搜索输入框
- 搜索逻辑根据表格名称过滤
- 实时显示搜索结果

**涉及文件**:
- `src/views/Home.vue`

---

### SubTask 2.2.6: 实现数据表拖拽排序 ✅
**状态**: 已完成

**实现方式**:
- Base.vue 侧边栏表格列表集成 sortablejs
- 监听拖拽结束事件
- 调用 tableStore.reorderTables() 更新排序

**涉及文件**:
- `src/views/Base.vue`
- `src/stores/tableStore.ts`

---

## v1.1 新增功能实现

### 实时协作功能 ✅
**状态**: 已完成

**实现内容**:
- 后端 Flask-SocketIO 事件处理（连接认证、房间管理、在线状态、单元格锁定）
- 前端 useRealtimeCollaboration composable（WebSocket 连接、房间、锁、冲突解决）
- collaborationStore Pinia 状态管理
- 协作 UI 组件（OnlineUsers、CellEditingIndicator、ConnectionStatusBar、ConflictDialog）
- 可配置启用/禁用（`ENABLE_REALTIME` 环境变量）

**涉及文件**:
- `smarttable-backend/app/routes/socketio_events.py`
- `smarttable-backend/app/services/collaboration_service.py`
- `src/composables/useRealtimeCollaboration.ts`
- `src/stores/collaborationStore.ts`
- `src/services/realtime/socketClient.ts`

---

### 邮件服务系统 ✅
**状态**: 已完成

**实现内容**:
- SMTP 邮件发送服务
- 邮件模板管理（Jinja2 渲染）
- 邮件队列和重试机制
- 邮件日志记录
- 管理界面（模板/日志/统计）
- 默认模板（注册欢迎/密码重置/邮箱验证）

**涉及文件**:
- `smarttable-backend/app/services/email_sender_service.py`
- `smarttable-backend/app/services/email_template_service.py`
- `smarttable-backend/app/services/email_queue_service.py`
- `smarttable-backend/app/services/email_retry_service.py`
- `smarttable-backend/app/services/email_log_service.py`
- `smarttable-backend/app/routes/email.py`
- `src/views/admin/EmailTemplates.vue`
- `src/views/admin/EmailLogs.vue`
- `src/views/admin/EmailStats.vue`

---

### 用户认证系统 ✅
**状态**: 已完成

**实现内容**:
- 注册/登录/登出
- 验证码系统
- 忘记密码/重置密码（邮件通知）
- 邮箱验证
- JWT 令牌管理（访问令牌 + 刷新令牌 + 黑名单）
- 密码强度验证
- 修改密码功能

**涉及文件**:
- `smarttable-backend/app/routes/auth.py`
- `smarttable-backend/app/services/auth_service.py`
- `src/views/auth/Login.vue`
- `src/views/auth/Register.vue`
- `src/views/auth/ForgotPassword.vue`
- `src/views/auth/ResetPassword.vue`
- `src/views/auth/VerifyEmail.vue`
- `src/stores/authStore.ts`

---

### 安全加固 ✅
**状态**: 已完成

**实现内容**:
- XSS 防护（DOMPurify 消毒 + HTML 转义 + CSP 安全头）
- 速率限制（登录/API/上传/查询/写入多级限制）
- 安全响应头（X-Content-Type-Options, X-Frame-Options, HSTS 等）
- 文件上传安全（Magic Number 验证 + 扩展名白名单）
- 异常信息安全（统一异常处理）
- 生产日志安全（Vite 生产构建移除 console.log）
- 内存泄漏修复（多个组件事件监听器清理）

**涉及文件**:
- `smart-table/src/utils/sanitize.ts`
- `smarttable-backend/app/middleware/security_headers.py`
- `smarttable-backend/app/utils/decorators.py`
- `smarttable-backend/app/utils/exception_handler.py`
- `smarttable-backend/app/services/attachment_service.py`
- `smart-table/vite.config.ts`

---

### 仪表盘功能 ✅
**状态**: 已完成

**实现内容**:
- ECharts 图表（柱状图、折线图、饼图）
- KPI 指标卡、时钟、日期、跑马灯组件
- 拖拽布局（网格/自由布局）
- 仪表盘分享（密码/过期时间/访问次数）
- 仪表盘模板

**涉及文件**:
- `src/views/Dashboard.vue`
- `src/views/DashboardShare.vue`
- `src/components/dashboard/`
- `smarttable-backend/app/services/dashboard_service.py`
- `smarttable-backend/app/services/dashboard_share_service.py`

---

### 管理员面板 ✅
**状态**: 已完成

**实现内容**:
- 用户管理（CRUD、角色/状态筛选、批量删除、重置密码）
- 系统配置（含邮件 SMTP 配置）
- 操作日志（含 CSV 导出）
- 邮件管理（模板/日志/统计）

**涉及文件**:
- `src/views/admin/UserManagement.vue`
- `src/views/admin/SystemSettings.vue`
- `src/views/admin/OperationLogs.vue`
- `src/views/admin/EmailTemplates.vue`
- `src/views/admin/EmailLogs.vue`
- `src/views/admin/EmailStats.vue`
- `smarttable-backend/app/routes/admin.py`

---

### Docker 部署 ✅
**状态**: 已完成

**实现内容**:
- 统一 Dockerfile（三阶段构建：前端构建 → 后端依赖 → 生产镜像）
- docker-compose.yml（SQLite 简化版）
- docker-compose.full.yml（PostgreSQL + Redis 完整版）
- Nginx 反向代理配置
- Supervisor 进程管理

**涉及文件**:
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.full.yml`
- `docker/nginx/nginx.conf`
- `docker/supervisor/supervisord.conf`

---

## 待实现功能

### 操作历史 📋
**优先级**: P1

**实现计划**:
1. 后端已有 RecordHistory 模型和 recordHistoryApiService
2. 需要完善前端操作历史查看界面
3. 需要实现版本快照功能

---

### Token 存储安全改造 📋
**优先级**: P1

**实现计划**:
1. Refresh Token 迁移至 HttpOnly + Secure + SameSite Cookie
2. Access Token 仅存储在内存中
3. 修改 Token 刷新逻辑适配新的存储方式

---

### 字段级权限 📋
**优先级**: P2

**实现计划**:
1. 在 Field 模型中添加权限配置
2. 实现字段可见性/可编辑性控制
3. 前端根据权限动态显示/隐藏字段

---

### 移动端适配 📋
**优先级**: P1

**实现计划**:
1. 设计移动端响应式布局
2. 实现移动端表格视图
3. 实现触摸手势支持

---

*文档版本：v2.0*
*最后更新：2026-04-18*
