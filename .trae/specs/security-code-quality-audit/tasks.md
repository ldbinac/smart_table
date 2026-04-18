# Tasks

## Phase 1: Critical & High 优先级修复

- [ ] Task 1.1: 配置安全加固 - 移除硬编码弱密钥
  - [ ] SubTask 1.1.1: 修改 DevelopmentConfig，将 fallback 密钥改为 None，添加启动时强制检查
  - [ ] SubTask 1.1.2: 修改 config.py 默认配置为 ProductionConfig
  - [ ] SubTask 1.1.3: 更新 .env.example 和 .env.full.example，移除弱默认密码，添加密钥生成说明
  - [ ] SubTask 1.1.4: 添加应用启动时的密钥检查逻辑，未设置时拒绝启动

- [x] Task 1.2: 后端异常信息安全 - 过滤 str(e) 泄露
  - [x] SubTask 1.2.1: 创建统一的异常处理工具函数，区分可公开错误和内部错误
  - [x] SubTask 1.2.2: 扫描并修复所有服务层中 str(e) 直接返回客户端的位置（50+ 处）
  - [x] SubTask 1.2.3: 确保异常详情仅记录到服务端日志，返回通用错误消息

- [ ] Task 1.3: 前端 XSS 防护 - v-html 和 innerHTML 加固
  - [ ] SubTask 1.3.1: 安装 DOMPurify 依赖，创建 sanitizeHtml 工具函数
  - [ ] SubTask 1.3.2: 修复 EmailTemplates.vue 中 v-html 渲染，添加 DOMPurify 消毒
  - [ ] SubTask 1.3.3: 审计 Dashboard.vue 和 DashboardShare.vue 中 38 处 innerHTML，确保所有用户输入经过转义
  - [ ] SubTask 1.3.4: 审计 Home.vue 中 v-html 搜索高亮，确认转义处理正确

- [x] Task 1.4: 前端内存泄漏修复
  - [x] SubTask 1.4.1: 修复 EmailStats.vue - 添加 onUnmounted 清理 resize 监听器
  - [x] SubTask 1.4.2: 修复 Home.vue - 添加 onUnmounted 清理自定义事件监听器
  - [x] SubTask 1.4.3: 修复 GanttView.vue - 将匿名 scroll 监听器改为命名函数以便清理
  - [x] SubTask 1.4.4: 审计 theme.ts mediaQuery 监听器，评估是否需要清理机制

- [ ] Task 1.5: 生产环境日志安全 - 清理 console.log
  - [ ] SubTask 1.5.1: 扫描并移除所有包含敏感信息的 console.log（Token、API 响应等）
  - [ ] SubTask 1.5.2: 配置 Vite 生产构建自动移除 console.log（drop_console）
  - [ ] SubTask 1.5.3: 将必要的调试日志替换为条件日志（仅开发环境输出）

## Phase 2: Medium 优先级修复

- [ ] Task 2.1: 密码重置安全 - 修复 reset-password 路由验证绕过
  - [ ] SubTask 2.1.1: 修改 auth.py reset-password 路由，使用 PasswordResetConfirmSchema 验证
  - [ ] SubTask 2.1.2: 添加测试用例验证密码强度要求生效

- [ ] Task 2.2: 文件上传安全加固
  - [ ] SubTask 2.2.1: 添加文件内容验证（Magic Number / MIME Type 检查）
  - [ ] SubTask 2.2.2: 对 SVG 文件进行消毒处理或从允许列表中移除
  - [ ] SubTask 2.2.3: 添加文件上传安全测试用例

- [ ] Task 2.3: Token 存储安全改造
  - [ ] SubTask 2.3.1: 后端添加 Refresh Token 的 HttpOnly Cookie 设置
  - [ ] SubTask 2.3.2: 前端修改 Token 存储逻辑，Access Token 仅存内存，Refresh Token 使用 Cookie
  - [ ] SubTask 2.3.3: 修改 Token 刷新逻辑适配新的存储方式
  - [ ] SubTask 2.3.4: 混淆 localStorage/sessionStorage 中的 Token 键名

- [ ] Task 2.4: API 速率限制扩展
  - [ ] SubTask 2.4.1: 创建全局速率限制中间件/装饰器
  - [ ] SubTask 2.4.2: 对数据查询 API 添加速率限制
  - [ ] SubTask 2.4.3: 对文件上传 API 添加速率限制
  - [ ] SubTask 2.4.4: 对记录操作 API 添加速率限制

- [ ] Task 2.5: 安全响应头配置
  - [ ] SubTask 2.5.1: 安装 Flask-Talisman 或创建安全头中间件
  - [ ] SubTask 2.5.2: 配置 X-Content-Type-Options、X-Frame-Options、X-XSS-Protection
  - [ ] SubTask 2.5.3: 配置 Content-Security-Policy
  - [ ] SubTask 2.5.4: 生产环境配置 Strict-Transport-Security (HSTS)

- [ ] Task 2.6: TypeScript 类型安全改进
  - [ ] SubTask 2.6.1: 修复关键文件中的 any 类型（Base.vue、TableView.vue、adminStore.ts）
  - [ ] SubTask 2.6.2: 为 API 响应和事件数据添加正确的类型定义
  - [ ] SubTask 2.6.3: 启用更严格的 TypeScript 编译选项（noImplicitAny）

## Phase 3: 验证与报告

- [ ] Task 3.1: 安全修复验证
  - [ ] SubTask 3.1.1: 验证 XSS 修复 - 测试 v-html 和 innerHTML 不再执行恶意脚本
  - [ ] SubTask 3.1.2: 验证异常信息安全 - 确认 API 响应不包含内部错误详情
  - [ ] SubTask 3.1.3: 验证密码重置安全 - 测试弱密码被拒绝
  - [ ] SubTask 3.1.4: 验证文件上传安全 - 测试伪造扩展名的文件被拒绝
  - [ ] SubTask 3.1.5: 验证速率限制 - 测试超出限制返回 429

- [ ] Task 3.2: 代码质量验证
  - [ ] SubTask 3.2.1: 验证内存泄漏修复 - 组件卸载后无残留监听器
  - [ ] SubTask 3.2.2: 验证 console.log 清理 - 生产构建无调试输出
  - [ ] SubTask 3.2.3: 验证 TypeScript 类型改进 - 无新增 any 类型警告

- [ ] Task 3.3: 生成审计报告
  - [ ] SubTask 3.3.1: 汇总所有修复项和验证结果
  - [ ] SubTask 3.3.2: 生成安全审计报告文档
  - [ ] SubTask 3.3.3: 列出仍需关注的风险项和后续改进建议

# Task Dependencies

- [Task 1.1] 无依赖，可立即开始
- [Task 1.2] 无依赖，可立即开始
- [Task 1.3] 无依赖，可立即开始（SubTask 1.3.1 需先完成）
- [Task 1.4] 无依赖，可立即开始
- [Task 1.5] 无依赖，可立即开始
- [Task 2.1] 无依赖，可立即开始
- [Task 2.2] 无依赖，可立即开始
- [Task 2.3] 依赖 [Task 1.3]（XSS 修复后 Token 存储改造才有意义）
- [Task 2.4] 无依赖，可立即开始
- [Task 2.5] 无依赖，可立即开始
- [Task 2.6] 无依赖，可立即开始
- [Task 3.1] 依赖 [Task 1.1-1.5, Task 2.1-2.5]
- [Task 3.2] 依赖 [Task 1.4, Task 1.5, Task 2.6]
- [Task 3.3] 依赖 [Task 3.1, Task 3.2]
