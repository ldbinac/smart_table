# SmartTable 安全与代码质量审计验收清单

## Phase 1: Critical & High 优先级修复

### 1.1 配置安全加固
- [ ] DevelopmentConfig 中无硬编码弱密钥 fallback，未设置环境变量时应用拒绝启动
- [ ] config.py 默认配置为 ProductionConfig
- [ ] .env.example 和 .env.full.example 中无弱默认密码
- [ ] 应用启动时检查 SECRET_KEY 和 JWT_SECRET_KEY，未设置时输出错误并退出

### 1.2 后端异常信息安全
- [x] 所有服务层方法不再将 str(e) 直接返回客户端
- [x] API 响应中的错误消息为通用描述，不包含数据库表名、文件路径等内部信息
- [x] 异常详情仅记录到服务端日志文件
- [x] 统一的异常处理工具函数已创建并使用

### 1.3 前端 XSS 防护
- [ ] DOMPurify 已安装并创建 sanitizeHtml 工具函数
- [ ] EmailTemplates.vue 中 v-html 渲染前经过 DOMPurify 消毒
- [ ] Dashboard.vue 和 DashboardShare.vue 中所有 innerHTML 插值点经过转义
- [ ] Home.vue 搜索高亮 v-html 确认转义正确

### 1.4 前端内存泄漏修复
- [x] EmailStats.vue 在 onUnmounted 中清理 resize 监听器
- [x] Home.vue 在 onUnmounted 中清理自定义事件监听器
- [x] GanttView.vue scroll 监听器使用命名函数，可在 onBeforeUnmount 中清理
- [x] theme.ts mediaQuery 监听器有清理机制（cleanup 函数）

### 1.5 生产环境日志安全
- [x] 无 console.log 直接打印 Token、API 响应等敏感信息
- [x] Vite 生产构建配置 drop_console 自动移除 console.log
- [x] 必要的调试日志使用条件判断（仅开发环境输出）

## Phase 2: Medium 优先级修复

### 2.1 密码重置安全
- [x] reset-password 路由使用 PasswordResetConfirmSchema 验证
- [x] 弱密码（如全小写 8 位）被拒绝
- [x] 密码强度要求：大写字母 + 小写字母 + 数字，至少 8 位

### 2.2 文件上传安全
- [x] 文件上传验证文件实际内容（Magic Number / MIME Type）
- [x] SVG 文件已从允许列表移除
- [x] 伪造扩展名的恶意文件被拒绝上传

### 2.3 Token 存储安全
- [ ] Refresh Token 通过 HttpOnly + Secure + SameSite Cookie 存储
- [ ] Access Token 仅存储在内存中，不持久化到 localStorage
- [ ] Token 刷新逻辑适配新的存储方式
- [ ] localStorage/sessionStorage 中 Token 键名已混淆

### 2.4 API 速率限制
- [x] 数据查询 API 有速率限制
- [x] 文件上传 API 有速率限制
- [x] 记录操作 API 有速率限制
- [x] 超出限制返回 429 状态码

### 2.5 安全响应头
- [x] 所有 HTTP 响应包含 X-Content-Type-Options: nosniff
- [x] 所有 HTTP 响应包含 X-Frame-Options: DENY
- [x] 所有 HTTP 响应包含 X-XSS-Protection: 1; mode=block
- [x] 配置了 Content-Security-Policy
- [x] 生产环境配置了 Strict-Transport-Security

### 2.6 TypeScript 类型安全
- [ ] Base.vue、TableView.vue、adminStore.ts 中关键 any 类型已替换
- [ ] API 响应和事件数据有正确的类型定义
- [ ] TypeScript 编译无 noImplicitAny 错误

## Phase 3: 验证与报告

### 3.1 安全修复验证
- [ ] XSS 修复验证：v-html 和 innerHTML 不执行恶意脚本
- [ ] 异常信息安全验证：API 响应不包含内部错误详情
- [ ] 密码重置验证：弱密码被拒绝
- [ ] 文件上传验证：伪造扩展名文件被拒绝
- [ ] 速率限制验证：超出限制返回 429

### 3.2 代码质量验证
- [ ] 内存泄漏验证：组件卸载后无残留监听器
- [ ] console.log 验证：生产构建无调试输出
- [ ] TypeScript 验证：无新增 any 类型警告

### 3.3 审计报告
- [ ] 安全审计报告文档已生成
- [ ] 所有修复项和验证结果已汇总
- [ ] 仍需关注的风险项和后续改进建议已列出
