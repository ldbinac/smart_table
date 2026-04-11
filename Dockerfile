# SmartTable 统一 Docker 镜像
# 包含前后端的完整生产环境镜像
# 基于 Nginx + Gunicorn + Flask + Vue.js

# ============================================
# 阶段 1: 构建前端
# ============================================
FROM node:20-alpine AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 复制 package 文件
COPY smart-table/package.json smart-table/package-lock.json ./

# 安装依赖
RUN npm ci --only=production

# 复制前端源代码
COPY smart-table/ ./

# 构建前端
RUN npm run build

# ============================================
# 阶段 2: 构建后端 Python 依赖
# ============================================
FROM python:3.11-slim AS backend-builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 文件
COPY smarttable-backend/requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================
# 阶段 3: 生产环境
# ============================================
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    PATH=/root/.local/bin:$PATH

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nginx \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=backend-builder /root/.local /root/.local

# 复制后端代码
COPY smarttable-backend/ ./

# 创建必要的目录
RUN mkdir -p uploads/attachments uploads/thumbnails logs static

# 从构建阶段复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist /app/static

# 复制 Nginx 配置
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# 复制 Supervisor 配置
COPY docker/supervisor/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 设置权限
RUN chmod +x /app/run.py && \
    chown -R www-data:www-data /app/static /app/uploads && \
    chmod -R 755 /app/uploads

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/api/health || exit 1

# 使用 Supervisor 启动多个进程
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
