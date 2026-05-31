# ============================================
# SmartTable 统一 Docker 镜像
# 包含 前端(Vue.js) + 后端(Flask) + Redis 的完整生产环境镜像
# 基于 Nginx + Gunicorn + Supervisor 进程管理
# ============================================

# ============================================
# 阶段 1: 构建前端
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制 package 文件（利用 Docker 缓存层）
COPY smart-table/package.json smart-table/package-lock.json ./

# 安装全部依赖（包含 devDependencies，prepare 脚本需要 husky）
RUN npm ci && npm cache clean --force

# 复制前端源代码
COPY smart-table/ ./

# 构建前端（跳过 vue-tsc 类型检查，使用 vite 直接编译）
RUN npx vite build

# ============================================
# 阶段 2: 构建后端 Python 依赖
# ============================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# 配置国内 Debian 镜像源加速
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true && \
    sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY smarttable-backend/requirements.txt ./

# 安装 Python 依赖到用户目录
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# 阶段 3: 生产运行环境
# ============================================
FROM python:3.11-slim

LABEL maintainer="SmartTable Team" \
      version="1.4.1" \
      description="SmartTable - 智能表格应用"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    PATH=/root/.local/bin:$PATH \
    TZ=Asia/Shanghai

# 配置国内 Debian 镜像源加速
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true && \
    sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nginx \
    curl \
    supervisor \
    redis-server \
    ca-certificates \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从后端构建阶段复制 Python 依赖
COPY --from=backend-builder /root/.local /root/.local

# 复制后端代码
COPY smarttable-backend/ ./

# 创建必要的运行目录
RUN mkdir -p /app/uploads/attachments /app/uploads/thumbnails /app/logs /data/redis /var/log/supervisor

# 从前端构建阶段复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist /app/static

# 复制 Nginx 配置
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# 复制 Supervisor 配置
COPY docker/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制 Redis 配置
COPY docker/redis/redis.conf /etc/redis/redis.conf

# 复制容器入口脚本
COPY docker/entrypoint.sh /entrypoint.sh

# 设置权限
RUN chmod +x /entrypoint.sh && \
    chown -R www-data:www-data /app/static /app/uploads && \
    chmod -R 755 /app/uploads

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/api/health || exit 1

# 使用入口脚本启动
ENTRYPOINT ["/entrypoint.sh"]