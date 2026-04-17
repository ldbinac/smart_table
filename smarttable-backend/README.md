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
- **WSGI**: Gunicorn

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
├── app/                    # 应用主目录
│   ├── __init__.py        # 应用工厂
│   ├── config.py          # 配置文件
│   ├── extensions.py      # 扩展初始化
│   ├── models/            # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py        # 用户模型
│   │   ├── base.py        # Base模型
│   │   ├── table.py       # 表格模型
│   │   ├── field.py       # 字段模型
│   │   ├── record.py      # 记录模型
│   │   ├── view.py        # 视图模型
│   │   ├── dashboard.py   # 仪表盘模型
│   │   ├── attachment.py  # 附件模型
│   │   └── collaboration_session.py  # 协作会话模型
│   ├── services/          # 业务逻辑层
│   │   ├── auth_service.py
│   │   ├── base_service.py
│   │   ├── table_service.py
│   │   ├── field_service.py
│   │   ├── record_service.py
│   │   ├── view_service.py
│   │   ├── formula_service.py
│   │   ├── dashboard_service.py
│   │   ├── attachment_service.py
│   │   ├── collaboration_service.py  # 协作服务（房间、在线状态、锁定、广播）
│   │   └── import_export_service.py
│   ├── routes/            # 路由层
│   │   ├── auth.py        # 认证路由
│   │   ├── bases.py       # Base路由
│   │   ├── tables.py      # 表格路由
│   │   ├── fields.py      # 字段路由
│   │   ├── records.py     # 记录路由
│   │   ├── views.py       # 视图路由
│   │   ├── dashboards.py  # 仪表盘路由
│   │   ├── attachments.py # 附件路由
│   │   ├── realtime.py    # 实时协作状态路由
│   │   └── import_export.py # 导入导出路由
│   ├── utils/             # 工具模块
│   │   ├── response.py    # 响应工具
│   │   ├── decorators.py  # 装饰器
│   │   └── validators.py  # 验证器
│   └── errors/            # 错误处理
│       └── handlers.py
├── migrations/            # 数据库迁移
├── tests/                 # 测试目录
├── docker/                # Docker配置
├── uploads/               # 上传文件目录
├── logs/                  # 日志目录
├── requirements.txt       # Python依赖
├── run.py                # 应用入口
├── gunicorn.conf.py      # Gunicorn配置
├── Dockerfile            # Docker镜像
├── docker-compose.yml    # Docker编排
├── alembic.ini           # Alembic配置
├── API文档.md            # API文档
└── 部署指南.md           # 部署文档
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
