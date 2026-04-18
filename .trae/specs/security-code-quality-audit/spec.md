# SmartTable 安全与代码质量审计 Spec

## Why

当前 SmartTable 项目存在多项安全隐患和代码质量问题，包括 XSS 漏洞、Token 存储不安全、异常信息泄露、内存泄漏、密码验证绕过等。需对前后端进行全面系统性扫描，识别并修复所有安全问题、代码错误和程序漏洞，确保系统在生产环境中的安全性和稳定性。

## What Changes

### 前端安全修复
- 修复 v-html 渲染用户输入导致的 XSS 风险（EmailTemplates.vue）
- 审计并加固 innerHTML 使用点（Dashboard.vue、DashboardShare.vue 共 38 处）
- 将 Refresh Token 迁移到 HttpOnly Cookie 存储
- 清理生产代码中保留的 console.log 调试输出（20+ 处）
- 修复事件监听器未清理导致的内存泄漏（EmailStats.vue、Home.vue、GanttView.vue）
- 减少 TypeScript `any` 类型使用（82 处）

### 后端安全修复
- 修复 reset-password 路由绕过密码强度 Schema 验证的问题
- 过滤服务层异常信息，不再将 `str(e)` 直接返回客户端（50+ 处）
- 添加文件上传内容验证（Magic Number / MIME Type），对 SVG 文件进行消毒处理
- 添加全局 API 速率限制
- 添加安全响应头（CSP、HSTS、X-Frame-Options 等）

### 配置安全加固
- **BREAKING** 移除 DevelopmentConfig 中的硬编码弱密钥 fallback，改为启动时强制检查
- 确保 .env.example 中不包含弱默认密码
- 确保生产环境不会意外启用 DEBUG 模式

## Impact

- Affected specs: comprehensive-system-check（功能完整性检查）
- Affected code:
  - 前端: `src/utils/auth/token.ts`, `src/views/admin/EmailTemplates.vue`, `src/views/Dashboard.vue`, `src/views/DashboardShare.vue`, `src/views/Home.vue`, `src/views/admin/EmailStats.vue`, `src/components/views/GanttView/GanttView.vue`, `src/stores/theme.ts`, `src/api/config.ts`, `src/composables/useRealtimeCollaboration.ts`, `src/stores/adminStore.ts`
  - 后端: `app/config.py`, `app/routes/auth.py`, `app/services/attachment_service.py`, `app/services/link_service.py`, `app/errors/handlers.py`, `app/extensions.py`, `app/utils/decorators.py`
  - 配置: `.env.example`, `.env.full.example`, `smarttable-backend/.env.example`

## ADDED Requirements

### Requirement: XSS 防护加固

系统 SHALL 对所有用户可控的 HTML 渲染进行安全处理，防止 XSS 攻击。

#### Scenario: v-html 渲染邮件模板
- **WHEN** 管理员编辑邮件 HTML 模板
- **THEN** 系统 SHALL 对模板内容进行 DOMPurify 消毒处理后再渲染
- **AND** 禁止执行模板中的 `<script>` 标签和事件处理器

#### Scenario: innerHTML 构建仪表盘组件
- **WHEN** 使用 innerHTML 构建仪表盘组件
- **THEN** 所有用户可控的插值点 SHALL 经过 HTML 转义处理
- **AND** 不存在未转义的用户输入直接插入 DOM 的情况

### Requirement: Token 安全存储

系统 SHALL 使用更安全的方式存储认证 Token。

#### Scenario: Refresh Token 存储
- **WHEN** 用户登录成功获取 Token
- **THEN** Refresh Token SHALL 通过 HttpOnly + Secure + SameSite Cookie 存储
- **AND** Access Token 可保留在内存中，不持久化到 localStorage

#### Scenario: Token 键名混淆
- **WHEN** Token 需要存储在浏览器存储中
- **THEN** 存储键名 SHALL 使用混淆后的值，不使用明文 `access_token` / `refresh_token`

### Requirement: 生产环境日志安全

系统 SHALL 确保生产环境不泄露敏感调试信息。

#### Scenario: console.log 清理
- **WHEN** 构建生产版本
- **THEN** 所有 console.log / console.warn 调试语句 SHALL 被移除或替换为条件日志
- **AND** 不存在直接打印 Token、API 响应数据等敏感信息的日志

### Requirement: 内存泄漏修复

系统 SHALL 正确清理所有事件监听器和定时器。

#### Scenario: 组件卸载时清理监听器
- **WHEN** Vue 组件卸载
- **THEN** 所有在 onMounted 中注册的事件监听器 SHALL 在 onUnmounted 中被移除
- **AND** 所有 setInterval / setTimeout SHALL 在组件卸载时被清除

### Requirement: 后端异常信息安全

系统 SHALL 确保异常详情不泄露给客户端。

#### Scenario: 服务层异常处理
- **WHEN** 服务层方法抛出异常
- **THEN** 返回给客户端的错误消息 SHALL 为通用描述
- **AND** 异常详情 SHALL 仅记录到服务端日志
- **AND** 不将 `str(e)` 直接包含在 API 响应中

### Requirement: 密码重置安全

系统 SHALL 对密码重置路由应用完整的密码强度验证。

#### Scenario: 密码重置验证
- **WHEN** 用户通过 Token 重置密码
- **THEN** 新密码 SHALL 通过 PasswordResetConfirmSchema 验证
- **AND** 密码必须包含大写字母、小写字母和数字，长度至少 8 位

### Requirement: 文件上传安全加固

系统 SHALL 对上传文件进行内容验证和安全处理。

#### Scenario: 文件类型验证
- **WHEN** 用户上传文件
- **THEN** 系统 SHALL 验证文件的实际内容（Magic Number / MIME Type）
- **AND** 不仅依赖文件扩展名进行验证

#### Scenario: SVG 文件安全处理
- **WHEN** 用户上传 SVG 文件
- **THEN** 系统 SHALL 对 SVG 内容进行消毒处理，移除内嵌 JavaScript
- **OR** 禁止 SVG 文件上传

### Requirement: API 速率限制

系统 SHALL 对所有 API 路由实施速率限制。

#### Scenario: 全局速率限制
- **WHEN** 客户端发送 API 请求
- **THEN** 系统 SHALL 基于客户端 IP 实施速率限制
- **AND** 超出限制时返回 429 状态码

### Requirement: 安全响应头

系统 SHALL 在所有 HTTP 响应中包含安全头。

#### Scenario: 安全头配置
- **WHEN** 服务器返回 HTTP 响应
- **THEN** 响应 SHALL 包含以下安全头：
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`（至少包含 default-src 和 script-src）
  - `Strict-Transport-Security`（生产环境）
  - `X-XSS-Protection: 1; mode=block`

### Requirement: 配置安全加固

系统 SHALL 确保生产环境不使用弱密钥和调试模式。

#### Scenario: 密钥强制检查
- **WHEN** 应用启动
- **THEN** 系统 SHALL 检查 SECRET_KEY 和 JWT_SECRET_KEY 是否已设置
- **AND** 如果未设置或使用默认值，SHALL 拒绝启动并输出错误信息

#### Scenario: 生产环境调试模式
- **WHEN** FLASK_ENV 为 production
- **THEN** DEBUG SHALL 为 False
- **AND** SQLALCHEMY_ECHO SHALL 为 False

## MODIFIED Requirements

无

## REMOVED Requirements

无
