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
# 注意：不能用 command -v docker compose（compose 会被当作独立命令名而误判失败），
# 直接执行 docker compose version 验证
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    echo "✅ Docker Compose 已安装：$(docker compose version)"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo "✅ 找到 docker-compose"
else
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo ""

# 选择部署模式
echo "请选择部署模式:"
echo "1) 简单部署（SQLite，适合测试）"
echo "2) 完整部署（PostgreSQL + Redis + MinIO，适合生产）"
read -p "请输入选项 (1/2): " choice

case $choice in
    1)
        # 检查 .env 文件（简单部署模板）
        if [ ! -f .env ]; then
            echo "📝 创建环境变量文件..."
            cp .env.example .env
            echo "✅ .env 文件已创建，请编辑此文件修改密钥配置"
            echo ""
        fi
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
        # 检查 .env 文件（完整部署模板，包含 DB/Redis/MinIO 配置）
        if [ ! -f .env ]; then
            echo "📝 创建环境变量文件..."
            cp .env.full.example .env
            echo "✅ .env 文件已创建，请编辑此文件修改数据库密码与密钥配置"
            echo ""
        fi
        echo ""
        echo "🚀 开始完整部署..."
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
