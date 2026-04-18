# SmartTable Docker 部署文件清单

## 📁 文件结构

```
smart-table-spec/
├── 📄 Dockerfile                      # 主 Docker 镜像构建文件
├── 📄 docker-compose.yml              # 简化部署配置（SQLite）
├── 📄 docker-compose.full.yml         # 完整部署配置（PostgreSQL+Redis+MinIO）
├── 📄 .env.example                    # 环境变量示例（简单部署）
├── 📄 .env.full.example               # 环境变量示例（完整部署）
├── 📄 .dockerignore                   # Docker 构建忽略文件
├── 📄 start.sh                        # Linux/Mac 启动脚本
├── 📄 start.ps1                       # Windows PowerShell 启动脚本
│
├── 📚 文档
│   ├── DOCKER_DEPLOYMENT.md           # 详细部署指南
│   ├── DOCKER_QUICKSTART.md           # 快速参考指南
│   ├── DOCKER_ARCHITECTURE.md         # 架构设计文档
│   └── DOCKER_FILES.md                # 本文件
│
├── 📂 docker/
│   ├── nginx/
│   │   └── nginx.conf                 # Nginx 配置文件
│   └── supervisor/
│       └── supervisord.conf           # Supervisor 进程管理配置
│
├── 📂 smart-table/                    # 前端项目
│   ├── src/                           # 源代码
│   ├── package.json                   # 前端依赖配置
│   └── vite.config.ts                 # Vite 构建配置
│
└── 📂 smarttable-backend/             # 后端项目
    ├── app/                           # Flask 应用代码
    ├── requirements.txt               # Python 依赖
    ├── run.py                         # 应用启动脚本
    └── gunicorn.conf.py               # Gunicorn 配置
```

## 📋 核心文件说明

### 1. Dockerfile

**位置**: `smart-table-spec/Dockerfile`

**作用**: 多阶段构建 Docker 镜像，包含前后端完整应用

**关键特性**:
- 三阶段构建（前端构建、后端依赖、生产运行）
- 基于 Python 3.11 Slim 镜像
- 集成 Nginx 作为 Web 服务器
- 使用 Supervisor 管理多进程
- 暴露 80 端口

**文件大小**: ~2.5KB

---

### 2. docker-compose.yml

**位置**: `smart-table-spec/docker-compose.yml`

**作用**: 简化版部署配置，使用 SQLite 数据库

**适用场景**:
- 快速测试和演示
- 开发环境
- 小型部署

**包含服务**:
- SmartTable 统一应用（前后端）

**数据持久化**:
- sqlite_data: 数据库文件
- uploads_data: 上传文件

**文件大小**: ~1.5KB

---

### 3. docker-compose.full.yml

**位置**: `smart-table-spec/docker-compose.full.yml`

**作用**: 完整生产环境部署配置

**适用场景**:
- 生产环境
- 高并发场景
- 需要高可用性

**包含服务**:
- PostgreSQL 数据库
- Redis 缓存
- MinIO 对象存储
- SmartTable 统一应用

**特性**:
- 健康检查
- 资源限制
- 服务依赖管理
- 数据持久化

**文件大小**: ~3.5KB

---

### 4. .env.example

**位置**: `smart-table-spec/.env.example`

**作用**: 简单部署的环境变量模板

**包含配置**:
- 应用端口
- Flask 密钥
- JWT 密钥
- 数据库配置（SQLite）
- 上传配置

**使用方法**:
```bash
cp .env.example .env
# 编辑 .env 文件修改配置
```

**文件大小**: ~1KB

---

### 5. .env.full.example

**位置**: `smart-table-spec/.env.full.example`

**作用**: 完整部署的环境变量模板

**包含配置**:
- 应用配置
- 安全密钥
- PostgreSQL 配置
- Redis 配置
- MinIO 配置
- 上传配置

**文件大小**: ~2KB

---

### 6. .dockerignore

**位置**: `smart-table-spec/.dockerignore`

**作用**: 指定 Docker 构建时需要忽略的文件

**忽略内容**:
- Git 相关文件
- Python 缓存文件
- Node.js 模块
- IDE 配置
- 文档和测试文件
- 本地数据库和日志

**文件大小**: ~500B

---

### 7. docker/nginx/nginx.conf

**位置**: `smart-table-spec/docker/nginx/nginx.conf`

**作用**: Nginx 服务器配置

**功能**:
- 静态文件服务
- API 反向代理
- Gzip 压缩
- 安全头设置
- 性能优化

**关键配置**:
- 监听端口：80
- 静态文件根目录：/app/static
- API 代理目标：Gunicorn:5000
- 最大上传大小：50MB

**文件大小**: ~2.5KB

---

### 8. docker/supervisor/supervisord.conf

**位置**: `smart-table-spec/docker/supervisor/supervisord.conf`

**作用**: Supervisor 进程管理配置

**管理进程**:
1. Nginx（优先级 10）
2. Gunicorn（优先级 20）

**特性**:
- 自动重启
- 日志管理
- 进程依赖
- 资源限制

**文件大小**: ~800B

---

### 9. start.sh

**位置**: `smart-table-spec/start.sh`

**作用**: Linux/Mac 快速启动脚本

**功能**:
- 检查 Docker 安装
- 检查 Docker Compose 安装
- 创建环境变量文件
- 选择部署模式
- 自动构建和启动

**使用**:
```bash
chmod +x start.sh
./start.sh
```

**文件大小**: ~2KB

---

### 10. start.ps1

**位置**: `smart-table-spec/start.ps1`

**作用**: Windows PowerShell 快速启动脚本

**功能**: 与 start.sh 相同，适配 Windows 环境

**使用**:
```powershell
.\start.ps1
```

**文件大小**: ~3KB

---

## 📚 文档文件

### 1. DOCKER_DEPLOYMENT.md

**位置**: `smart-table-spec/DOCKER_DEPLOYMENT.md`

**内容**:
- 系统要求
- 快速开始指南
- 详细部署步骤
- 配置说明
- 常见问题解答
- 维护指南

**适合人群**: 所有用户

**文件大小**: ~15KB

---

### 2. DOCKER_QUICKSTART.md

**位置**: `smart-table-spec/DOCKER_QUICKSTART.md`

**内容**:
- 快速启动命令
- 常用操作
- 故障排查
- 快速参考

**适合人群**: 有经验的用户

**文件大小**: ~3KB

---

### 3. DOCKER_ARCHITECTURE.md

**位置**: `smart-table-spec/DOCKER_ARCHITECTURE.md`

**内容**:
- 架构设计图
- 镜像结构
- 请求流程
- 数据持久化
- 安全架构
- 资源分配
- 高可用方案
- 性能优化

**适合人群**: 架构师、运维工程师

**文件大小**: ~12KB

---

### 4. DOCKER_FILES.md (本文件)

**位置**: `smart-table-spec/DOCKER_FILES.md`

**内容**:
- 完整文件清单
- 每个文件的详细说明
- 文件大小
- 使用场景

**适合人群**: 需要了解项目结构的用户

**文件大小**: ~10KB

---

## 🔧 配置文件关系

```
┌─────────────────────────────────────┐
│         用户选择部署模式             │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐ ┌──────▼──────┐
│  简单部署   │ │  完整部署   │
└──────┬──────┘ └──────┬──────┘
       │               │
       │               │
┌──────▼──────────────▼──────┐
│   复制对应的.env 文件       │
│   - .env.example           │
│   - .env.full.example      │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│   运行启动脚本或命令        │
│   - ./start.sh             │
│   - ./start.ps1            │
│   - docker compose up      │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│   Docker 读取配置文件       │
│   - Dockerfile             │
│   - docker-compose.yml     │
│   - docker-compose.full.yml│
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│   构建镜像                  │
│   - 使用.dockerignore      │
│   - 多阶段构建             │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│   启动容器                  │
│   - 使用 supervisord.conf  │
│   - 使用 nginx.conf        │
└────────────────────────────┘
```

---

## 📊 文件大小统计

| 文件类型 | 数量 | 总大小 |
|---------|------|--------|
| Docker 配置 | 3 | ~5.5KB |
| 环境变量 | 2 | ~3KB |
| 脚本 | 2 | ~5KB |
| 文档 | 4 | ~40KB |
| Nginx/Supervisor | 2 | ~3.3KB |
| **总计** | **13** | **~56.8KB** |

---

## 🎯 使用建议

### 快速开始
1. 阅读 `DOCKER_QUICKSTART.md`
2. 运行 `./start.sh` 或 `.\start.ps1`

### 详细部署
1. 阅读 `DOCKER_DEPLOYMENT.md`
2. 根据需要选择配置文件
3. 按照步骤操作

### 了解架构
1. 阅读 `DOCKER_ARCHITECTURE.md`
2. 理解系统设计和数据流

### 参考文件
1. 查阅 `DOCKER_FILES.md`（本文件）
2. 了解每个文件的作用

---

**所有文件都经过精心设计，确保 Docker 部署的简单性和可靠性！** 🚀
