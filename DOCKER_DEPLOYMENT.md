# SmartTable Docker 部署指南

本指南将帮助您使用 Docker 快速部署 SmartTable 多维表格管理系统。

## 📋 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [维护指南](#维护指南)

---

## 🖥️ 系统要求

### 硬件要求
- **CPU**: 2 核心或更高
- **内存**: 2GB RAM 或更高（推荐 4GB）
- **磁盘**: 至少 5GB 可用空间

### 软件要求
- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本（可选，但推荐）

### 检查 Docker 安装

```bash
# 检查 Docker 版本
docker --version

# 检查 Docker Compose 版本
docker compose version

# 或者（旧版本）
docker-compose --version
```

如果未安装 Docker，请参考 [Docker 官方安装指南](https://docs.docker.com/get-docker/)

---

## 🚀 快速开始

### 1. 克隆项目（如果还没有）

```bash
cd D:\_dev\fs_table\smart-table-spec
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 在 Windows PowerShell 中
Copy-Item .env.example .env
```

### 3. 构建并启动

```bash
# 使用 Docker Compose（推荐）
docker compose up -d --build

# 或者使用单条 Docker 命令
docker build -t smarttable . && docker run -d -p 80:80 --name smarttable smarttable
```

### 4. 访问应用

打开浏览器访问：http://localhost

**恭喜！部署完成！** 🎉

---

## 📝 详细部署步骤

### 步骤 1: 准备环境

#### 1.1 安装 Docker Desktop（Windows）

1. 下载 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. 运行安装程序
3. 启用 WSL 2 功能（推荐）
4. 重启电脑

#### 1.2 验证安装

```bash
docker run hello-world
```

如果看到欢迎信息，说明 Docker 安装成功。

### 步骤 2: 配置应用

#### 2.1 创建环境变量文件

在项目根目录创建 `.env` 文件：

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

#### 2.2 修改密钥（重要！）

编辑 `.env` 文件，生成安全的密钥：

```bash
# 生成 Flask 密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 生成 JWT 密钥
python -c "import secrets; print(secrets.token_hex(32))"
```

将生成的值复制到 `.env` 文件中：

```env
SECRET_KEY=生成的 flask 密钥
JWT_SECRET_KEY=生成的 jwt 密钥
```

### 步骤 3: 构建镜像

#### 3.1 使用 Docker Compose（推荐）

```bash
# 构建镜像
docker compose build

# 或者一步完成构建和启动
docker compose up -d --build
```

#### 3.2 使用 Docker 命令

```bash
# 构建镜像
docker build -t smarttable:latest .

# 查看镜像
docker images smarttable
```

### 步骤 4: 启动容器

#### 4.1 使用 Docker Compose

```bash
# 启动所有服务
docker compose up -d

# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f
```

#### 4.2 使用 Docker 命令

```bash
# 创建并启动容器
docker run -d \
  --name smarttable \
  -p 80:80 \
  --env-file .env \
  -v smarttable-data:/app \
  -v smarttable-uploads:/app/uploads \
  smarttable:latest
```

### 步骤 5: 验证部署

#### 5.1 检查容器状态

```bash
# Docker Compose
docker compose ps

# 或 Docker
docker ps
```

应该看到 `smarttable` 容器状态为 `Up`。

#### 5.2 访问应用

打开浏览器访问：

- **前端**: http://localhost
- **API 文档**: http://localhost/api/
- **健康检查**: http://localhost/api/health

#### 5.3 测试 API

```bash
# 使用 curl 测试健康检查端点
curl http://localhost/api/health

# 应该返回类似：
# {"success":true,"data":{"status":"healthy"}}
```

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `APP_PORT` | 应用访问端口 | `80` | `8080` |
| `FLASK_ENV` | Flask 运行环境 | `production` | `development` |
| `SECRET_KEY` | Flask 密钥 | - | `your-secret-key` |
| `JWT_SECRET_KEY` | JWT 密钥 | - | `your-jwt-secret` |
| `LOG_LEVEL` | 日志级别 | `INFO` | `DEBUG` |
| `MAX_CONTENT_LENGTH` | 最大上传大小 | `52428800` (50MB) | `104857600` (100MB) |

### 端口映射

| 容器端口 | 主机端口 | 说明 |
|---------|---------|------|
| 80 | 80 | HTTP 访问端口 |

如需修改端口，在 `.env` 文件中设置：

```env
APP_PORT=8080
```

然后重启：

```bash
docker compose down
docker compose up -d
```

### 数据持久化

应用数据通过 Docker 卷进行持久化：

- **sqlite_data**: 数据库文件
- **uploads_data**: 上传的文件

查看卷：

```bash
docker volume ls | grep smarttable
```

备份数据：

```bash
# 备份数据库
docker run --rm \
  -v smarttable_sqlite_data:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/smarttable-db-backup.tar.gz -C /source .
```

恢复数据：

```bash
# 恢复数据库
docker run --rm \
  -v smarttable_sqlite_data:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/smarttable-db-backup.tar.gz -C /target
```

---

## ❓ 常见问题

### 1. Docker 构建失败

**问题**: 构建过程中出现错误

**解决方案**:

```bash
# 清理构建缓存
docker builder prune -a

# 重新构建
docker compose build --no-cache
```

### 2. 端口冲突

**问题**: 端口 80 已被占用

**解决方案**:

```bash
# 查看占用端口的进程
# Windows
netstat -ano | findstr :80

# Linux/Mac
sudo lsof -i :80

# 修改 .env 文件中的 APP_PORT
APP_PORT=8080

# 重启
docker compose down
docker compose up -d
```

### 3. 容器无法启动

**问题**: 容器启动后立即退出

**解决方案**:

```bash
# 查看容器日志
docker compose logs smarttable

# 或者
docker logs smarttable

# 检查环境变量
docker compose config
```

### 4. 数据库连接错误

**问题**: 应用无法连接数据库

**解决方案**:

```bash
# 检查数据库文件权限
docker exec smarttable ls -la /app/*.db

# 修复权限
docker exec smarttable chmod 644 /app/smarttable.db

# 重启容器
docker compose restart
```

### 5. 上传文件失败

**问题**: 无法上传附件

**解决方案**:

```bash
# 检查上传目录权限
docker exec smarttable ls -la /app/uploads

# 修复权限
docker exec smarttable chmod -R 755 /app/uploads
docker exec smarttable chown -R www-data:www-data /app/uploads

# 重启
docker compose restart
```

### 6. 内存不足

**问题**: 容器因内存不足被杀死

**解决方案**:

```bash
# 限制容器内存使用
# 编辑 docker-compose.yml，添加：
# deploy:
#   resources:
#     limits:
#       memory: 1G
```

### 7. 访问速度慢

**问题**: 应用响应慢

**解决方案**:

```bash
# 增加 Gunicorn worker 数量
# 编辑 smarttable-backend/gunicorn.conf.py
workers = 4  # 增加到 4 或更多

# 重新构建
docker compose build
docker compose up -d
```

---

## 🔧 维护指南

### 查看日志

```bash
# 查看所有日志
docker compose logs

# 查看实时日志
docker compose logs -f

# 查看特定服务日志
docker compose logs smarttable

# 查看最近 100 行
docker compose logs --tail=100
```

### 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除容器（数据保留）
docker compose down

# 停止并删除所有（包括数据卷）
docker compose down -v
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart smarttable
```

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并重启
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 进入容器

```bash
# 进入容器 shell
docker compose exec smarttable bash

# 或
docker exec -it smarttable bash

# 查看容器信息
docker inspect smarttable
```

### 数据库备份

```bash
# 备份 SQLite 数据库
docker cp smarttable:/app/smarttable.db ./smarttable-backup-$(date +%Y%m%d).db

# 恢复数据库
docker cp smarttable-backup-20240101.db smarttable:/app/smarttable.db
docker compose restart
```

### 监控资源使用

```bash
# 查看容器资源使用
docker stats smarttable

# 查看容器详细信息
docker inspect smarttable
```

---

## 📊 性能优化建议

### 1. 使用生产级数据库

对于生产环境，建议使用 PostgreSQL：

```bash
# 使用完整的 docker-compose.yml（包含 PostgreSQL）
docker compose -f docker-compose.full.yml up -d
```

### 2. 启用 Redis 缓存

```bash
# 使用包含 Redis 的配置
docker compose --profile redis up -d
```

### 3. 配置 HTTPS

```bash
# 准备 SSL 证书
mkdir -p docker/nginx/ssl
cp your-cert.pem docker/nginx/ssl/cert.pem
cp your-key.pem docker/nginx/ssl/key.pem

# 启用 HTTPS 配置
# 编辑 docker/nginx/nginx.conf，取消注释 HTTPS 部分
```

### 4. 使用反向代理

在生产环境中，建议在 Docker 前再配置一层 Nginx 或 Traefik 作为反向代理。

---

## 🆘 获取帮助

如果遇到问题：

1. 查看日志：`docker compose logs -f`
2. 检查容器状态：`docker compose ps`
3. 验证配置：`docker compose config`
4. 查看 [GitHub Issues](https://github.com/your-repo/smarttable/issues)

---

## 📝 版本信息

- **Docker 镜像版本**: latest
- **Docker Compose 版本**: 3.8
- **Python 版本**: 3.11
- **Node.js 版本**: 20
- **Flask 版本**: 2.x
- **Vue.js 版本**: 3.x

---

**祝您使用愉快！** 🎊
