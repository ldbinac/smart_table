# SmartTable Release Notes

## 版本发布说明 / Release Notes

---

# SmartTable v1.1.0 Release Notes

**发布日期 / Release Date**: 2026-04-18

**版本号 / Version**: v1.1.0

**标签 / Tags**: `release`, `v1.1.0`, `stable`

---

## 中文版本

### 🎉 SmartTable v1.1.0 更新说明

本次更新带来了多项重要功能增强和安全改进，包括实时协作功能、邮件服务系统、全面的安全加固以及多项Bug修复。

### ✨ 新增功能

#### 🚀 实时协作功能
- **WebSocket 实时同步** - 基于 WebSocket 的实时数据同步，支持多用户同时编辑
- **协作状态显示** - 显示当前正在编辑的用户信息
- **用户姓名字段** - 支持显示协作用户的真实姓名

#### 📧 邮件服务系统
- **完整邮件模块** - 实现完整的邮件服务功能模块
- **邮件队列服务** - 支持异步邮件发送，提高系统响应速度
- **密码找回功能** - 通过邮件实现密码重置功能
- **修改密码功能** - 用户可在设置中修改密码

#### 🔒 安全增强
- **XSS 防护** - 使用 DOMPurify 实现 HTML 消毒，防止 XSS 攻击
- **安全响应头** - 添加 X-Content-Type-Options、X-Frame-Options、X-XSS-Protection 等安全响应头
- **API 速率限制** - 防止暴力破解和恶意请求，超出限制返回 429 状态码
- **文件上传安全** - 增强 Magic Number 和 MIME Type 验证，移除 SVG 等高风险文件类型
- **异常信息安全** - 统一异常处理，防止内部错误信息泄露
- **生产日志安全** - 生产环境自动移除 console.log，防止敏感信息泄露

#### 🎨 UI/UX 改进
- **侧边栏悬浮菜单** - 收起状态下支持悬浮二级菜单
- **多维表格复制** - 支持一键复制多维表格
- **验证码功能** - 登录和注册流程增加验证码验证
- **评分字段** - 新增评分字段类型支持
- **日期格式化** - 日期字段值支持格式化显示

#### 🐳 部署支持
- **Docker 部署** - 添加完整的 Docker 部署配置和文档
- **远程访问** - 开发服务器支持远程访问

### 🐛 Bug 修复

- 修复仪表盘配置界面刷新报错问题
- 修复前端内存泄漏问题（多个组件事件监听器未清理）
- 修复密码重置路由验证绕过问题
- 修复取消收藏接口 HTTP 方法错误
- 修复 SQLAlchemy 无法检测 config 变更的问题
- 修复时区问题，统一使用 UTC 时间
- 修复前端安全漏洞问题
- 修复表单验证错误处理和重置逻辑

### 🔧 优化改进

- 优化记录详情抽屉底部按钮布局
- 优化模板同步流程
- 优化错误处理机制
- 完善基础数据删除时的级联删除逻辑

### 📝 文档更新

- 添加安全与代码质量审计报告
- 添加实时协作功能规格说明
- 添加群组管理系统规格文档

---

## English Version

### 🎉 SmartTable v1.1.0 Release Notes

This release brings significant feature enhancements and security improvements, including real-time collaboration, email service system, comprehensive security hardening, and multiple bug fixes.

### ✨ New Features

#### 🚀 Real-time Collaboration
- **WebSocket Real-time Sync** - Real-time data synchronization based on WebSocket, supporting multi-user simultaneous editing
- **Collaboration Status Display** - Shows information about users currently editing
- **User Name Field** - Support for displaying collaborator's real names

#### 📧 Email Service System
- **Complete Email Module** - Fully implemented email service functionality
- **Email Queue Service** - Asynchronous email sending for improved system responsiveness
- **Password Recovery** - Password reset via email
- **Change Password** - Users can change password in settings

#### 🔒 Security Enhancements
- **XSS Protection** - HTML sanitization using DOMPurify to prevent XSS attacks
- **Security Headers** - Added X-Content-Type-Options, X-Frame-Options, X-XSS-Protection security headers
- **API Rate Limiting** - Prevent brute force attacks and malicious requests, returns 429 status code when exceeded
- **File Upload Security** - Enhanced Magic Number and MIME Type validation, removed SVG and other high-risk file types
- **Exception Information Security** - Unified exception handling to prevent internal error information leakage
- **Production Log Security** - Automatic removal of console.log in production to prevent sensitive information leakage

#### 🎨 UI/UX Improvements
- **Sidebar Hover Menu** - Floating secondary menu in collapsed state
- **Base Duplication** - One-click base duplication
- **CAPTCHA Feature** - Added CAPTCHA verification for login and registration
- **Rating Field** - New rating field type support
- **Date Formatting** - Date field values support formatted display

#### 🐳 Deployment Support
- **Docker Deployment** - Complete Docker deployment configuration and documentation
- **Remote Access** - Development server supports remote access

### 🐛 Bug Fixes

- Fixed dashboard configuration page refresh error
- Fixed frontend memory leak issues (multiple component event listeners not cleaned up)
- Fixed password reset route validation bypass issue
- Fixed incorrect HTTP method for unstar API
- Fixed SQLAlchemy config change detection issue
- Fixed timezone issues, unified UTC time usage
- Fixed frontend security vulnerabilities
- Fixed form validation error handling and reset logic

### 🔧 Improvements

- Optimized record detail drawer bottom button layout
- Optimized template synchronization process
- Optimized error handling mechanism
- Improved cascade deletion logic for base data

### 📝 Documentation Updates

- Added security and code quality audit report
- Added real-time collaboration feature specification
- Added group management system specification document

---

# SmartTable v1.0.0 Release Notes

### 🎉 欢迎使用 SmartTable v1.0.0

SmartTable 是一个开源的多维表格管理系统，提供类似 Airtable 的数据管理体验。

### ✨ 主要功能

#### 核心功能
- **多维表格管理** - 创建和管理多个数据表格，支持自定义字段类型
- **多种字段类型** - 支持文本、数字、日期、单选、多选、附件、链接、评分、进度等 15+ 种字段类型
- **数据视图** - 支持表格视图、看板视图、表单视图等多种数据展示方式
- **数据关联** - 支持表格之间的关联关系，实现数据联动

#### 表单分享功能
- **公开表单分享** - 将表格数据以表单形式分享给外部用户填写
- **匿名提交支持** - 支持无需登录即可提交数据
- **验证码保护** - 表单分享支持验证码验证，防止恶意提交
- **自定义配置** - 可配置分享有效期、提交次数限制等

#### 用户与权限
- **用户认证** - 支持邮箱注册、登录、密码修改
- **JWT 令牌** - 基于 JWT 的安全认证机制
- **权限控制** - 细粒度的数据访问权限控制

#### 安全特性
- **验证码机制** - 登录、注册、表单提交均支持验证码验证
- **速率限制** - 防止暴力破解和恶意请求
- **密码安全** - 密码使用 bcrypt 加密存储
- **SQL 注入防护** - 使用 ORM 防止 SQL 注入攻击
- **XSS 防护** - 输入验证和输出转义防止 XSS 攻击

### 🛠 技术栈

#### 后端
- **Python 3.11+**
- **Flask 3.0** - Web 框架
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL** - 主数据库
- **Redis** - 缓存和会话存储
- **JWT** - 身份认证

#### 前端
- **Vue 3** - 前端框架
- **TypeScript** - 类型安全
- **Element Plus** - UI 组件库
- **Pinia** - 状态管理
- **Vue Router** - 路由管理

### 📦 安装与部署

#### 快速开始

```bash
# 克隆仓库
git clone https://github.com/ldbinac/smart_table.git
cd smart_table

# 启动后端
cd smarttable-backend
pip install -r requirements.txt
python run.py

# 启动前端
cd ../smart-table
npm install
npm run dev
```

详细安装文档请参考 [README.md](./README.md)

### 🐛 已知问题

- 暂无

### 🔜 即将推出

- 协作编辑功能
- 数据导入导出（Excel、CSV）
- API 密钥管理
- Webhook 支持
- 更多字段类型

### 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)

### 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## English Version

### 🎉 Welcome to SmartTable v1.0.0

SmartTable is an open-source multi-dimensional table management system, providing an Airtable-like data management experience.

### ✨ Key Features

#### Core Features
- **Multi-dimensional Table Management** - Create and manage multiple data tables with custom field types
- **Multiple Field Types** - Support for 15+ field types including text, number, date, single select, multi-select, attachment, link, rating, progress, and more
- **Data Views** - Support for grid view, kanban view, form view, and other data presentation methods
- **Data Relationships** - Support for relationships between tables, enabling data linkage

#### Form Sharing Features
- **Public Form Sharing** - Share table data as forms for external users to fill out
- **Anonymous Submission Support** - Support for data submission without login
- **CAPTCHA Protection** - Form sharing supports CAPTCHA verification to prevent malicious submissions
- **Custom Configuration** - Configurable sharing expiration, submission limits, and more

#### User & Permissions
- **User Authentication** - Support for email registration, login, and password modification
- **JWT Tokens** - Secure authentication mechanism based on JWT
- **Permission Control** - Fine-grained data access permission control

#### Security Features
- **CAPTCHA Mechanism** - Login, registration, and form submission all support CAPTCHA verification
- **Rate Limiting** - Prevent brute force attacks and malicious requests
- **Password Security** - Passwords encrypted using bcrypt
- **SQL Injection Protection** - Use ORM to prevent SQL injection attacks
- **XSS Protection** - Input validation and output escaping to prevent XSS attacks

### 🛠 Tech Stack

#### Backend
- **Python 3.11+**
- **Flask 3.0** - Web framework
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL** - Primary database
- **Redis** - Cache and session storage
- **JWT** - Authentication

#### Frontend
- **Vue 3** - Frontend framework
- **TypeScript** - Type safety
- **Element Plus** - UI component library
- **Pinia** - State management
- **Vue Router** - Route management

### 📦 Installation & Deployment

#### Quick Start

```bash
# Clone repository
git clone https://github.com/ldbinac/smart_table.git
cd smart_table

# Start backend
cd smarttable-backend
pip install -r requirements.txt
python run.py

# Start frontend
cd ../smart-table
npm install
npm run dev
```

For detailed installation instructions, please refer to [README.md](./README.md)

### 🐛 Known Issues

- None

### 🔜 Coming Soon

- Collaborative editing features
- Data import/export (Excel, CSV)
- API key management
- Webhook support
- More field types

### 📄 License

This project is licensed under the [MIT License](./LICENSE)

### 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 链接 / Links

- **GitHub**: https://github.com/ldbinac/smart_table.git
- **Gitee**: https://gitee.com/binac/smart_table.git
- **文档 / Documentation**: https://github.com/ldbinac/smart_table/wiki
- **问题反馈 / Issue Tracker**: https://github.com/ldbinac/smart_table/issues

---

**发布日期 / Release Date**: 2026-04-13

**版本号 / Version**: v1.0.0

**标签 / Tags**: `release`, `v1.0.0`, `stable`
