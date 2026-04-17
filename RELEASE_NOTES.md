# SmartTable v1.0.0 Release Notes

## 版本发布说明 / Release Notes

---

## 中文版本

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
