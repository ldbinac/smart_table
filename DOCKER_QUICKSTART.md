# SmartTable Docker 快速参考

## 🚀 快速启动

### Windows PowerShell

```powershell
# 运行快速启动脚本
.\start.ps1
```

### Linux/Mac

```bash
# 运行快速启动脚本
./start.sh
```

## 📦 构建和启动

### 简单部署（SQLite）

```bash
# 使用 docker-compose.yml
docker compose up -d --build
```

### 完整部署（PostgreSQL + Redis + MinIO）

```bash
# 使用 docker-compose.full.yml
docker compose -f docker-compose.full.yml up -d --build
```

## 🔍 常用命令

```bash
# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 进入容器
docker compose exec smarttable bash

# 重新构建
docker compose build --no-cache
```

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost | SmartTable 主界面 |
| API | http://localhost/api/ | REST API |
| 健康检查 | http://localhost/api/health | 健康检查端点 |

**完整部署额外提供：**

| 服务 | 地址 | 说明 |
|------|------|------|
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |
| MinIO | localhost:9000 | 对象存储 API |
| MinIO Console | localhost:9001 | 对象存储管理界面 |

## ⚙️ 配置

### 修改端口

编辑 `.env` 文件：

```env
APP_PORT=8080
```

重启：

```bash
docker compose down
docker compose up -d
```

### 修改密钥

生成新密钥：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

编辑 `.env` 文件，更新：

```env
SECRET_KEY=生成的密钥
JWT_SECRET_KEY=生成的密钥
```

重新构建：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 启用实时协作

编辑 `.env` 文件，添加：

```env
ENABLE_REALTIME=true
SOCKETIO_MESSAGE_QUEUE=redis://redis:6379/1
```

> **注意**：启用实时协作时，需使用完整部署模式（`docker-compose.full.yml`）以确保 Redis 服务可用。

重新构建：

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 🐛 故障排查

### 查看日志

```bash
# 查看所有日志
docker compose logs

# 查看特定服务日志
docker compose logs smarttable

# 实时查看日志
docker compose logs -f smarttable
```

### 检查容器状态

```bash
# 查看容器状态
docker compose ps

# 查看详细信息
docker inspect smarttable
```

### 测试健康检查

```bash
curl http://localhost/api/health
```

### 重置所有

```bash
# 停止并删除所有容器和数据卷
docker compose down -v

# 重新构建和启动
docker compose build --no-cache
docker compose up -d
```

## 📊 资源限制

编辑 `docker-compose.full.yml`：

```yaml
services:
  smarttable:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 💾 数据备份

### 备份数据库

```bash
# SQLite
docker cp smarttable:/app/smarttable.db ./backup.db

# PostgreSQL
docker exec smarttable-postgres pg_dump -U smarttable smarttable > backup.sql
```

### 恢复数据库

```bash
# SQLite
docker cp backup.db smarttable:/app/smarttable.db
docker compose restart

# PostgreSQL
docker exec -i smarttable-postgres psql -U smarttable smarttable < backup.sql
```

## 🆘 获取帮助

```bash
# 查看配置
docker compose config

# 查看镜像
docker images

# 查看卷
docker volume ls

# 清理未使用的资源
docker system prune -a
```

---

**更多详细信息请查看 [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)**
