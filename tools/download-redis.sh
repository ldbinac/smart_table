#!/bin/bash
#
# Redis 二进制文件自动下载脚本 (Linux/macOS)
# 用法: chmod +x download-redis.sh && ./download-redis.sh
#

set -e

echo "============================================"
echo "  Redis 自动下载脚本"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

REDIS_VERSION="7.2.4"
REDIS_LINUX_DIR="$PROJECT_ROOT/tools/redis-linux"

echo "[信息] 目标目录: $REDIS_LINUX_DIR"
echo "[信息] Redis 版本: $REDIS_VERSION"
echo ""

# 检查是否已存在
if [ -f "$REDIS_LINUX_DIR/redis-server" ]; then
    echo "[提示] redis-server 已存在，跳过下载。"
    echo "如需重新下载，请先删除: rm $REDIS_LINUX_DIR/redis-server"
    exit 0
fi

# 检测操作系统类型
OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="macos";;
    *)          echo "[错误] 不支持的操作系统: $OS_TYPE"; exit 1;;
esac

echo "[步骤 1/3] 检测系统架构..."
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)    ARCH_NAME="x64";;
    aarch64)   ARCH_NAME="arm64";;
    *)         echo "[错误] 不支持的架构: $ARCH"; exit 1;;
esac
echo "  平台: $PLATFORM, 架构: $ARCH_NAME"

# 尝试从系统已安装的 Redis 复制（最快）
echo ""
echo "[步骤 2/3] 尝试查找系统安装的 Redis..."

if command -v redis-server &> /dev/null; then
    SYSTEM_REDIS="$(which redis-server)"
    echo "  找到系统 Redis: $SYSTEM_REDIS"
    read -p "  是否复制系统版本? [Y/n]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        mkdir -p "$REDIS_LINUX_DIR"
        cp "$SYSTEM_REDIS" "$REDIS_LINUX_DIR/redis-server"
        chmod +x "$REDIS_LINUX_DIR/redis-server"
        echo "✓ 已复制到: $REDIS_LINUX_DIR/redis-server"
        
        # 验证
        echo ""
        echo "[验证]"
        "$REDIS_LINUX_DIR/redis-server --version"
        echo ""
        echo "✅ 完成！Redis 已准备就绪。"
        exit 0
    fi
fi

echo "  未找到系统 Redis，将尝试编译安装..."

# 从源码编译
echo ""
echo "[步骤 3/3] 从源码编译 Redis..."

TMPDIR=$(mktemp -d)
cd "$TMPDIR"

echo "  下载 Redis ${REDIS_VERSION} 源码..."
wget -q "https://github.com/redis/redis/archive/refs/tags/${REDIS_VERSION}.tar.gz" \
     -O "redis-${REDIS_VERSION}.tar.gz"

echo "  解压..."
tar xzf "redis-${REDIS_VERSION}.tar.gz"
cd "redis-${REDIS_VERSION}"

echo "  编译中... (需要 1-2 分钟)"
make clean > /dev/null 2>&1 || true
make -j$(nproc) > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "  编译成功！"
    
    mkdir -p "$REDIS_LINUX_DIR"
    cp src/redis-server "$REDIS_LINUX_DIR/redis-server"
    chmod +x "$REDIS_LINUX_DIR/redis-server"
    
    # 清理临时文件
    cd /
    rm -rf "$TMPDIR"
    
    echo ""
    echo "[验证]"
    "$REDIS_LINUX_DIR/redis-server --version"
    echo ""
    echo "✅ 完成！Redis 已准备就绪。"
    echo "位置: $REDIS_LINUX_DIR/redis-server"
else
    echo ""
    echo "❌ 编译失败！"
    echo "请手动安装 Redis 或查看错误日志："
    echo "  1. 确保 gcc 和 make 已安装: sudo apt-get install build-essential"
    echo "  2. 手动下载预编译版本"
    exit 1
fi
