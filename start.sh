#!/bin/bash
# SmartTable Docker 快速启动脚本（Linux/Mac）

set -e

echo "======================================"
echo "SmartTable Docker 快速部署"
echo "======================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

echo "✅ Docker 已安装：$(docker --version)"

# 检查 Docker Compose 是否安装
if ! command -v docker compose &> /dev/null; then
    echo "⚠️  Docker Compose 未安装，尝试使用 docker-compose"
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        echo "✅ 找到 docker-compose"
    else
        echo "❌ Docker Compose 未安装"
        exit 1
    fi
else
    COMPOSE_CMD="docker compose"
    echo "✅ Docker Compose 已安装：$(docker compose version)"
fi

echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "✅ .env 文件已创建，请编辑此文件修改密钥配置"
    echo ""
fi

# 选择部署模式
echo "请选择部署模式:"
echo "1) 简单部署（SQLite，适合测试）"
echo "2) 完整部署（PostgreSQL + Redis + MinIO，适合生产）"
read -p "请输入选项 (1/2): " choice

case $choice in
    1)
        echo ""
        echo "🚀 开始简单部署..."
        $COMPOSE_CMD -f docker-compose.yml up -d --build
        echo ""
        echo "✅ 部署完成！"
        echo ""
        echo "访问地址：http://localhost"
        echo "查看日志：$COMPOSE_CMD logs -f"
        ;;
    2)
        echo ""
        echo "🚀 开始完整部署..."
        if [ ! -f .env ]; then
            cp .env.full.example .env
        fi
        $COMPOSE_CMD -f docker-compose.full.yml up -d --build
        echo ""
        echo "✅ 部署完成！"
        echo ""
        echo "访问地址：http://localhost"
        echo "PostgreSQL: localhost:5432"
        echo "Redis: localhost:6379"
        echo "MinIO: localhost:9000"
        echo "MinIO 控制台：localhost:9001"
        echo "查看日志：$COMPOSE_CMD logs -f"
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "常用命令:"
echo "======================================"
echo "查看状态：$COMPOSE_CMD ps"
echo "查看日志：$COMPOSE_CMD logs -f"
echo "停止服务：$COMPOSE_CMD down"
echo "重启服务：$COMPOSE_CMD restart"
echo "======================================"
