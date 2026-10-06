# ============================================
# SmartTable 统一 Docker 镜像
# 包含 前端(Vue.js) + 后端(Flask) + Redis 的完整生产环境镜像
# 基于 Nginx + Eventlet WSGI Server + Supervisor 进程管理
# ============================================

# 基础镜像可由构建脚本覆盖 (--build-arg): 国内网络下 buildx 容器拉 Docker Hub
# 不稳定, build_docker.py 会将基础镜像经阿里云 ACR 中转后传入, 无中转时使用官方名
ARG NODE_IMAGE=node:22-alpine
ARG PYTHON_IMAGE=python:3.11-slim

# ============================================
# 阶段 1: 构建前端
# ============================================
FROM ${NODE_IMAGE} AS frontend-builder

WORKDIR /app/frontend

# 启用 corepack 以使用 pnpm
# 国内网络直连 registry.npmjs.org 不稳定, corepack 与 pnpm 统一走 npmmirror
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
RUN corepack enable && corepack prepare pnpm@latest --activate

# 复制 pnpm 相关文件（利用 Docker 缓存层）
COPY smart-table/package.json smart-table/pnpm-lock.yaml smart-table/pnpm-workspace.yaml ./

# 安装全部依赖（包含 devDependencies；开启 CI 模式避免 TTY 交互）
ENV CI=true
RUN pnpm install --frozen-lockfile --registry=https://registry.npmmirror.com && pnpm store prune

# 复制前端源代码
COPY smart-table/ ./

# 构建前端（跳过 prepare 钩子中的 husky 与类型检查，Docker 中不需要）
ENV HUSKY=0 \
    CI=true
RUN pnpm exec vite build

# ============================================
# 阶段 2: 构建后端 Python 依赖
# ============================================
FROM ${PYTHON_IMAGE} AS backend-builder

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

# 安装 Python 依赖到用户目录（清华 PyPI 镜像加速，与 apt 换源保持一致）
RUN pip install --no-cache-dir --user -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# ============================================
# 阶段 3: 生产运行环境
# ============================================
FROM ${PYTHON_IMAGE}

# 构建参数（build_docker.py 会传入 BUILD_VERSION / BUILD_DATE；
# 默认值与 version.json 当前版本保持一致）
ARG BUILD_VERSION=1.6.6
ARG BUILD_DATE=unknown

LABEL maintainer="SmartTable Team" \
      version="${BUILD_VERSION}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      description="SmartTable - 智能表格应用"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production \
    DOCKER_ENV=true \
    PATH=/root/.local/bin:$PATH \
    TZ=Asia/Shanghai

# 配置国内 Debian 镜像源加速
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true && \
    sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

# 安装运行时依赖
# libpango/libpangocairo：WeasyPrint（PDF 导出）运行时必需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    nginx \
    curl \
    supervisor \
    redis-server \
    ca-certificates \
    gettext-base \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从后端构建阶段复制 Python 依赖
COPY --from=backend-builder /root/.local /root/.local

# 复制后端代码
COPY smarttable-backend/ ./

# 复制宿主版本信息（插件引擎兼容校验 engines.smarttable 需要）
COPY version.json /app/version.json

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
COPY docker/server_runner.py /app/docker/server_runner.py
COPY docker/entrypoint.sh /entrypoint.sh

# 源码保护与敏感文件清理（须在全部 .py 就位后执行）：
# 1) 全部 Python 源码编译为字节码（.pyc 与源文件同目录平铺）后删除 .py 源文件，
#    覆盖业务包 app/、入口与工具脚本、docker/server_runner.py 及 alembic migrations/
#    （alembic 1.13 的 load_python_file 原生支持 .pyc 回退加载，迁移可正常运行）；
#    仅保留运行时插件 uploads/plugins/*/main.py（产品功能，非后端源码）
# 2) 兜底删除 .db/.pem 等敏感文件（即使 .dockerignore 规则遗漏也不进入最终镜像）
RUN python -m compileall -b app/ migrations/ docker/server_runner.py \
        run.py init_db.py create_tables.py fix_loop_data_source.py init_link_tables.py && \
    find app/ migrations/ docker/ -type f -name '*.py' -delete && \
    rm -f run.py init_db.py create_tables.py fix_loop_data_source.py init_link_tables.py && \
    find app/ migrations/ docker/ -type d -name '__pycache__' -prune -exec rm -rf {} + && \
    find /app -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \
        -o -name '*.pem' -o -name '*.key' -o -name '*.p12' -o -name '*.pfx' \) -delete && \
    find /app -type d -empty -name '__pycache__' -delete

# 修复 Windows CRLF 换行符问题，并设置权限
RUN sed -i 's/\r$//' /entrypoint.sh /etc/nginx/nginx.conf /etc/supervisor/conf.d/supervisord.conf /etc/redis/redis.conf && \
    chmod +x /entrypoint.sh && \
    chown -R www-data:www-data /app/static /app/uploads && \
    chmod -R 755 /app/uploads

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80/api/health || exit 1

# 使用入口脚本启动
ENTRYPOINT ["/entrypoint.sh"]