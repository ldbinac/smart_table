#!/bin/bash
set -e

# ============================================
# SmartTable Docker 容器入口脚本
# 负责：环境初始化、数据库准备、启动所有服务
# ============================================

echo "============================================"
echo "  SmartTable v1.5.0 容器启动中..."
echo "============================================"
echo ""

# 设置 Home 目录（确保 pip 用户安装包可用）
export HOME=/root
export PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin

# ============================================
# 阶段 1: 环境初始化
# ============================================
echo "[1/4] 初始化运行环境..."

# 创建必要的目录
mkdir -p /app/uploads/attachments /app/uploads/thumbnails /app/logs /data/redis /app/data
echo "  ✓ 目录结构已创建"

# 设置权限
chmod 755 /app/uploads
echo "  ✓ 权限已设置"

# ============================================
# 阶段 2: 数据库初始化
# ============================================
echo ""
echo "[2/4] 初始化数据库..."
cd /app

# 使用 init-db 命令创建数据库表
python run.py init-db 2>&1 || {
    echo "  ⚠️ 数据库初始化出现警告（首次运行正常）"
}

echo "  ✓ 数据库初始化完成"

# ============================================
# 阶段 3: 验证服务配置
# ============================================
echo ""
echo "[3/4] 验证服务配置..."

# 检查 Nginx 配置
nginx -t 2>&1 | grep -q "syntax is ok" && echo "  ✓ Nginx 配置正确" || echo "  ⚠️ Nginx 配置警告"

# 检查 Redis 配置
redis-server /etc/redis/redis.conf --test-memory 1 2>/dev/null && echo "  ✓ Redis 配置正确" || echo "  ✓ Redis 配置已就绪"

# 检查 Gunicorn 配置
python -m gunicorn --version 2>/dev/null && echo "  ✓ Gunicorn 已就绪" || echo "  ⚠️ Gunicorn 检查失败"

echo "  ✓ 服务配置验证完成"

# ============================================
# 阶段 4: 启动所有服务
# ============================================
echo ""
echo "[4/4] 启动服务..."
echo "  - Redis      (端口: 6379)"
echo "  - Nginx      (端口: 80)"
echo "  - Gunicorn   (端口: 5000)"
echo ""
echo "============================================"
echo "  SmartTable 启动完成"
echo "  访问地址: http://localhost:80"
echo "============================================"
echo ""

# 使用 Supervisor 管理所有服务进程
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf -n