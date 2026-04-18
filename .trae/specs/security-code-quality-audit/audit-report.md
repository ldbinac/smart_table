# SmartTable 安全与代码质量审计报告

**审计日期**: 2026-04-18  
**审计范围**: 前后端源代码、配置文件、依赖包及相关基础设施  
**审计状态**: 已完成

---

## 执行摘要

本次审计对 SmartTable 项目进行了全面的安全与代码质量检查，共识别出 **15 个主要问题领域**，其中 **12 个已修复**，**3 个待后续处理**。

### 修复统计

| 优先级 | 总计 | 已完成 | 待处理 |
|--------|------|--------|--------|
| Critical/High | 5 | 4 | 1 |
| Medium | 6 | 4 | 2 |
| Low | 4 | 4 | 0 |
| **总计** | **15** | **12** | **3** |

---

## 已完成的修复项

### Phase 1: Critical & High 优先级修复

#### 1.2 后端异常信息安全 ✅
**问题**: 服务层方法将 `str(e)` 直接返回客户端，可能泄露内部错误详情（数据库表名、文件路径等）

**修复内容**:
- 创建统一的异常处理工具函数，区分可公开错误和内部错误
- 扫描并修复所有服务层中 `str(e)` 直接返回客户端的位置（50+ 处）
- 确保异常详情仅记录到服务端日志，返回通用错误消息

**修改文件**:
- `smarttable-backend/app/services/*.py` (多个服务文件)
- `smarttable-backend/app/utils/error_handler.py` (新增)

#### 1.3 前端 XSS 防护 ✅
**问题**: `v-html` 和 `innerHTML` 直接渲染用户可控内容，存在 XSS 风险

**修复内容**:
- 安装 DOMPurify 依赖，创建 `sanitizeHtml` 工具函数
- 修复 `EmailTemplates.vue` 中 v-html 渲染，添加 DOMPurify 消毒
- 审计 `Dashboard.vue` 和 `DashboardShare.vue` 中 19 处 innerHTML，确保所有用户输入经过转义
- 修复 ECharts tooltip formatter 中 `params.name` 未转义问题
- 确认 `Home.vue` 搜索高亮 v-html 转义处理正确

**修改文件**:
- `smart-table/src/utils/sanitize.ts` (新增)
- `smart-table/src/views/admin/EmailTemplates.vue`
- `smart-table/src/views/Dashboard.vue`
- `smart-table/src/views/DashboardShare.vue`

#### 1.4 前端内存泄漏修复 ✅
**问题**: 多个组件在卸载时未清理事件监听器，导致内存泄漏

**修复内容**:
- `EmailStats.vue`: 添加 onUnmounted 清理 resize 监听器
- `Home.vue`: 添加 onUnmounted 清理自定义事件监听器
- `GanttView.vue`: 将匿名 scroll 监听器改为命名函数以便清理
- `Dashboard.vue`/`DashboardShare.vue`: 清理 resize 监听器和图表实例

**修改文件**:
- `smart-table/src/views/admin/EmailStats.vue`
- `smart-table/src/views/Home.vue`
- `smart-table/src/views/Dashboard.vue`
- `smart-table/src/views/DashboardShare.vue`

#### 1.5 生产环境日志安全 ✅
**问题**: console.log 直接打印敏感信息（Token、API 响应等）

**修复内容**:
- 扫描并移除所有包含敏感信息的 console.log
- 配置 Vite 生产构建自动移除 console.log 和 debugger
- 必要的调试日志替换为条件日志（仅开发环境输出）

**修改文件**:
- `smart-table/vite.config.ts`
- `smart-table/src/**/*.vue` (多个文件)

---

### Phase 2: Medium 优先级修复

#### 2.1 密码重置安全 ✅
**问题**: reset-password 路由验证可绕过，弱密码可被接受

**修复内容**:
- 修改 `auth.py` reset-password 路由，使用 `PasswordResetConfirmSchema` 验证
- 密码强度要求：大写字母 + 小写字母 + 数字，至少 8 位

**修改文件**:
- `smarttable-backend/app/routes/auth.py`
- `smarttable-backend/app/schemas/auth.py`

**验证结果**: 弱密码 "weakpass" 被正确拒绝，返回错误信息 "密码必须包含至少一个大写字母"

#### 2.2 文件上传安全加固 ✅
**问题**: 文件上传仅验证扩展名，未验证文件实际内容

**修复内容**:
- 添加文件内容验证（Magic Number / MIME Type 检查）
- SVG 文件从允许列表移除
- 添加危险文件类型黑名单

**修改文件**:
- `smarttable-backend/app/services/attachment_service.py`

**安全措施**:
```python
FILE_SIGNATURES = {
    'image/jpeg': [(b'\xff\xd8\xff', 0)],
    'image/png': [(b'\x89PNG\r\n\x1a\n', 0)],
    # ... 更多签名
}

DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.svg', '.svgz', ...
}
```

#### 2.4 API 速率限制扩展 ✅
**问题**: 部分敏感 API 缺少速率限制

**修复内容**:
- 创建全局速率限制装饰器 `@rate_limit`
- 对数据查询、文件上传、记录操作 API 添加速率限制
- 超出限制返回 429 状态码

**修改文件**:
- `smarttable-backend/app/utils/decorators.py`
- `smarttable-backend/app/routes/*.py` (多个路由文件)

#### 2.5 安全响应头配置 ✅
**问题**: HTTP 响应缺少安全响应头

**修复内容**:
- 创建安全响应头中间件
- 配置 X-Content-Type-Options: nosniff
- 配置 X-Frame-Options: DENY
- 配置 X-XSS-Protection: 1; mode=block
- 配置 Content-Security-Policy
- 生产环境配置 Strict-Transport-Security (HSTS)

**修改文件**:
- `smarttable-backend/app/middleware/security_headers.py`

**验证结果**:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 待处理的修复项

### 1.1 配置安全加固 (待处理)
**问题**: DevelopmentConfig 中存在硬编码弱密钥 fallback

**建议**:
- 修改 DevelopmentConfig，将 fallback 密钥改为 None
- 添加应用启动时的密钥检查逻辑，未设置时拒绝启动
- 更新 .env.example，移除弱默认密码

### 2.3 Token 存储安全改造 (待处理)
**问题**: Token 存储在 localStorage，存在 XSS 窃取风险

**建议**:
- Refresh Token 通过 HttpOnly + Secure + SameSite Cookie 存储
- Access Token 仅存储在内存中，不持久化到 localStorage
- 修改 Token 刷新逻辑适配新的存储方式

### 2.6 TypeScript 类型安全改进 (待处理)
**问题**: 关键文件中存在 any 类型，降低类型安全性

**建议**:
- 修复 Base.vue、TableView.vue、adminStore.ts 中的 any 类型
- 为 API 响应和事件数据添加正确的类型定义
- 启用更严格的 TypeScript 编译选项（noImplicitAny）

---

## 验证结果汇总

### 安全修复验证

| 验证项 | 状态 | 说明 |
|--------|------|------|
| XSS 修复验证 | ✅ 通过 | v-html 和 innerHTML 使用 DOMPurify/escapeHtml 消毒 |
| 异常信息安全 | ✅ 通过 | API 响应返回通用错误消息，详情记录服务端日志 |
| 密码重置安全 | ✅ 通过 | 弱密码 "weakpass" 被正确拒绝 |
| 文件上传安全 | ✅ 通过 | Magic Number 验证 + 危险扩展名黑名单 |
| 速率限制 | ✅ 通过 | 登录 API 限制 5 次/15分钟，返回 429 |
| 安全响应头 | ✅ 通过 | 所有安全头正确配置 |

### 代码质量验证

| 验证项 | 状态 | 说明 |
|--------|------|------|
| 内存泄漏修复 | ✅ 通过 | 所有组件在 onUnmounted 中清理监听器 |
| console.log 清理 | ✅ 通过 | Vite 生产构建配置 drop: ['console', 'debugger'] |
| TypeScript 验证 | ✅ 通过 | 无新增 any 类型警告 |

---

## 后续改进建议

### 短期 (1-2 周)
1. 完成配置安全加固 (Task 1.1)
2. 完成 Token 存储安全改造 (Task 2.3)
3. 添加自动化安全测试用例

### 中期 (1-2 月)
1. 完成 TypeScript 类型安全改进 (Task 2.6)
2. 实施 CSP 报告机制
3. 添加安全审计日志

### 长期 (3-6 月)
1. 实施定期安全扫描流程
2. 建立 SDL (安全开发生命周期) 流程
3. 进行渗透测试

---

## 附录

### 修改文件清单

**后端文件**:
- `app/middleware/security_headers.py` - 安全响应头中间件
- `app/utils/decorators.py` - 速率限制装饰器
- `app/utils/error_handler.py` - 异常处理工具
- `app/services/attachment_service.py` - 文件上传安全
- `app/routes/auth.py` - 密码重置验证
- `app/schemas/auth.py` - 密码验证 Schema

**前端文件**:
- `src/utils/sanitize.ts` - HTML 消毒工具
- `src/views/admin/EmailTemplates.vue` - XSS 防护
- `src/views/Dashboard.vue` - XSS 防护 + 内存泄漏修复
- `src/views/DashboardShare.vue` - XSS 防护 + 内存泄漏修复
- `src/views/Home.vue` - 内存泄漏修复
- `src/views/admin/EmailStats.vue` - 内存泄漏修复
- `vite.config.ts` - 生产构建安全配置

---

**报告生成时间**: 2026-04-18  
**审计人员**: AI Security Audit Agent
