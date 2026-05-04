# SmartTable 零依赖打包方案设计文档

> **日期**: 2026-05-03
> **版本**: v1.0
> **状态**: 已批准

## 1. 项目背景与目标

### 1.1 背景

SmartTable 是一个功能丰富的智能表格应用，当前采用 Docker Compose 容化部署方式。为降低部署门槛，提升用户体验，需要将应用打包为"零依赖运行"的可执行程序，适配 Windows 和 Linux 平台。

### 1.2 目标

- **零依赖运行**: 无需 Docker、Python 运行时、Nginx 等外部环境
- **开箱即用**: 双击启动，自动管理所有组件
- **完整功能**: 保留所有核心功能（缓存、实时协作、文件上传）
- **跨平台支持**: 优先 Windows x64，其次 Linux x64

### 1.3 核心需求

| 需求项 | 实现方案 | 优先级 |
|--------|----------|--------|
| 前后端整合 | 单进程模式（Flask 托管静态资源） | P0 |
| Python 打包 | PyInstaller --onefile | P0 |
| 数据库 | 内嵌 SQLite | P0 |
| 缓存服务 | 内嵌 Redis 单文件版 | P0 |
| 文件存储 | 本地文件系统替代 MinIO | P0 |
| 跨平台 | Windows + Linux 双版本 | P1 |

---

## 2. 技术架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────┐
│              SmartTable.exe (主程序)              │
│  ┌───────────────────────────────────────────┐  │
│  │         Flask Application (内嵌)           │  │
│  │  ┌─────────────┐  ┌────────────────────┐  │  │
│  │  │   API 路由   │  │  静态文件服务      │  │  │
│  │  │ /api/*      │  │  / → index.html    │  │  │
│  │  └──────┬──────┘  └────────┬───────────┘  │  │
│  │         │                  │               │  │
│  │  ┌──────▼──────────────────▼───────────┐  │  │
│  │  │        业务逻辑层                     │  │  │
│  │  │  (Services / Models / Routes)       │  │  │
│  │  └──────┬──────────┬──────────┬───────┘  │  │
│  │         │          │          │            │  │
│  │  ┌──────▼──┐ ┌────▼────┐ ┌──▼───────┐   │  │
│  │  │ SQLite  │ │ Redis   │ │ Local FS  │   │  │
│  │  │ (数据库) │ │ (缓存)  │ │ (文件存储) │   │  │
│  │  └─────────┘ └─────────┘ └──────────┘   │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │      PyInstaller 运行时环境                │  │
│  │  (Python 解释器 + 所有依赖库)              │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

外部组件：
┌──────────────┐     ┌────────────────────┐
│ redis-server  │ ←→  │  SmartTable.exe    │
│ (独立进程)    │     │  (自动管理生命周期)  │
└──────────────┘     └────────────────────┘
```

### 2.2 组件职责

#### 主程序 (SmartTable.exe / smarttable)
- **技术栈**: Flask + PyInstaller 打包
- **职责**:
  - 提供 RESTful API 服务 (`/api/*`)
  - 托管前端静态资源 (Vue 构建产物)
  - 管理 SQLite 数据库连接
  - 连接 Redis 缓存服务
  - 处理文件上传/下载（本地文件系统）
  - 可选：SocketIO 实时协作（需 Redis 消息队列）

#### Redis 服务 (redis-server)
- **角色**: 外部独立进程
- **用途**:
  - 应用层缓存 (Flask-Caching)
  - SocketIO 消息队列（实时协作功能）
- **生命周期**: 由主程序启动脚本管理

---

## 3. 关键技术实现

### 3.1 前端集成策略

#### 3.1.1 构建流程
```bash
# 1. 构建前端
cd smart-table
npm install
npm run build  # 生成 dist/ 目录

# 2. 将 dist/ 内容嵌入 PyInstaller
pyinstaller --add-data "smart-table/dist;dist" ...
```

#### 3.1.2 Flask 静态文件托管
```python
import os
import sys
from flask import send_from_directory

def configure_static_serving(app):
    """配置前端静态文件服务"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发环境路径
        base_path = os.path.dirname(os.path.abspath(__file__))

    dist_dir = os.path.join(base_path, 'dist')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """前端路由：API 请求转发，其他请求返回前端资源"""
        if path.startswith('api/') or path.startswith('uploads'):
            return  # 由 API 路由处理

        if path and os.path.exists(os.path.join(dist_dir, path)):
            return send_from_directory(dist_dir, path)
        else:
            # Vue Router history 模式回退到 index.html
            return send_from_directory(dist_dir, 'index.html')
```

### 3.2 Redis 集成方案

#### 3.2.1 平台选择

| 平台 | Redis 版本 | 说明 |
|------|-----------|------|
| Windows | MemuraiValkey 或 Redis for Windows | 原生 Windows 支持 |
| Linux | Redis 7.x 静态编译版 | 通用 Linux 二进制 |

#### 3.2.2 进程管理器
```python
import subprocess
import time
import atexit
import platform

class RedisManager:
    """Redis 进程生命周期管理"""

    def __init__(self, port=6379):
        self.port = port
        self.redis_process = None
        self.redis_executable = self._detect_redis_path()

    def _detect_redis_path(self):
        """检测 Redis 可执行文件路径"""
        system = platform.system()
        if system == 'Windows':
            return 'redis-server.exe'  # 相对于主程序目录
        else:
            return './redis-server'

    def start(self):
        """启动 Redis 服务"""
        print(f'[Redis] Starting Redis on port {self.port}...')
        try:
            self.redis_process = subprocess.Popen(
                [self.redis_executable, '--port', str(self.port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            # 等待 Redis 就绪
            time.sleep(2)
            if self.redis_process.poll() is None:
                print('[Redis] ✓ Redis started successfully')
                atexit.register(self.stop)
                return True
            else:
                print('[Redis] ✗ Failed to start Redis')
                return False
        except Exception as e:
            print(f'[Redis] ✗ Error: {e}')
            return False

    def stop(self):
        """停止 Redis 服务"""
        if self.redis_process and self.redis_process.poll() is None:
            print('[Redis] Stopping Redis...')
            self.redis_process.terminate()
            self.redis_process.wait(timeout=5)
            print('[Redis] ✓ Redis stopped')

    def is_running(self):
        """检查 Redis 是否在运行"""
        return self.redis_process and self.redis_process.poll() is None
```

### 3.3 文件存储替代方案

#### 3.3.1 配置调整
```python
# config.py 中修改 MinIO 相关配置
class Config:
    # 禁用 MinIO，使用本地文件系统
    MINIO_ENABLED = False
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    
    # 本地存储路径结构
    # uploads/
    #   ├── attachments/      # 用户上传附件
    #   ├── thumbnails/       # 图片缩略图
    #   └── exports/          # 导出文件临时存储
```

#### 3.3.2 存储服务实现
```python
import os
from werkzeug.utils import secure_filename
from flask import send_file

class LocalFileStorage:
    """本地文件系统存储（替代 MinIO）"""

    def __init__(self, base_folder='uploads'):
        self.base_folder = base_folder
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        dirs = ['attachments', 'thumbnails', 'exports']
        for dir_name in dirs:
            os.makedirs(os.path.join(self.base_folder, dir_name), exist_ok=True)

    def save_file(self, file, subfolder='attachments', filename=None):
        """
        保存上传文件
        Args:
            file: Flask FileStorage 对象
            subfolder: 子目录名称
            filename: 自定义文件名（可选）
        Returns:
            str: 文件访问 URL 路径
        """
        if filename is None:
            filename = secure_filename(file.filename)

        # 生成唯一文件名（避免冲突）
        import uuid
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

        save_path = os.path.join(self.base_folder, subfolder, unique_filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        file.save(save_path)

        # 返回相对访问路径
        return f'/api/files/{subfolder}/{unique_filename}'

    def get_file(self, filepath):
        """获取文件内容"""
        full_path = os.path.join(self.base_folder, filepath.lstrip('/'))
        if os.path.exists(full_path):
            return send_file(full_path)
        else:
            raise FileNotFoundError(f'File not found: {filepath}')

    def delete_file(self, filepath):
        """删除文件"""
        full_path = os.path.join(self.base_folder, filepath.lstrip('/'))
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
```

### 3.4 PyInstaller 打包配置

#### 3.4.1 规范文件 (smarttable.spec)
```python
# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(project_root, 'smarttable-backend', 'run.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # 前端构建产物
        (
            os.path.join(project_root, 'smart-table', 'dist'),
            'dist'
        ),
        # 配置文件模板
        (
            os.path.join(project_root, 'smarttable-backend', '.env.example'),
            'config'
        ),
        # Alembic 迁移文件（数据库初始化需要）
        (
            os.path.join(project_root, 'smarttable-backend', 'migrations'),
            'migrations'
        ),
    ],
    hiddenimports=[
        # Flask 核心
        'flask',
        'flask_sqlalchemy',
        'flask_migrate',
        'flask_caching',
        'flask_socketio',
        'flask_cors',
        'flask_jwt_extended',
        'flask_bcrypt',

        # 数据库
        'sqlalchemy',
        'psycopg2',
        'sqlite3',

        # Redis
        'redis',

        # 数据处理
        'pandas',
        'openpyxl',
        'xlrd',

        # 图片处理
        'PIL',
        'Pillow',

        # 安全
        'cryptography',
        'bcrypt',

        # 序列化
        'marshmallow',
        'marshmallow_sqlalchemy',

        # WebSocket
        'eventlet',
        'socketio',
        'engineio',

        # 其他工具
        'python_dotenv',
        'gunicorn',
        'flasgger',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy.f2py',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # 使用单文件模式时设为 False
    name='SmartTable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用 UPX 压缩（减小体积）
    console=True,  # 显示控制台日志（调试阶段），生产环境可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

#### 3.4.2 构建脚本 (build.py)
```python
#!/usr/bin/env python3
"""
SmartTable 跨平台打包构建脚本
用法:
  python build.py windows   # 构建 Windows 版本
  python build.py linux     # 构建 Linux 版本
  python build.py all       # 构建两个平台
"""
import subprocess
import os
import sys
import shutil
import argparse
from pathlib import Path

def run_command(cmd, cwd=None):
    """执行 shell 命令并输出日志"""
    print(f'\n[执行] {" ".join(cmd)}')
    result = subprocess.run(cmd, cwd=cwd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f'[错误] 命令执行失败: {result.returncode}')
        sys.exit(1)
    return result

def build_frontend():
    """构建前端项目"""
    print('\n' + '='*50)
    print('[1/4] 构建前端项目...')
    print('='*50)

    frontend_dir = Path(__file__).parent / 'smart-table'
    run_command(['npm', 'install'], cwd=frontend_dir)
    run_command(['npm', 'run', 'build'], cwd=frontend_dir)

    dist_path = frontend_dir / 'dist'
    if not dist_path.exists():
        raise RuntimeError('前端构建失败：dist 目录不存在')

    print(f'✓ 前端构建完成: {dist_path}')

def build_backend(platform):
    """使用 PyInstaller 构建后端"""
    print('\n' + '='*50)
    print(f'[2/4] 构建 {platform} 后端可执行文件...')
    print('='*50)

    spec_file = Path(__file__).parent / 'smarttable.spec'

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '-y',
        str(spec_file),
        f'--name=SmartTable_{"win" if platform == "windows" else "linux"}',
    ]

    # 平台特定参数
    if platform == 'windows':
        cmd.append('--onefile')  # Windows 使用单文件模式
        cmd.append('--windowed')  # 不显示控制台窗口（可选）
    else:
        cmd.append('--onefile')  # Linux 也使用单文件模式

    run_command(cmd)

def prepare_release_package(platform):
    """准备发布包"""
    print('\n' + '='*50)
    print(f'[3/4] 准备 {platform} 发布包...')
    print('='*50)

    release_dir = Path(__file__).parent / 'release' / platform.capitalize()
    release_dir.mkdir(parents=True, exist_ok=True)

    # 复制主程序
    exe_name = f'SmartTable_{"win" if platform == "windows" else "linux"}'
    if platform == 'windows':
        exe_name += '.exe'
        shutil.copy2(f'dist/{exe_name}', release_dir / 'SmartTable.exe')

        # 复制 Redis for Windows
        redis_src = Path(__file__).parent / 'tools' / 'redis-windows' / 'redis-server.exe'
        if redis_src.exists():
            shutil.copy2(redis_src, release_dir / 'redis-server.exe')

        # 创建启动脚本
        create_windows_scripts(release_dir)
    else:
        shutil.copy2(f'dist/{exe_name}', release_dir / 'smarttable')

        # 复制 Redis for Linux
        redis_src = Path(__file__).parent / 'tools' / 'redis-linux' / 'redis-server'
        if redis_src.exists():
            shutil.copy2(redis_src, release_dir / 'redis-server')
            os.chmod(release_dir / 'redis-server', 0o755)

        # 创建启动脚本
        create_linux_scripts(release_dir)

    # 复制配置文件
    config_dir = release_dir / 'config'
    config_dir.mkdir(exist_ok=True)
    shutil.copy2(
        Path(__file__).parent / 'smarttable-backend' / '.env.example',
        config_dir / '.env'
    )

    # 复制 README
    create_readme(release_dir, platform)

    print(f'✓ 发布包准备完成: {release_dir}')

def create_windows_scripts(release_dir):
    """创建 Windows 启动/停止脚本"""
    # start.bat
    start_bat = release_dir / 'start.bat'
    start_bat.write_text('''@echo off
chcp 65001 >nul
title SmartTable Server
echo ============================================
echo   SmartTable 启动器
echo ============================================
echo.

:: 检查 Redis 是否已在运行
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server">NUL
if "%ERRORLEVEL%"=="0" (
    echo [Redis] Redis 已在运行，跳过启动...
) else (
    echo [Redis] 正在启动 Redis 服务...
    start /B "" "%~dp0redis-server.exe" --port 6379 --loglevel warning >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo [Redis] ✓ Redis 已启动
)

echo.
echo [SmartTable] 正在启动应用程序...
echo [SmartTable] 请在浏览器中打开 http://localhost:5000
echo.
echo 按 Ctrl+C 停止服务...
echo.

start /B "" "%~dp0SmartTable.exe"

:: 等待用户中断
pause >nul 2>&1

echo.
echo [停止] 正在关闭所有服务...
taskkill /F /IM SmartTable.exe >nul 2>&1
taskkill /F /IM redis-server.exe >nul 2>&1
echo [停止] ✓ 所有服务已停止
''', encoding='utf-8')

    # stop.bat
    stop_bat = release_dir / 'stop.bat'
    stop_bat.write_text('''@echo off
echo 正在停止 SmartTable...
taskkill /F /IM SmartTable.exe >nul 2>&1
taskkill /F /IM redis-server.exe >nul 2>&1
echo ✓ SmartTable 已停止
''', encoding='utf-8')

def create_linux_scripts(release_dir):
    """创建 Linux 启动/停止脚本"""
    # start.sh
    start_sh = release_dir / 'start.sh'
    start_sh.write_text('''#!/bin/bash

echo "============================================"
echo "  SmartTable 启动器"
echo "============================================"
echo ""

# 检查 Redis 是否已在运行
if pgrep -x "redis-server" > /dev/null; then
    echo "[Redis] Redis 已在运行，跳过启动..."
else
    echo "[Redis] 正在启动 Redis 服务..."
    ./redis-server --port 6379 --loglevel warning --daemonize yes
    sleep 2
    echo "[Redis] ✓ Redis 已启动"
fi

echo ""
echo "[SmartTable] 正在启动应用程序..."
echo "[SmartTable] 请在浏览器中打开 http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务..."
echo ""

./smarttable &
APP_PID=$!

# 清理函数
cleanup() {
    echo ""
    echo "[停止] 正在关闭所有服务..."
    kill $APP_PID 2>/dev/null
    ./redis-cli shutdown 2>/dev/null
    echo "[停止] ✓ 所有服务已停止"
    exit 0
}

# 捕获信号
trap cleanup SIGINT SIGTERM

wait $APP_PID
''', encoding='utf-8')
    os.chmod(start_sh, 0o755)

    # stop.sh
    stop_sh = release_dir / 'stop.sh'
    stop_sh.write_text('''#!/bin/bash
echo "正在停止 SmartTable..."
pkill -f "smarttable" 2>/dev/null
./redis-cli shutdown 2>/dev/null
echo "✓ SmartTable 已停止"
''', encoding='utf-8')
    os.chmod(stop_sh, 0o755)

def create_readme(release_dir, platform):
    """创建运行说明文档"""
    readme_content = f'''# SmartTable 运行说明 ({platform} 版本)

## 📋 系统要求

### {platform} 平台
{"- 操作系统: Windows 10/11 (64位)" if platform == "windows" else "- 操作系统: Ubuntu 20.04+/CentOS 8+ (x86_64)"}
- 内存: 最低 2GB RAM（推荐 4GB）
- 磁盘空间: 500MB 可用空间（不含数据）
- 网络: 本地访问无需网络，远程访问需开放端口 5000

## 🚀 快速开始

### 第一次运行

1. **解压/复制** 将整个文件夹放到目标位置（建议非中文路径）
2. **编辑配置**（可选）打开 `config/.env` 修改配置参数
3. **启动服务**
   - {"Windows: 双击 `start.bat` 或在命令行运行 `start.bat`" if platform == "windows" else "Linux: 在终端运行 `./start.sh`"}
4. **访问应用** 浏览器打开 http://localhost:5000
5. **初始化管理员**（首次运行必做）
   ```bash
   {"SmartTable.exe create-admin admin@example.com password123 Admin" if platform == "windows" else "./smarttable create-admin admin@example.com password123 Admin"}
   ```

### 日常操作

- **启动**: {"双击 `start.bat`" if platform == "windows" else "运行 `./start.sh`"}
- **停止**: {"双击 `stop.bat`" if platform == "windows" else "运行 `./stop.sh"`}
- **查看日志**: 控制台输出或 `logs/smarttable.log`

## ⚙️ 配置说明

编辑 `config/.env` 文件可自定义以下参数：

### 服务器配置
```env
FLASK_HOST=0.0.0.0        # 监听地址（0.0.0.0 允许远程访问）
FLASK_PORT=5000            # 监听端口
LOG_LEVEL=INFO             # 日志级别: DEBUG/INFO/WARNING/ERROR
```

### 安全配置（重要！）
```env
SECRET_KEY=your-secret-key        # 应用密钥（必须修改）
JWT_SECRET_KEY=your-jwt-key       # JWT 密钥（必须修改）
```
> ⚠️ **安全警告**: 生产环境务必生成强随机密钥！

### 数据库配置
```env
DATABASE_URL=sqlite:///data/smarttable.db   # SQLite 数据库路径
```
- 数据文件默认保存在程序目录下的 `data/` 文件夹
- 如需迁移数据，可直接复制 `.db` 文件

### Redis 配置
```env
REDIS_URL=redis://localhost:6379/0   # Redis 连接地址
```
- 默认使用内嵌的 Redis 服务，通常无需修改

### 功能开关
```env
ENABLE_REALTIME=false   # 是否启用实时协作（需 Redis）
```

## 📁 目录结构说明

```
SmartTable/
├── SmartTable.exe (或 smarttable)   # 主程序
├── start.bat (或 start.sh)          # 启动脚本
├── stop.bat (或 stop.sh)            # 停止脚本
├── redis-server (或 .exe)           # Redis 服务
├── config/
│   └── .env                         # 配置文件
├── data/                            # 数据目录（运行后生成）
│   ├── smarttable.db                # SQLite 数据库
│   └── uploads/                     # 上传文件
└── logs/                            # 日志文件（运行后生成）
```

## ❓ 常见问题

### Q1: 启动时报 "Port 5000 is already in use"
**A**: 端口被占用，解决方案：
1. 停止占用端口的程序（可能是之前的实例未完全关闭）
2. 或修改 `config/.env` 中的 `FLASK_PORT` 为其他端口（如 8080）

### Q2: Redis 启动失败
**A**:
1. 检查是否有其他 Redis 实例在运行（默认端口 6379）
2. 查看 `config/.env` 中的 `REDIS_URL` 配置
3. 确认 `redis-server` 文件存在于程序目录

### Q3: 无法访问 http://localhost:5000
**A**:
1. 确认程序已成功启动（控制台无错误信息）
2. 检查防火墙是否阻止了端口 5000
3. 尝试使用 http://127.0.0.1:5000 访问

### Q4: 如何备份数据？
**A**:
1. 停止服务
2. 备份 `data/smarttable.db` 和 `data/uploads/` 目录
3. 恢复时替换对应文件即可

### Q5: 如何更新版本？
**A**:
1. 停止正在运行的旧版本
2. 替换 `SmartTable.exe`（或 `smarttable`）文件
3. 保留 `data/` 和 `config/` 目录不变
4. 重新启动即可

## 🔧 高级配置

### 远程访问配置
如需从其他设备访问本机运行的 SmartTable：

1. 修改 `config/.env`:
   ```env
   FLASK_HOST=0.0.0.0
   ```
2. 防火墙放行端口 5000:
   ```bash
   # Windows 防火墙（以管理员身份运行）
   netsh advfirewall firewall add rule name="SmartTable" dir=in action=allow protocol=TCP localport=5000

   # Linux iptables
   sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
   ```
3. 从其他设备访问 `http://你的IP地址:5000`

### 性能优化建议
- 生产环境建议设置 `LOG_LEVEL=WARNING` 减少日志输出
- 大量并发场景可考虑增加 Redis 内存限制
- 定期清理 `logs/` 目录中的旧日志文件

## 📞 技术支持

如遇到问题，请：
1. 查看控制台输出的错误信息
2. 检查 `logs/smarttable.log` 日志文件
3. 确认系统要求是否满足
4. 参考官方文档或提交 Issue

---

**版本**: 1.0.0
**更新日期**: 2026-05-03
'''

    readme = release_dir / 'README.md'
    readme.write_text(readme_content, encoding='utf-8')
    print(f'✓ README.md 已生成: {readme}')

def main():
    parser = argparse.ArgumentParser(description='SmartTable 跨平台构建工具')
    parser.add_argument(
        'platform',
        choices=['windows', 'linux', 'all'],
        help='目标平台'
    )
    parser.add_argument(
        '--skip-frontend',
        action='store_true',
        help='跳过前端构建（如果已完成）'
    )

    args = parser.parse_args()

    print('='*60)
    print('  SmartTable 跨平台打包构建工具')
    print('='*60)

    # Step 1: 构建前端
    if not args.skip_frontend:
        build_frontend()
    else:
        print('\n[跳过] 前端构建步骤')

    platforms = []
    if args.platform == 'all':
        platforms = ['windows', 'linux']
    else:
        platforms = [args.platform]

    for platform in platforms:
        # Step 2: 构建后端
        build_backend(platform)

        # Step 3: 准备发布包
        prepare_release_package(platform)

    print('\n' + '='*60)
    print('  ✓ 所有构建任务完成！')
    print('='*60)
    print(f'\n发布包位置: {Path(__file__).parent / "release"}')
    print('\n下一步:')
    print('  1. 测试各平台的可执行文件')
    print('  2. 在纯净环境中验证功能完整性')
    print('  3. （可选）制作安装程序或压缩包分发')

if __name__ == '__main__':
    main()
```

---

## 4. 交付物清单

### 4.1 最终发布包结构

```
smarttable-release-v1.0/
├── Windows/                          # Windows x64 版本
│   ├── SmartTable.exe               # 主程序（~150-250 MB）
│   ├── start.bat                    # 启动脚本
│   ├── stop.bat                     # 停止脚本
│   ├── redis-server.exe             # Redis 服务（~2-5 MB）
│   ├── config/
│   │   └── .env                     # 默认配置
│   └── README.md                    # 详细运行说明
│
├── Linux/                            # Linux x64 版本
│   ├── smarttable                   # 主程序（~100-200 MB）
│   ├── start.sh                     # 启动脚本（需 chmod +x）
│   ├── stop.sh                      # 停止脚本
│   ├── redis-server                 # Redis 服务（~2-5 MB）
│   ├── config/
│   │   └── .env                     # 默认配置
│   └── README.md                    # 详细运行说明
│
└── README.md                         # 总体说明文档
```

### 4.2 文件大小估算

| 组件 | Windows | Linux | 说明 |
|------|---------|-------|------|
| SmartTable.exe / smarttable | 150-250 MB | 100-200 MB | 含 Python + 所有依赖 |
| redis-server | 2-5 MB | 2-5 MB | Redis 单文件版 |
| 配置及文档 | < 1 MB | < 1 MB | .env + README |
| **总计** | **155-256 MB** | **105-206 MB** | |

> 注：实际大小取决于 UPX 压缩率和依赖数量

---

## 5. 测试验证标准

### 5.1 环境准备测试

**测试场景**: 纯净操作系统（无开发工具、无 Python、无 Docker）

**验证清单**:
- [ ] 双击 `start.bat` / 运行 `./start.sh` 能正常启动
- [ ] 控制台显示 "SmartTable started successfully"
- [ ] Redis 自动启动且无报错
- [ ] 浏览器访问 http://localhost:5000 显示登录页面
- [ ] 运行 `create-admin` 命令能创建管理员账户

### 5.2 功能完整性测试

**核心业务流程**:

1. **用户认证**
   - [ ] 注册新用户
   - [ ] 登录/登出
   - [ ] JWT Token 刷新
   - [ ] 密码重置

2. **基础数据管理**
   - [ ] 创建 Base（工作区）
   - [ ] 创建 Table（表格）
   - [ ] 添加字段（各种类型）
   - [ ] 添加/编辑/删除记录
   - [ ] 导入 Excel/CSV 数据
   - [ ] 导出数据为 Excel

3. **视图功能**
   - [ ] 表格视图（TableView）
   - [ ] 看板视图（KanbanView）
   - [ ] 日历视图（CalendarView）
   - [ ] 甘特图视图（GanttView）
   - [ ] 画廊视图（GalleryView）
   - [ ] 表单视图（FormView）

4. **高级功能**
   - [ ] 成员管理与权限
   - [ ] 分享链接生成与访问
   - [ ] 仪表盘（Dashboard）
   - [ ] 文件附件上传/下载
   - [ ] 公式计算
   - [ ] 数据筛选/排序/分组

### 5.3 数据持久化测试

**SQLite 数据库测试**:
- [ ] 重启应用后数据不丢失
- [ ] 数据库文件正确创建在 `data/` 目录
- [ ] 并发写入不损坏数据库
- [ ] 数据库文件可备份和恢复

**文件存储测试**:
- [ ] 上传的文件保存在 `data/uploads/` 目录
- [ ] 重启后文件仍可正常访问
- [ ] 文件删除后磁盘空间释放

### 5.4 Redis 集成测试

**缓存功能测试**:
- [ ] 页面加载速度合理（有缓存加速）
- [ ] 缓存过期机制正常工作
- [ ] Redis 连接断开后应用降级运行（不崩溃）

**实时协作测试**（如启用）:
- [ ] 多用户同时编辑同一单元格
- [ ] 冲突检测和解决机制正常
- [ ] 在线用户列表实时更新

### 5.5 性能与稳定性测试

- [ ] 连续运行 24 小时无崩溃
- [ ] 内存占用稳定（无明显泄漏）
- [ ] 同时支持 10+ 用户并发访问
- [ ] 1000+ 条记录查询响应时间 < 2 秒

---

## 6. 已知限制与注意事项

### 6.1 技术限制

1. **首次启动延迟**: PyInstaller --onefile 模式需要解压依赖，首次启动可能需要 5-15 秒
2. **体积较大**: 由于包含完整 Python 运行时和所有依赖，文件较大
3. **杀毒软件误报**: 部分杀毒软件可能将 PyInstaller 打包的程序标记为可疑（需添加信任）
4. **Redis 端口冲突**: 如果系统已有 Redis 运行在 6379 端口，需修改配置

### 6.2 平台特定注意

**Windows**:
- 需要安装 [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Windows Defender 可能扫描大文件导致启动慢
- 建议将程序放在简单路径（避免中文、空格、特殊字符）

**Linux**:
- 需要给予 `start.sh` 执行权限: `chmod +x start.sh`
- CentOS/RHEL 可能需要安装额外的 glibc 库
- SELinux 可能阻止程序运行（需配置策略或临时关闭）

### 6.3 安全建议

1. **必须修改默认密钥**: `SECRET_KEY` 和 `JWT_SECRET_KEY`
2. **生产环境禁用 DEBUG 模式**
3. **定期备份数据库文件**
4. **如需公网访问，建议配置 HTTPS 反向代理**
5. **及时更新到最新版本**

---

## 7. 未来改进方向

### 7.1 短期优化（v1.1）

- [ ] 制作 NSIS/Inno Setup 安装程序（Windows）
- [ ] 制作 .deb/.rpm 安装包（Linux）
- [ ] 添加自动更新功能
- [ ] 优化启动速度（预解压机制）

### 7.2 中期增强（v2.0）

- [ ] 支持嵌入式 Redis（完全消除外部依赖）
- [ ] 添加系统托盘图标（最小化到托盘）
- [ ] 支持多实例运行（不同端口）
- [ ] Web 管理界面（配置向导）

### 7.3 长期规划（v3.0）

- [ ] 使用 Go/Rust 重写后端（更小的体积和更好的性能）
- [ ] 支持容器化单文件分发（类似 Docker App）
- [ ] 云同步和备份功能
- [ ] 移动端适配

---

## 附录 A: 开发环境搭建

### A.1 Windows 开发环境

```powershell
# 1. 安装 Python 3.11+
# 下载: https://www.python.org/downloads/

# 2. 安装 PyInstaller
pip install pyinstaller==6.3.0

# 3. 安装 Node.js 18+ (用于构建前端)
# 下载: https://nodejs.org/

# 4. 安装 UPX (可选，用于压缩可执行文件)
# 下载: https://upx.github.io/
# 放入系统 PATH

# 5. 克隆项目并安装依赖
git clone <repository-url>
cd smart-table-spec
pip install -r smarttable-backend/requirements.txt
cd smart-table && npm install
```

### A.2 Linux 开发环境

```bash
# 1. 安装系统依赖
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3-pip python3-venv \
    nodejs npm gcc g++ libpq-dev

# 2. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 3. 安装 Python 依赖
pip install pyinstaller==6.3.0
pip install -r smarttable-backend/requirements.txt

# 4. 安装前端依赖
cd smart-table && npm install
```

---

## 附录 B: 故障排查指南

### B.1 常见错误代码

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `ModuleNotFoundError` | PyInstaller 未包含某模块 | 在 .spec 的 hiddenimports 中添加 |
| `Permission denied` | 权限不足 | Linux: chmod +x; Windows: 以管理员身份运行 |
| `Address already in use` | 端口被占用 | 修改 FLASK_PORT 或结束占用进程 |
| `Redis connection refused` | Redis 未启动 | 检查 redis-server 是否存在并可执行 |
| `Database is locked` | SQLite 并发锁定 | 减少并发或使用 WAL 模式 |

### B.2 日志分析

关键日志位置:
- 应用日志: `logs/smarttable.log`
- 控制台输出: 启动脚本的实时输出
- Redis 日志: 默认输出到控制台（可通过配置重定向到文件）

---

**文档维护**: 本文档应随项目迭代持续更新，确保与实际实现保持一致。
