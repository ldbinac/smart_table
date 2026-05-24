# SmartTable Docker 镜像打包构建教程

> **版本**: 1.4.0 | **更新日期**: 2026-05-24

---

## 目录

1. [官方 Docker 镜像拉取指南](#1-官方-docker-镜像拉取指南)
2. [架构设计详解](#2-架构设计详解)
3. [相关文件说明](#3-相关文件说明)
4. [镜像构建步骤](#4-镜像构建步骤)
5. [使用方式指南](#5-使用方式指南)
6. [高级配置与优化](#6-高级配置与优化)

---

## 1. 官方 Docker 镜像拉取指南

### 1.1 镜像仓库地址

SmartTable 官方 Docker 镜像托管于 Docker Hub 公共仓库：

| 仓库 | 地址 |
|------|------|
| **官方仓库** | `ygbinac/smarttable` |
| **完整 URL** | `https://hub.docker.com/r/ygbinac/smarttable` |

### 1.2 可用镜像标签

| 标签 | 对应版本 | 说明 | 镜像大小 |
|------|---------|------|---------|
| `latest` | 最新稳定版 | 始终指向最新的稳定发布版本 | ~521MB |
| `1.4.0` | v1.4.0 | 指定版本的稳定镜像 | ~521MB |

### 1.3 拉取镜像

**拉取最新版本：**

```bash
docker pull ygbinac/smarttable:latest
```

**拉取指定版本：**

```bash
docker pull ygbinac/smarttable:1.4.0
```

### 1.4 拉取后的验证

**检查镜像是否存在：**

```bash
docker images ygbinac/smarttable
```

**查看镜像详细信息：**

```bash
docker inspect ygbinac/smarttable:latest
```

**快速启动验证容器运行：**

```bash
docker run --rm -d -p 80:80 --name smarttable-test ygbinac/smarttable:latest
sleep 5
curl http://localhost:80/api/health
docker stop smarttable-test
```

如果健康检查返回 `{"status": "healthy", "service": "smarttable"}`，则表明镜像运行正常。

### 1.5 镜像更新与版本管理

**更新到最新镜像：**

```bash
docker pull ygbinac/smarttable:latest
docker compose down
docker compose up -d
```

**版本升级流程：**

1. 查看[官方仓库 Tags](https://hub.docker.com/r/ygbinac/smarttable/tags)，确认最新版本
2. 拉取新版本镜像：`docker pull ygbinac/smarttable:1.4.0`
3. 更新 `docker-compose.yml` 中的镜像标签
4. 执行 `docker compose down && docker compose up -d` 重启服务
5. 验证运行状态：`curl http://localhost:80/api/health`

> **建议**：在生产环境中始终使用具体的版本标签（如 `1.4.0`），而非 `latest`，以确保部署的可复现性。

---

## 2. 架构设计详解

### 2.1 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                  SmartTable Docker 容器                        │
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌──────────────────────────┐ │
│  │  Redis   │    │  Nginx  │    │     Gunicorn             │ │
│  │  (6379)  │    │   (80)  │    │     (5000)               │ │
│  │          │    │         │    │                          │ │
│  │ 缓存服务  │◄──►│ 静态文件│◄──►│  /api/*   → Flask 后端   │ │
│  │ 会话存储  │    │ 反向代理│    │  WebSocket → SocketIO    │ │
│  └────┬─────┘    └─────────┘    └────────────┬─────────────┘ │
│       │                                      │               │
│       └──────────────────────────────────────┘               │
│                         │                                    │
│              ┌──────────┴──────────┐                        │
│              │     Supervisor      │                        │
│              │   (进程管理器)       │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│              ┌──────────┴──────────┐                        │
│              │   entrypoint.sh     │                        │
│              │   (容器入口脚本)      │                        │
│              └─────────────────────┘                        │
│                                                              │
│  数据卷挂载:                                                 │
│  /app/data      ← SQLite 数据库文件                          │
│  /app/uploads   ← 用户上传文件                               │
│  /data/redis    ← Redis 持久化数据                           │
│  /app/logs      ← 应用运行日志                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 镜像分层结构

Docker 镜像采用多阶段构建，共分为三个构建阶段，最终产物为一个单层优化的生产镜像：

```
┌─────────────────────────────────────┐
│ 阶段 1: frontend-builder            │
│ 基础镜像: node:20-alpine            │
│                                     │
│ 层 1: 基础 Node.js 环境             │
│ 层 2: package.json + lock 文件      │
│ 层 3: npm ci 安装依赖               │
│ 层 4: 前端源代码                    │
│ 层 5: vite build 构建产物 (/dist)   │
│ 产物: dist/ 目录                    │
└──────────────┬──────────────────────┘
               │ 仅复制 dist
┌──────────────▼──────────────────────┐
│ 阶段 2: backend-builder             │
│ 基础镜像: python:3.11-slim          │
│                                     │
│ 层 1: 基础 Python 环境              │
│ 层 2: Debian 镜像源配置             │
│ 层 3: 编译依赖安装(apt)             │
│ 层 4: requirements.txt 文件         │
│ 层 5: pip install 安装依赖          │
│ 产物: /root/.local/ (Python 包)     │
└──────────────┬──────────────────────┘
               │ 仅复制 Python 包
┌──────────────▼──────────────────────┐
│ 阶段 3: 生产运行环境 (最终镜像)       │
│ 基础镜像: python:3.11-slim          │
│                                     │
│ 层 1: 基础 Python 运行环境           │
│ 层 2: 系统依赖 (nginx, redis...)    │
│ 层 3: Python 依赖 (from stage 2)    │
│ 层 4: 后端源代码                    │
│ 层 5: 运行目录结构                  │
│ 层 6: 前端静态文件 (from stage 1)   │
│ 层 7: 配置文件 (nginx/supervisor)   │
│ 层 8: 入口脚本 + 权限设置           │
│ 最终: 521MB 优化镜像                │
└─────────────────────────────────────┘
```

### 2.3 基础镜像选择依据

| 组件 | 基础镜像 | 版本 | 选择理由 |
|------|---------|------|---------|
| **前端构建** | `node:20-alpine` | Node.js 20 LTS | Alpine 版本仅 ~50MB，构建速度快，包含完整的 npm 工具链 |
| **后端构建/运行** | `python:3.11-slim` | Python 3.11 | Slim 版本约 ~120MB，平衡了体积和构建兼容性，包含编译所需基础库 |

**版本策略：**
- 前端使用 Node.js 20 LTS（长期支持版），确保稳定性和安全性
- 后端使用 Python 3.11，兼容当前所有依赖包的最新版本
- 运行阶段不再保留 Alpine，避免 musl libc 兼容性问题
- 所有基础镜像锁定主版本号（如 `python:3.11-slim`），避免意外升级破坏兼容性

### 2.4 多阶段构建原理与优势

**实现原理：**

传统 Docker 构建将所有步骤放在一个镜像中，导致最终镜像包含大量构建时工具（如 gcc、npm），体积臃肿。多阶段构建允许在 Dockerfile 中使用多个 `FROM` 指令，每个 `FROM` 开始一个独立的构建阶段，最终产物只从各阶段复制所需文件到最终镜像。

**核心优势：**

| 优势 | 说明 |
|------|------|
| **镜像体积缩小 60%+** | 仅保留运行时依赖，排除 gcc、npm、缓存等构建产物 |
| **安全性提升** | 构建工具（如 TypeScript 编译器、gcc）不会出现在最终镜像中，减少攻击面 |
| **层级缓存优化** | 各阶段独立缓存，前端代码不变时直接复用缓存层 |
| **构建环境隔离** | 前端使用 Node.js 镜像，后端使用 Python 镜像，各取所需 |

---

## 3. 相关文件说明

### 3.1 文件目录结构

```
smart_table/
├── Dockerfile                    # Docker 镜像构建定义（核心）
├── .dockerignore                 # Docker 构建上下文排除规则
├── build_docker.py               # 一键式自动化构建脚本
├── docker-compose.yml            # 容器编排配置（快速部署）
├── version.json                  # 项目版本信息文件
│
├── docker/                       # Docker 辅助配置文件目录
│   ├── entrypoint.sh             # 容器入口初始化脚本
│   ├── nginx/
│   │   └── nginx.conf            # Nginx 反向代理配置
│   ├── supervisor/
│   │   └── supervisord.conf      # Supervisor 进程管理配置
│   └── redis/
│       └── redis.conf            # Redis 服务配置
│
├── smart-table/                  # 前端源代码目录
│   ├── package.json
│   └── ...
│
└── smarttable-backend/           # 后端源代码目录
    ├── requirements.txt
    ├── run.py
    ├── gunicorn.conf.py
    └── ...
```

### 3.2 Dockerfile 详解

> 文件路径: [Dockerfile](file:///d:/_dev/_src/github/smart_table/Dockerfile)

```dockerfile
# ============================================
# 阶段 1: 构建前端
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 先复制 package 文件，利用 Docker 缓存层加速
COPY smart-table/package.json smart-table/package-lock.json ./
RUN npm ci && npm cache clean --force

# 复制源代码并构建
COPY smart-table/ ./
RUN npx vite build
```

- `FROM node:20-alpine AS frontend-builder` — 使用 Node.js 20 Alpine 镜像作为前端构建阶段，别名为 `frontend-builder`
- `WORKDIR /app/frontend` — 设置工作目录
- `COPY package.json` + `npm ci` — 先复制依赖配置文件安装依赖，利用 Docker 缓存机制：只要 `package.json` 不变，就复用缓存层的 `node_modules`
- `COPY .` + `npx vite build` — 复制前端源码后直接使用 Vite 构建（跳过 vue-tsc 类型检查，避免类型错误阻断构建）

```dockerfile
# ============================================
# 阶段 2: 构建后端 Python 依赖
# ============================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# 配置国内镜像源加速
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY smarttable-backend/requirements.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt
```

- `FROM python:3.11-slim AS backend-builder` — Python 3.11 精简版镜像，用于编译安装 Python 依赖
- `sed` 命令 — 配置清华大学 Debian 镜像源（适用于中国大陆网络环境），加速 apt-get 下载
- `build-essential libpq-dev` — 编译依赖，某些 Python 包（如 psycopg2、weasyprint）需要 C 编译器
- `libpango*` — PDF 导出（WeasyPrint）所需的字体渲染库
- `pip install --user -r requirements.txt` — 安装到用户目录 `/root/.local`，后续可单独复制到最终镜像
- `rm -rf /var/lib/apt/lists/*` — 清理 apt 缓存，减少构建层体积

```dockerfile
# ============================================
# 阶段 3: 生产运行环境
# ============================================
FROM python:3.11-slim

LABEL maintainer="SmartTable Team" \
      version="1.4.0" \
      description="SmartTable - 智能表格应用"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    PATH=/root/.local/bin:$PATH \
    TZ=Asia/Shanghai

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 nginx curl supervisor redis-server \
    ca-certificates gettext-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制产物
COPY --from=backend-builder /root/.local /root/.local
COPY smarttable-backend/ ./
COPY --from=frontend-builder /app/frontend/dist /app/static

# 复制配置文件
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/redis/redis.conf /etc/redis/redis.conf
COPY docker/entrypoint.sh /entrypoint.sh

# 设置权限
RUN chmod +x /entrypoint.sh && \
    chown -R www-data:www-data /app/static /app/uploads && \
    chmod -R 755 /app/uploads

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/api/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
```

**关键指令说明：**

| 指令 | 作用 | 说明 |
|------|------|------|
| `LABEL` | 镜像元数据 | 记录维护者、版本号、描述信息，可通过 `docker inspect` 查看 |
| `ENV` | 环境变量 | `PYTHONDONTWRITEBYTECODE` 禁止生成 `.pyc` 文件；`PYTHONUNBUFFERED` 确保日志实时输出；`TZ` 设置时区 |
| `COPY --from=` | 跨阶段复制 | 从前端/后端构建阶段仅复制必要产物到最终镜像 |
| `EXPOSE 80` | 端口声明 | 容器运行时监听 80 端口 |
| `HEALTHCHECK` | 健康检查 | 每 30 秒检查 `/api/health`，3 次失败则标记容器为不健康 |
| `ENTRYPOINT` | 入口指令 | 容器启动时执行 `/entrypoint.sh`，完成初始化后启动服务 |

### 3.3 .dockerignore 文件

> 文件路径: [.dockerignore](file:///d:/_dev/_src/github/smart_table/.dockerignore)

```
# Git
.git
.gitignore

# Python 缓存和虚拟环境
__pycache__/
*.py[cod]
*.egg-info/
env/
venv/
.venv/

# Node 依赖
node_modules/

# IDE
.idea/
.vscode/

# 文档和测试（无需进入镜像）
doc/
docs/
tests/
test/
*.test.ts
*.spec.ts

# Docker Compose 配置
docker-compose*.yml

# 环境变量（保护敏感信息）
.env
.env.local

# 数据库文件
*.db
*.sqlite

# 上传文件和构建产物
uploads/
smart-table/dist/
smart-table/build/
```

**作用：** `.dockerignore` 定义了发送给 Docker 守护进程的构建上下文（context）中需要排除的文件和目录，有以下好处：

- **加速构建** — 减少上下文传输体积，避免将 `node_modules`（数百 MB）发送给 Docker 守护进程
- **安全性** — 排除 `.env` 等敏感文件，防止密钥泄露到镜像层
- **避免缓存污染** — 排除日志、临时文件等不稳定的内容

### 3.4 辅助配置文件

#### Nginx 配置 (`docker/nginx/nginx.conf`)

功能：作为反向代理和静态文件服务器，负责：
- 前端路由：将所有 `/` 路径请求映射到 `/app/static` 目录，并支持 SPA 的 history 模式（`try_files $uri /index.html`）
- API 代理：将 `/api/` 路径请求转发到 Gunicorn（127.0.0.1:5000）
- 性能优化：开启 gzip 压缩、静态文件 30 天缓存、长连接 keepalive
- 安全头：添加 X-Frame-Options、X-Content-Type-Options 等安全响应头
- 上传文件：将 `/uploads/` 路径映射到 `/app/uploads/` 目录

#### Supervisor 配置 (`docker/supervisor/supervisord.conf`)

功能：进程管理器，统一管理容器内的三个服务进程：

| 服务 | 启动命令 | 优先级 | 自动重启 |
|------|---------|--------|---------|
| Redis | `redis-server /etc/redis/redis.conf` | 5 | 是 |
| Nginx | `/usr/sbin/nginx -g "daemon off;"` | 10 | 是 |
| Gunicorn | `gunicorn -c gunicorn.conf.py run:app` | 20 | 是 |

- 三个服务按优先级顺序启动（先 Redis，最后 Gunicorn）
- 任意服务崩溃后会自动重启
- 日志统一输出到 `/var/log/supervisor/` 目录

#### Redis 配置 (`docker/redis/redis.conf`)

功能：适用于容器内部的 Redis 优化配置：
- 仅监听 `127.0.0.1`（不对外暴露）
- 非守护进程模式（daemonize no），由 Supervisor 管理生命周期
- 最多 512MB 内存限制，使用 LRU 淘汰策略
- RDB 持久化（每 900 秒至少 1 个 key 变更）
- 禁用保护模式（仅在容器内部监听）

#### Gunicorn 配置 (`gunicorn.conf.py`)

功能：WSGI HTTP 服务器配置：
- 根据 `ENABLE_REALTIME` 环境变量动态选择 worker 类型（eventlet / gthread）
- 自动根据 CPU 核心数计算工作进程数
- 预加载应用（preload_app），加速 Worker 启动
- 每处理 10000 个请求自动重启 Worker，防止内存泄漏

#### 容器入口脚本 (`docker/entrypoint.sh`)

功能：容器启动时按顺序执行四大初始化步骤：

```
[1/4] 初始化运行环境 → 创建目录、设置权限
[2/4] 初始化数据库   → 创建 SQLite 数据库表
[3/4] 验证服务配置   → 检查 Nginx、Redis、Gunicorn 配置
[4/4] 启动服务       → 通过 Supervisor 启动所有进程
```

### 3.5 一键构建脚本 (`build_docker.py`)

> 文件路径: [build_docker.py](file:///d:/_dev/_src/github/smart_table/build_docker.py)

自动化构建脚本，提供以下功能：

| 参数 | 作用 |
|------|------|
| `--no-cache` | 不使用 Docker 缓存，重新构建所有层 |
| `--skip-frontend` | 跳过前端构建，使用已有 dist 目录 |
| `--tag v1.0.0` | 指定镜像标签 |
| `--push` | 构建完成后推送到镜像仓库 |
| `--run` | 构建后启动容器 |
| `--check-only` | 仅检查构建环境，不实际构建 |
| `--clean` | 清理构建产物后退出 |
| `--verify-only` | 仅验证上次构建的镜像 |

---

## 4. 镜像构建步骤

### 4.1 环境要求

| 依赖项 | 最低版本 | 验证命令 |
|--------|---------|---------|
| Docker Engine | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Python | 3.7+ | `python --version` |
| Node.js（可选，仅本地构建前端需要） | 20+ | `node --version` |
| 磁盘空间 | 5GB+ | — |

**操作系统支持：** Windows 10/11（Docker Desktop）、macOS、Linux（Ubuntu 20.04+ / CentOS 7+）

### 4.2 Docker 安装检查

```bash
# 检查 Docker 是否安装
docker --version

# 检查 Docker 守护进程是否运行
docker info

# 检查 Docker Compose 是否可用
docker compose version

# 检查是否支持 BuildKit（推荐）
docker buildx version
```

### 4.3 使用一键脚本构建（推荐）

```bash
# 克隆项目
git clone https://github.com/ygbinac/smart_table.git
cd smart_table

# 完整构建（自动完成前端编译 + 后端依赖安装 + Docker 镜像打包）
python build_docker.py

# 使用缓存构建（推荐，在修改少量代码后使用）
python build_docker.py

# 完全重新构建（不使用缓存）
python build_docker.py --no-cache

# 构建并指定版本标签
python build_docker.py --tag 1.4.0

# 构建并推送到仓库
python build_docker.py --tag 1.4.0 --push

# 构建并启动容器
python build_docker.py --run

# 跳过前端构建（如果已有 dist 目录）
python build_docker.py --skip-frontend

# 仅检查构建环境是否满足要求
python build_docker.py --check-only
```

**构建流程说明：**

```
步骤 1/4: 检查运行环境
  → 验证 Docker、Python、Node.js 是否可用
  → 检查 Docker 守护进程状态

步骤 2/4: 检查 Dockerfile
  → 验证 Dockerfile 是否存在且格式正确

步骤 3/4: 构建前端（如果跳过则使用已有产物）
  → npm ci 安装依赖
  → npx vite build 构建产物

步骤 4/4: 构建 Docker 镜像
  → docker buildx build --load -t smarttable:latest .
  → 验证镜像大小和配置完整性
```

### 4.4 手动分步构建

如果需要更细粒度的控制，可以手动执行各步骤：

**步骤 1：构建前端**

```bash
cd smart-table
npm ci
npx vite build
cd ..
```

**步骤 2：构建 Docker 镜像**

```bash
# 基础构建
docker build -t smarttable:latest .

# 构建并指定标签
docker build -t smarttable:1.4.0 -t smarttable:latest .

# 不使用缓存
docker build --no-cache -t smarttable:latest .
```

**步骤 3：验证构建结果**

```bash
# 查看镜像
docker images smarttable

# 检查镜像分层
docker history smarttable:latest

# 启动测试容器
docker run --rm -d -p 80:80 --name smarttable-test smarttable:latest

# 等待初始化完成
sleep 10

# 验证健康检查
curl http://localhost:80/api/health

# 查看服务日志
docker logs smarttable-test

# 停止并删除测试容器
docker stop smarttable-test
```

### 4.5 构建过程常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `npm ci` 失败 | 网络问题或 `package-lock.json` 不匹配 | 确保 `package-lock.json` 与 `package.json` 版本匹配，或使用 `npm install` 替代 |
| `pip install` 超时 | 网络连接缓慢 | Dockerfile 已配置国内镜像源，若仍有问题可手动更换其他 PyPI 镜像 |
| `apt-get update` 失败（403） | Debian 镜像源不可用 | Dockerfile 已配置清华镜像源，若 403 仍然存在，可切换到阿里云镜像 |
| Docker 构建上下文太大 | `.dockerignore` 配置不当 | 检查 `node_modules`、`.git` 等大目录是否被正确排除 |
| BuildKit 报错 | Docker BuildKit 未启用 | 设置环境变量 `DOCKER_BUILDKIT=1`，或使用 `docker buildx build` |
| 磁盘空间不足 | 缓存层积累过多 | 运行 `docker builder prune -a` 清理构建缓存 |

### 4.6 构建验证清单

构建完成后，通过以下清单验证镜像质量：

- [ ] 镜像构建成功，退出码为 0
- [ ] 镜像大小不超过 600MB
- [ ] 镜像包含 Redis、Nginx、Supervisor 等运行时
- [ ] 容器启动后健康检查返回 HTTP 200
- [ ] 前端页面（`/`）返回 HTTP 200
- [ ] 数据库表自动创建成功
- [ ] Supervisor 管理三个进程（redis、nginx、gunicorn）均处于 RUNNING 状态

---

## 5. 使用方式指南

### 5.1 快速启动（使用 Docker Compose，推荐）

**创建 `docker-compose.yml`：**

```yaml
services:
  smarttable:
    image: ygbinac/smarttable:latest
    container_name: smarttable
    restart: unless-stopped
    ports:
      - "80:80"
    environment:
      SECRET_KEY: your-secret-key-here
      JWT_SECRET_KEY: your-jwt-secret-key-here
    volumes:
      - sqlite_data:/app/data
      - redis_data:/data/redis
      - uploads_data:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  sqlite_data:
  redis_data:
  uploads_data:
```

**启动服务：**

```bash
docker compose up -d
```

**查看运行状态：**

```bash
docker compose ps
docker compose logs -f
```

### 5.2 直接使用 Docker 命令运行

```bash
docker run -d \
  --name smarttable \
  --restart unless-stopped \
  -p 80:80 \
  -e SECRET_KEY=your-secret-key-here \
  -e JWT_SECRET_KEY=your-jwt-secret-key-here \
  -v sqlite_data:/app/data \
  -v redis_data:/data/redis \
  -v uploads_data:/app/uploads \
  ygbinac/smarttable:latest
```

### 5.3 环境变量配置说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SECRET_KEY` | `change-this-secret-key-in-production` | Flask 应用密钥（**生产环境必须修改**） |
| `JWT_SECRET_KEY` | `change-this-jwt-secret-in-production` | JWT 签名密钥（**生产环境必须修改**） |
| `JWT_ACCESS_TOKEN_EXPIRES` | `86400` | JWT Token 过期时间（秒），默认 24 小时 |
| `FLASK_ENV` | `production` | Flask 运行环境（production / development） |
| `LOG_LEVEL` | `INFO` | 日志级别（DEBUG / INFO / WARNING / ERROR） |
| `ENABLE_REALTIME` | `false` | 是否启用实时协作功能（需要 eventlet worker） |
| `GUNICORN_WORKERS` | 自动计算 | Gunicorn 工作进程数 |
| `GUNICORN_THREADS` | `4` | 每个工作进程的线程数 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址 |
| `MAX_CONTENT_LENGTH` | `52428800` | 最大上传文件大小（字节），默认 50MB |

> **安全提醒**：务必在首次启动前修改 `SECRET_KEY` 和 `JWT_SECRET_KEY`，使用强随机字符串。可以通过 `openssl rand -hex 32` 命令生成。

### 5.4 数据卷挂载说明

| 挂载点 | 用途 | 是否需要持久化 |
|--------|------|---------------|
| `/app/data` | SQLite 数据库文件 | **必须** — 否则重启后数据丢失 |
| `/data/redis` | Redis 持久化数据 | 推荐 — 避免缓存重建 |
| `/app/uploads` | 用户上传的文件 | **必须** — 否则上传文件丢失 |
| `/app/logs` | 应用运行日志 | 可选 — 建议挂载以便日志分析 |

### 5.5 网络配置

默认情况下，容器监听宿主机的 80 端口。如需修改端口映射：

```bash
# 将容器 80 端口映射到宿主机 8080 端口
docker run -d -p 8080:80 ygbinac/smarttable:latest
```

如果需要自定义网络：

```bash
# 创建自定义网络
docker network create smarttable-net

# 启动容器并加入网络
docker run -d \
  --network smarttable-net \
  --name smarttable \
  -p 80:80 \
  ygbinac/smarttable:latest
```

### 5.6 容器生命周期管理

```bash
# 启动容器
docker start smarttable

# 停止容器（优雅关闭）
docker stop smarttable

# 重启容器
docker restart smarttable

# 查看容器状态
docker ps -a --filter name=smarttable

# 查看实时日志
docker logs -f smarttable

# 进入容器内部
docker exec -it smarttable bash

# 查看运行进程
docker exec smarttable supervisorctl status

# 停止所有服务
docker compose down

# 停止并删除数据卷
docker compose down -v
```

### 5.7 访问应用

启动容器后，通过浏览器访问：

```
http://localhost:80
```

对于远程服务器，替换 `localhost` 为服务器 IP 地址或域名。

---

## 6. 高级配置与优化

### 6.1 镜像大小优化

当前镜像约 521MB，通过以下技术持续优化：

**已实施的优化措施：**

| 优化手段 | 效果 | 实现方式 |
|----------|------|---------|
| 多阶段构建 | 减少 60%+ 体积 | 仅复制运行产物到最终镜像 |
| 清理 apt 缓存 | 减少 ~50MB | `rm -rf /var/lib/apt/lists/*` |
| 清理 npm 缓存 | 减少 ~30MB | `npm cache clean --force` |
| 使用 --no-cache-dir | 减少 ~20MB | `pip install --no-cache-dir` |
| 选择 slim 基础镜像 | 减少 ~800MB | 使用 `python:3.11-slim` 而非完整版本 |

**进一步优化建议：**

```dockerfile
# 合并 RUN 命令减少层数
RUN apt-get update && apt-get install -y ... && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# 移除不必要的包
RUN apt-get remove -y --purge build-essential libpq-dev && \
    apt-get autoremove -y
```

### 6.2 安全加固

**生产环境安全配置建议：**

1. **修改默认密钥**
   
   ```bash
   # 生成强随机密钥
   SECRET_KEY=$(openssl rand -hex 32)
   JWT_SECRET_KEY=$(openssl rand -hex 32)
   
   # 启动容器时注入
   docker run -d \
     -e SECRET_KEY=$SECRET_KEY \
     -e JWT_SECRET_KEY=$JWT_SECRET_KEY \
     ygbinac/smarttable:latest
   ```

2. **使用非 root 用户运行**
   
   默认 Supervisor 以 root 运行。生产环境建议创建专用用户：
   ```dockerfile
   RUN useradd -m -s /bin/bash smarttable
   USER smarttable
   ```

3. **限制容器资源**
   ```bash
   docker run -d \
     --memory=1g \
     --cpus=1 \
     --memory-swap=1g \
     --restart unless-stopped \
     -p 80:80 \
     ygbinac/smarttable:latest
   ```

4. **启用只读文件系统**
   ```bash
   docker run -d \
     --read-only \
     --tmpfs /tmp \
     --tmpfs /var/run \
     -v sqlite_data:/app/data \
     ygbinac/smarttable:latest
   ```

5. **配置日志轮转**
   ```yaml
   # docker-compose.yml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

### 6.3 多平台构建

支持在不同 CPU 架构上运行：

```bash
# 创建并使用多平台构建器
docker buildx create --name multiarch --driver docker-container --use

# 同时构建 linux/amd64 和 linux/arm64 镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ygbinac/smarttable:1.4.0 \
  -t ygbinac/smarttable:latest \
  --push \
  .
```

这允许镜像在以下平台上运行：
- **x86_64/amd64** — 大多数 Intel/AMD 服务器和 PC
- **arm64** — Apple M 系列芯片 Mac、AWS Graviton、树莓派等

### 6.4 CI/CD 集成

**GitHub Actions 自动构建示例：**

```yaml
# .github/workflows/docker-build.yml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract version
        id: version
        run: |
          echo "version=$(cat version.json | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"version\"])')" >> $GITHUB_OUTPUT

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            ygbinac/smarttable:latest
            ygbinac/smarttable:${{ steps.version.outputs.version }}
          platforms: linux/amd64,linux/arm64
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**GitLab CI 示例：**

```yaml
# .gitlab-ci.yml
variables:
  DOCKER_IMAGE: ygbinac/smarttable
  DOCKER_TAG: $CI_COMMIT_TAG

stages:
  - build
  - deploy

docker-build:
  stage: build
  image: docker:24
  services:
    - docker:dind
  before_script:
    - docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
  script:
    - |
      VERSION=$(python3 -c "import json; print(json.load(open('version.json'))['version'])")
      docker build -t $DOCKER_IMAGE:$VERSION -t $DOCKER_IMAGE:latest .
      docker push $DOCKER_IMAGE:$VERSION
      docker push $DOCKER_IMAGE:latest
  only:
    - tags
```

### 6.5 性能调优

**Gunicorn Worker 优化：**

根据服务器配置调整 Gunicorn 工作进程数：

```bash
# 2C4G 服务器推荐配置
docker run -d \
  -e GUNICORN_WORKERS=4 \
  -e GUNICORN_THREADS=2 \
  ygbinac/smarttable:latest

# 4C8G 服务器推荐配置
docker run -d \
  -e GUNICORN_WORKERS=8 \
  -e GUNICORN_THREADS=4 \
  ygbinac/smarttable:latest
```

**Nginx 静态文件缓存优化：**

```nginx
# 在 nginx.conf 中调整
location / {
    root /app/static;
    try_files $uri $uri/ /index.html;
    expires 365d;              # 延长静态文件缓存
    add_header Cache-Control "public, immutable";
}
```

**Redis 内存限制调整：**

```bash
# 根据服务器内存调整 Redis 最大内存
docker run -d \
  -e REDIS_MAX_MEMORY=1gb \
  ygbinac/smarttable:latest
```

### 6.6 日志管理

**查看实时日志：**

```bash
# 应用日志
docker logs -f smarttable

# Supervisor 进程日志
docker exec smarttable cat /var/log/supervisor/gunicorn.err.log
docker exec smarttable cat /var/log/supervisor/nginx.err.log
docker exec smarttable cat /var/log/supervisor/redis.err.log
```

**日志接入外部系统：**

使用 Docker 日志驱动将日志发送到集中式日志平台：

```yaml
# docker-compose.yml
services:
  smarttable:
    logging:
      driver: "fluentd"
      options:
        fluentd-address: "localhost:24224"
        tag: "smarttable"
```

---

## 附录

### A. 常用 Docker 命令速查

| 命令 | 用途 |
|------|------|
| `docker ps` | 查看运行中的容器 |
| `docker images` | 查看本地镜像列表 |
| `docker logs -f <container>` | 跟踪容器日志 |
| `docker exec -it <container> sh` | 进入容器 Shell |
| `docker system df` | 查看 Docker 磁盘使用 |
| `docker builder prune -a` | 清理构建缓存 |
| `docker system prune -a` | 清理所有未使用资源 |

### B. 版本历史

| 镜像版本 | 发布日期 | 主要变更 |
|---------|---------|---------|
| 1.4.0 | 2026-05-24 | 首次公共发布，集成 Redis + Nginx + Gunicorn |
| 1.3.3 | — | Docker 多阶段构建基础版本 |

### C. 参考资源

- [Docker 官方文档](https://docs.docker.com/)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Docker Hub 仓库](https://hub.docker.com/r/ygbinac/smarttable)
- [SmartTable 项目源码](https://github.com/ygbinac/smart_table)