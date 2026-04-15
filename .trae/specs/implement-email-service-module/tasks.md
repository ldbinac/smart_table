# 邮件配置功能模块任务列表

## 阶段一：完善现有邮件配置界面

- [x] Task 1: 完善前端邮件配置界面
  - [x] SubTask 1.1: 在 SystemSettings.vue 邮件配置标签页新增"启用邮件服务"开关
  - [x] SubTask 1.2: 新增"发件人显示名称"输入字段
  - [x] SubTask 1.3: 新增"SMTP账号"输入字段
  - [x] SubTask 1.4: 新增"SMTP密码"密码输入字段（带显示/隐藏切换）
  - [x] SubTask 1.5: 完善"使用SSL"为"使用SSL/TLS"下拉选择（SSL/TLS/无）
  - [x] SubTask 1.6: 新增"发送测试邮件"按钮和测试邮箱输入框
  - [x] SubTask 1.7: 添加表单字段验证规则

- [x] Task 2: 完善后端邮件配置API
  - [x] SubTask 2.1: 新增邮件配置验证接口 POST /api/admin/email/verify-config
  - [x] SubTask 2.2: 新增测试邮件发送接口 POST /api/admin/email/test
  - [x] SubTask 2.3: 实现SMTP密码加密存储（使用应用密钥加密）
  - [x] SubTask 2.4: 实现SMTP密码解密读取

## 阶段二：邮件服务核心模块

- [x] Task 3: 创建邮件服务数据库模型
  - [x] SubTask 3.1: 创建邮件模板表 (email_templates) - 存储邮件模板
  - [x] SubTask 3.2: 创建邮件日志表 (email_logs) - 存储邮件发送记录
  - [x] SubTask 3.3: 创建数据库迁移脚本

- [x] Task 4: 实现邮件服务核心模块
  - [x] SubTask 4.1: 实现邮件配置读取服务 (EmailConfigService) - 从SystemConfig读取并解密
  - [x] SubTask 4.2: 实现邮件发送服务 (EmailSenderService) - SMTP连接和发送
  - [x] SubTask 4.3: 实现邮件模板服务 (EmailTemplateService) - 模板管理和渲染
  - [x] SubTask 4.4: 实现邮件日志服务 (EmailLogService) - 日志记录和查询
  - [x] SubTask 4.5: 实现邮件重试机制 (EmailRetryService) - 失败重试逻辑

- [x] Task 5: 实现邮件服务API接口
  - [x] SubTask 5.1: 实现获取邮件模板列表接口 GET /api/admin/email/templates
  - [x] SubTask 5.2: 实现获取单个模板接口 GET /api/admin/email/templates/:id
  - [x] SubTask 5.3: 实现更新模板接口 PUT /api/admin/email/templates/:id
  - [x] SubTask 5.4: 实现重置模板接口 POST /api/admin/email/templates/:id/reset
  - [x] SubTask 5.5: 实现获取邮件日志接口 GET /api/admin/email/logs
  - [x] SubTask 5.6: 实现获取邮件统计接口 GET /api/admin/email/stats

## 阶段三：邮件模板系统

- [x] Task 6: 创建默认邮件模板
  - [x] SubTask 6.1: 创建用户注册验证邮件模板
  - [x] SubTask 6.2: 创建密码重置邮件模板
  - [x] SubTask 6.3: 创建账号停用通知邮件模板
  - [x] SubTask 6.4: 创建账号启用通知邮件模板
  - [x] SubTask 6.5: 创建密码重置通知邮件模板
  - [x] SubTask 6.6: 创建账号信息变更通知邮件模板
  - [x] SubTask 6.7: 创建账号删除通知邮件模板
  - [x] SubTask 6.8: 创建分享邀请邮件模板
  - [x] SubTask 6.9: 创建分享移除通知邮件模板
  - [x] SubTask 6.10: 创建权限变更通知邮件模板

- [x] Task 7: 初始化邮件模板数据
  - [x] SubTask 7.1: 编写默认模板数据初始化脚本
  - [x] SubTask 7.2: 在应用启动时检查并初始化默认模板

## 阶段四：业务功能集成

- [x] Task 8: 集成用户注册邮箱验证
  - [x] SubTask 8.1: 修改用户模型，新增 email_verified 和 verification_token 字段
  - [x] SubTask 8.2: 修改用户注册流程，生成验证令牌
  - [x] SubTask 8.3: 发送注册验证邮件（仅在邮件服务启用时）
  - [x] SubTask 8.4: 实现邮箱验证接口 GET /api/auth/verify-email/:token
  - [x] SubTask 8.5: 实现重新发送验证邮件接口 POST /api/auth/resend-verification
  - [x] SubTask 8.6: 前端新增邮箱验证页面

- [x] Task 9: 集成找回密码功能
  - [x] SubTask 9.1: 修改密码找回流程，生成重置令牌
  - [x] SubTask 9.2: 发送密码重置邮件（仅在邮件服务启用时）
  - [x] SubTask 9.3: 实现密码重置页面和接口
  - [x] SubTask 9.4: 实现请求频率限制（5分钟内最多3次）

- [x] Task 10: 集成账号管理通知
  - [x] SubTask 10.1: 在账号停用后发送通知邮件
  - [x] SubTask 10.2: 在账号启用后发送通知邮件
  - [x] SubTask 10.3: 在密码重置后发送通知邮件
  - [x] SubTask 10.4: 在账号信息编辑后发送通知邮件
  - [x] SubTask 10.5: 在账号删除前发送通知邮件

- [x] Task 11: 集成多维表分享通知
  - [x] SubTask 11.1: 在添加分享成员后发送邀请邮件
  - [x] SubTask 11.2: 在移除分享成员后发送通知邮件
  - [x] SubTask 11.3: 在修改分享权限后发送通知邮件

## 阶段五：前端界面开发

- [x] Task 12: 开发邮件模板管理页面
  - [x] SubTask 12.1: 创建邮件模板管理路由和页面
  - [x] SubTask 12.2: 创建模板列表组件
  - [x] SubTask 12.3: 创建模板编辑组件（支持HTML编辑）
  - [x] SubTask 12.4: 实现模板预览功能
  - [x] SubTask 12.5: 实现重置默认模板功能

- [x] Task 13: 开发邮件日志查询页面
  - [x] SubTask 13.1: 创建邮件日志页面路由和页面
  - [x] SubTask 13.2: 创建邮件日志列表组件
  - [x] SubTask 13.3: 实现筛选功能（时间、类型、状态）
  - [x] SubTask 13.4: 实现分页功能
  - [x] SubTask 13.5: 显示邮件详情弹窗

- [x] Task 14: 开发邮件统计页面
  - [x] SubTask 14.1: 创建邮件统计页面路由和页面
  - [x] SubTask 14.2: 创建发送成功率统计图表
  - [x] SubTask 14.3: 创建邮件类型分布图表
  - [x] SubTask 14.4: 创建发送失败原因分析图表

- [x] Task 15: 更新系统管理菜单
  - [x] SubTask 15.1: 在系统管理菜单下新增"邮件模板"菜单项
  - [x] SubTask 15.2: 在系统管理菜单下新增"邮件日志"菜单项
  - [x] SubTask 15.3: 在系统管理菜单下新增"邮件统计"菜单项

## 阶段六：测试与优化

- [x] Task 16: 编写单元测试
  - [x] SubTask 16.1: 测试邮件配置服务
  - [x] SubTask 16.2: 测试邮件发送服务
  - [x] SubTask 16.3: 测试邮件模板服务
  - [x] SubTask 16.4: 测试邮件重试机制

- [x] Task 17: 编写集成测试
  - [x] SubTask 17.1: 测试用户注册验证流程
  - [x] SubTask 17.2: 测试密码找回流程
  - [x] SubTask 17.3: 测试账号管理通知
  - [x] SubTask 17.4: 测试分享成员通知

- [x] Task 18: 性能优化
  - [x] SubTask 18.1: 实现邮件发送队列（使用线程池）
    - 创建 EmailQueueService 类实现异步邮件发送
    - 支持优先级队列（高/普通/低）
    - 支持批量处理邮件
    - 实现指数退避重试机制
    - 提供队列统计接口 GET /api/admin/email/queue/stats
  - [x] SubTask 18.2: 优化批量邮件处理
    - 批量收集邮件任务
    - 使用线程池并发处理
    - 批量大小和间隔可配置
  - [x] SubTask 18.3: 添加邮件发送异步处理
    - 应用启动时自动初始化邮件队列
    - 支持非阻塞邮件发送
    - 提供回调机制处理发送结果

# Task Dependencies

## 依赖关系图
```
Task 1 (完善前端界面) ──┐
                        ├──→ Task 4 (核心服务) ──→ Task 6/7 (模板) ──→ Task 8/9/10/11 (业务集成)
Task 2 (完善后端API) ───┘                                              ↓
                                                             Task 12/13/14/15 (前端界面)
                                                                              ↓
                                                                     Task 16/17/18 (测试优化)
```

## 并行任务
- Task 1 和 Task 2 可以并行开发
- Task 3 和 Task 4 可以并行开发
- Task 12、13、14、15 可以并行开发
- Task 16、17、18 可以并行开发

## 关键路径
Task 1/2 → Task 4 → Task 6/7 → Task 8/9/10/11 → Task 12/13/14/15 → Task 16/17/18
