# SmartTable Flask 后端

基于 Python Flask 的多维表格项目管理后端服务。

## 项目概述

SmartTable 是一个功能强大的多维表格管理系统，支持：

- 多维表格（Base）管理
- 灵活的表格（Table）结构
- 22种字段类型支持
- 6种视图类型（表格、画廊、看板、甘特图、日历、表单）
- 公式计算引擎
- 文件附件管理
- 数据导入导出
- 权限管理
- 实时协作（可选，通过 `--enable-realtime` 启用）

## 技术栈

- **框架**: Flask 3.0.0
- **数据库**: PostgreSQL 16 + SQLAlchemy 2.0
- **缓存**: Redis 7
- **认证**: JWT (Flask-JWT-Extended)
- **实时通信**: Flask-SocketIO 5.3.6 + eventlet 0.33.3
- **迁移**: Alembic
- **部署**: Docker + Docker Compose
- **WSGI**: Eventlet WSGI Server (生产环境) / Flask Dev Server (本地开发)

## 快速开始

### 使用 Docker Compose

```bash
# 1. 克隆项目
cd smarttable-backend

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动服务
docker-compose up -d

# 4. 执行数据库迁移
docker-compose --profile migrate run --rm migrate

# 5. 访问 API
# http://localhost:5000/api
```

### 本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 初始化数据库
flask db upgrade

# 5. 启动开发服务器
flask run --reload

# 或启用实时协作
python run.py --enable-realtime
```

## 项目结构

```
smarttable-backend/
├── app/
│   ├── __init__.py                 # 应用工厂
│   ├── config.py                   # 配置文件
│   ├── extensions.py               # 扩展初始化
│   ├── db_types.py                 # 数据库类型定义
│   ├── models/                     # 数据模型
│   │   ├── user.py                 # 用户模型
│   │   ├── base.py                 # Base 模型
│   │   ├── table.py                # 表格模型
│   │   ├── field.py                # 字段模型
│   │   ├── record.py               # 记录模型
│   │   ├── view.py                 # 视图模型
│   │   ├── dashboard.py            # 仪表盘模型
│   │   ├── dashboard_share.py      # 仪表盘分享模型
│   │   ├── attachment.py           # 附件模型
│   │   ├── base_share.py           # Base 分享模型
│   │   ├── form_share.py           # 表单分享模型
│   │   ├── form_submission.py      # 表单提交模型
│   │   ├── link_relation.py        # 关联关系模型
│   │   ├── collaboration_session.py # 协作会话模型
│   │   ├── email_log.py            # 邮件日志模型
│   │   ├── email_template.py       # 邮件模板模型
│   │   ├── operation_history.py    # 操作历史模型
│   │   ├── log.py                  # 日志模型
│   │   └── config.py               # 配置模型
│   ├── services/                   # 业务逻辑层
│   │   ├── auth_service.py         # 认证服务
│   │   ├── base_service.py         # Base 服务
│   │   ├── table_service.py        # 表格服务
│   │   ├── field_service.py        # 字段服务
│   │   ├── record_service.py       # 记录服务
│   │   ├── view_service.py         # 视图服务
│   │   ├── formula_service.py      # 公式服务
│   │   ├── dashboard_service.py    # 仪表盘服务
│   │   ├── dashboard_share_service.py # 仪表盘分享服务
│   │   ├── attachment_service.py   # 附件服务
│   │   ├── collaboration_service.py # 协作服务
│   │   ├── share_service.py        # 分享服务
│   │   ├── form_share_service.py   # 表单分享服务
│   │   ├── permission_service.py   # 权限服务
│   │   ├── import_export_service.py # 导入导出服务
│   │   ├── link_service.py        # 关联服务
│   │   ├── admin_service.py       # 管理服务
│   │   ├── email_sender_service.py # 邮件发送服务
│   │   ├── email_config_service.py # 邮件配置服务
│   │   ├── email_queue_service.py  # 邮件队列服务
│   │   ├── email_retry_service.py  # 邮件重试服务
│   │   └── email_template_service.py # 邮件模板服务
│   ├── routes/                     # 路由层（RESTful API）
│   │   ├── auth.py                 # 认证路由 (/api/auth/*)
│   │   ├── auth_captcha.py         # 验证码路由 (/api/auth/captcha)
│   │   ├── bases.py                # Base 路由 (/api/bases/*)
│   │   ├── tables.py               # 表格路由 (/api/bases/{base_id}/tables/*)
│   │   ├── fields.py               # 字段路由 (/api/fields/*)
│   │   ├── records.py              # 记录路由 (/api/records/*)
│   │   ├── views.py                # 视图路由 (/api/views/*)
│   │   ├── dashboards.py           # 仪表盘路由 (/api/dashboards/*)
│   │   ├── dashboards_share.py     # 仪表盘分享路由
│   │   ├── attachments.py          # 附件路由 (/api/attachments/*)
│   │   ├── shares.py               # 分享路由 (/api/shares/*)
│   │   ├── form_shares.py          # 表单分享路由 (/api/form-shares/*)
│   │   ├── import_export.py        # 导入导出路由 (/api/import-export/*)
│   │   ├── email.py                # 邮件路由 (/api/email/*)
│   │   ├── documents.py           # 文档路由 (/api/documents/*)
│   │   ├── document_versions.py   # 文档版本路由
│   │   ├── admin.py                # 管理路由 (/api/admin/*)
│   │   ├── users.py                # 用户路由 (/api/users/*)
│   │   ├── realtime.py             # 实时协作状态 API (/api/realtime/*)
│   │   └── socketio_events.py      # Socket.IO 事件处理
│   ├── schemas/                    # 数据验证模式
│   │   ├── user_schema.py          # 用户验证
│   │   ├── record_schema.py        # 记录验证
│   │   └── admin_schema.py         # 管理验证
│   ├── utils/                      # 工具模块
│   │   ├── captcha.py              # 验证码生成
│   │   ├── constants.py            # 常量定义
│   │   ├── decorators.py           # 装饰器
│   │   ├── exception_handler.py    # 异常处理
│   │   ├── response.py             # 响应格式化
│   │   ├── validators.py           # 验证器
│   │   └── init_email_templates.py # 初始化邮件模板
│   ├── errors/                     # 错误处理
│   │   └── handlers.py             # 错误处理器
│   ├── middleware/                  # 中间件
│   │   └── security_headers.py     # 安全响应头
│   └── data/                       # 数据文件
│       └── default_email_templates.py # 默认邮件模板
├── migrations/                     # 数据库迁移（Alembic）
│   ├── versions/                   # 迁移版本
│   │   ├── 20250403_0001_initial_migration.py
│   │   ├── 20250405_0002_add_dashboard_is_default.py
│   │   ├── 20250406_0002_add_admin_management_models.py
│   │   ├── 20250406_0003_add_base_sharing.py
│   │   ├── 20250409_0004_add_link_relations.py
│   │   ├── 20250412_0005_add_form_share_tables.py
│   │   ├── 20250414_0006_add_email_tables.py
│   │   ├── 20250414_0007_add_user_email_verification.py
│   │   └── 20250416_0008_add_collaboration_sessions.py
│   ├── env.py                      # 迁移环境
│   └── script.py.mako              # 迁移脚本模板
├── tests/                          # 测试目录
│   ├── conftest.py                 # 测试配置
│   ├── test_auth.py                # 认证测试
│   ├── test_base.py                # Base 测试
│   ├── test_table.py               # 表格测试
│   ├── test_field.py               # 字段测试
│   ├── test_record.py              # 记录测试
│   ├── test_view.py                # 视图测试
│   ├── test_dashboard.py           # 仪表盘测试
│   ├── test_attachment.py          # 附件测试
│   ├── test_formula_service.py     # 公式服务测试
│   ├── test_import_export.py       # 导入导出测试
│   ├── test_auto_number.py         # 自动编号测试
│   ├── test_member_sharing.py      # 成员分享测试
│   ├── test_create_base.py         # 创建 Base 测试
│   ├── test_realtime_enabled.py    # 实时协作测试（启用）
│   ├── test_realtime_disabled.py   # 实时协作测试（禁用）
│   ├── test_logout_all.py          # 登出测试
│   ├── test_validators.py          # 验证器测试
│   ├── test_startup_params.py      # 启动参数测试
│   ├── test_email_integration.py   # 邮件集成测试
│   └── test_email_services.py      # 邮件服务测试
├── requirements.txt                # Python 依赖
├── requirements-dev.txt            # 开发依赖
├── requirements-minimal.txt        # 最小依赖
├── run.py                          # 应用入口
├── init_db.py                      # 数据库初始化
├── init_link_tables.py             # 关联表初始化
├── alembic.ini                     # Alembic 配置
├── Dockerfile                      # Docker 镜像
├── Dockerfile.dev                  # 开发镜像
├── docker-compose.yml              # Docker 编排（SQLite）
├── docker-compose.dev.yml          # Docker 编排（PostgreSQL）
├── .env.example                    # 环境变量示例
└── README.md
```

## API 文档

详见 [API文档.md](./API文档.md)

## 部署指南

详见 [部署指南.md](./部署指南.md)

## 测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_auth.py
pytest tests/test_base.py

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| FLASK_ENV | 运行环境 | development |
| SECRET_KEY | Flask密钥 | - |
| DATABASE_URL | 数据库连接URL | - |
| REDIS_URL | Redis连接URL | - |
| JWT_SECRET_KEY | JWT密钥 | - |
| UPLOAD_FOLDER | 上传目录 | ./uploads |
| MAX_CONTENT_LENGTH | 最大上传大小 | 52428800 |
| ENABLE_REALTIME | 启用实时协作 | false |
| SOCKETIO_MESSAGE_QUEUE | SocketIO消息队列 | - |
| SOCKETIO_PING_TIMEOUT | SocketIO心跳超时 | 60 |
| SOCKETIO_PING_INTERVAL | SocketIO心跳间隔 | 25 |

## 主要功能

### 1. 用户认证
- 用户注册/登录
- JWT Token认证
- Token刷新
- 权限管理

### 2. Base管理
- 创建/编辑/删除多维表格
- 成员管理
- 权限控制

### 3. 表格管理
- 创建/编辑/删除表格
- 字段管理（22种类型）
- 记录CRUD操作
- 批量操作

### 4. 视图管理
- 6种视图类型
- 筛选/排序/分组
- 视图复制

### 5. 公式引擎
- 40+内置函数
- 字段引用
- 实时计算

### 6. 文件管理
- 文件上传/下载
- 缩略图生成
- 附件关联

### 7. 数据导入导出
- Excel/CSV/JSON格式
- 批量导入
- 数据备份

### 8. 实时协作（可选）
- 基于 Flask-SocketIO 的 WebSocket 实时通信
- 房间管理（加入/离开协作房间）
- 在线状态（用户加入/离开通知、视图切换、单元格选中）
- 单元格锁定（编辑时自动锁定，防止冲突）
- 数据变更广播（记录/字段/视图/表格变更实时推送）
- 乐观锁冲突检测（`expected_updated_at` 参数，冲突返回 409）
- 优雅降级（禁用时无额外资源开销）

#### 启用方式

```bash
# 命令行参数
python run.py --enable-realtime
# 或
python run.py -r

# 环境变量
ENABLE_REALTIME=true
```

#### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/realtime/status` | GET | 查询实时协作服务状态 |

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。

## 联系方式

如有问题，请联系开发团队。
