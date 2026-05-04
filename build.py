#!/usr/bin/env python3
"""
SmartTable v1.2.3 跨平台自动化构建脚本
"""

import subprocess
import os
import sys
import shutil
import argparse
import time
import platform
from pathlib import Path
from datetime import datetime

VERSION = "1.2.3"
PROJECT_NAME = "SmartTable"
PROJECT_ROOT = Path(__file__).parent.absolute()
FRONTEND_DIR = PROJECT_ROOT / "smart-table"
BACKEND_DIR = PROJECT_ROOT / "smarttable-backend"
DIST_DIR = FRONTEND_DIR / "dist"
RELEASE_DIR = PROJECT_ROOT / "release"
SPEC_FILE = PROJECT_ROOT / "smarttable.spec"

PLATFORMS = {
    'windows': {'exe_name': 'SmartTable.exe', 'display_name': 'Windows',
                'redis_src': PROJECT_ROOT / 'tools' / 'redis-windows' / 'redis-server.exe',
                'redis_dest': 'redis-server.exe'},
    'linux': {'exe_name': 'smarttable', 'display_name': 'Linux',
              'redis_src': PROJECT_ROOT / 'tools' / 'redis-linux' / 'redis-server',
              'redis_dest': 'redis-server'}
}


def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}] [{level}] {message}')


def run_command(cmd, cwd=None, capture=False):
    """
    执行 shell 命令
    Args:
        cmd: 命令列表或字符串
        cwd: 工作目录
        capture: 是否捕获输出
    Returns:
        CompletedProcess
    """
    # Windows 兼容性处理：cmd 为列表时，在 Windows 上需要 shell=True 才能执行 .cmd 脚本
    is_windows = platform.system() == 'Windows'
    
    kwargs = {
        'cwd': cwd or PROJECT_ROOT,
        'shell': isinstance(cmd, str) or (is_windows and isinstance(cmd, list)),
        'text': True,
    }
    if capture:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0 and capture:
        log(f'命令失败: {result.stderr}', 'ERROR')
        sys.exit(1)
    return result


def check_prerequisites(skip_frontend=False):
    log('检查前置条件...', 'STEP')
    if not skip_frontend:
        for cmd, name in [('node', 'Node.js'), ('npm', 'npm')]:
            try:
                r = run_command([cmd, '--version'], capture=True)
                log(f'{name}: {r.stdout.strip()}')
            except: log(f'⚠️ {name} 未检测到（已跳过前端构建）', 'WARNING')

    r = run_command([sys.executable, '--version'], capture=True)
    log(f'Python: {r.stdout.strip()}')
    try:
        r = run_command([sys.executable, '-m', 'PyInstaller', '--version'], capture=True)
        log(f'PyInstaller: {r.stdout.strip()}')
    except: log('❌ PyInstaller 未安装！运行: pip install pyinstaller==6.3.0', 'ERROR'); sys.exit(1)
    log('✅ 前置检查通过', 'SUCCESS')


def clean_build_artifacts(skip_frontend=False):
    log('清理旧产物...', 'STEP')
    # 清理 PyInstaller 产物
    for d in [PROJECT_ROOT / 'build', PROJECT_ROOT / 'dist', RELEASE_DIR]:
        if d.exists(): shutil.rmtree(d); log(f'  删除: {d.relative_to(PROJECT_ROOT)}')
    
    # 只有在不跳过前端构建时才清理前端产物
    if not skip_frontend:
        if DIST_DIR.exists(): shutil.rmtree(DIST_DIR); log(f'  删除: {DIST_DIR.relative_to(PROJECT_ROOT)}')
    else:
        if DIST_DIR.exists():
            log(f'  ✓ 保留前端产物: {DIST_DIR}', 'SUCCESS')


def build_frontend():
    log('='*60, 'STEP'); log('第 1 步：构建前端 (Vue + Vite)', 'STEP'); log('='*60, 'STEP')
    t = time.time()
    run_command(['npm', 'install'], cwd=FRONTEND_DIR)
    run_command(['npm', 'run', 'build'], cwd=FRONTEND_DIR)
    if not DIST_DIR.exists(): log('❌ 前端构建失败！', 'ERROR'); sys.exit(1)
    size = sum(f.stat().st_size for f in DIST_DIR.rglob('*') if f.is_file()) / (1024*1024)
    log(f'✅ 前端完成 ({time.time()-t:.1f}s, {size:.1f} MB)', 'SUCCESS')


def build_backend(platform):
    log('='*60, 'STEP'); log(f'第 2 步：构建 {PLATFORMS[platform]["display_name"]} 后端', 'STEP'); log('='*60, 'STEP')
    t = time.time()
    for d in [PROJECT_ROOT / 'build', PROJECT_ROOT / 'dist']:
        if d.exists(): shutil.rmtree(d)
    exe = f'{PROJECT_NAME}_{platform}'
    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', '-y', str(SPEC_FILE)]
    # 注意：--onefile, --name, --windowed 等选项已在 .spec 文件中定义
    # 如果需要修改平台特定选项，请编辑 smarttable.spec 文件
    run_command(cmd)
    ext = '.exe' if platform == 'windows' else ''
    out = PROJECT_ROOT / 'dist' / f'{exe}{ext}'
    if not out.exists(): log(f'❌ 构建失败: {out}', 'ERROR'); sys.exit(1)
    size = out.stat().st_size / (1024*1024)
    log(f'✅ 后端完成 ({time.time()-t:.1f}s, {size:.1f} MB) -> {out}', 'SUCCESS')


def prepare_release_package(platform):
    log('='*60, 'STEP'); log(f'第 3 步：准备 {PLATFORMS[platform]["display_name"]} 发布包', 'STEP'); log('='*60, 'STEP')
    info = PLATFORMS[platform]
    release_subdir = RELEASE_DIR / info['display_name']
    release_subdir.mkdir(parents=True, exist_ok=True)

    # 复制主程序
    ext = '.exe' if platform == 'windows' else ''
    # .spec 文件中的 name 是 'SmartTable'，不是 'SmartTable_windows'
    src = PROJECT_ROOT / 'dist' / f'SmartTable{ext}'
    if not src.exists():
        log(f'❌ 未找到构建产物: {src}', 'ERROR')
        sys.exit(1)
    shutil.copy2(src, release_subdir / info['exe_name'])
    log(f'  主程序: {info["exe_name"]} ({src.stat().st_size/1e6:.1f} MB)')

    # Redis
    redis_dst = release_subdir / info['redis_dest']
    if info['redis_src'].exists():
        shutil.copy2(info['redis_src'], redis_dst)
        if platform == 'linux': os.chmod(redis_dst, 0o755)
        log(f'  Redis: {info["redis_dest"]}')
    else: log(f'  ⚠️ Redis 未找到', 'WARNING')

    # 配置
    config_dir = release_subdir / 'config'; config_dir.mkdir(exist_ok=True)
    env_src = BACKEND_DIR / '.env.example'
    if env_src.exists(): shutil.copy2(env_src, config_dir / '.env')

    # 脚本
    if platform == 'windows':
        _create_windows_scripts(release_subdir)
    else:
        _create_linux_scripts(release_subdir)

    # README
    _create_readme(release_subdir, platform)

    # 目录
    for d in ['data', 'uploads', 'logs']:
        (release_subdir / d).mkdir(exist_ok=True); (release_subdir / d / '.gitkeep').write_text('')

    log(f'✅ 发布包就绪: {release_subdir}', 'SUCCESS')


def _create_windows_scripts(d):
    (d / 'start.bat').write_text('''@echo off
chcp 65001 >nul
title SmartTable Server v{ver}
echo ============================================
echo   SmartTable v{ver}
echo ============================================
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server">NUL
if "%ERRORLEVEL%"=="0" (echo [Redis] 已运行) else (start /B "" "%~dp0redis-server.exe" --port 6379 >nul 2>&1 & timeout /t 2 >nul)
echo.
echo [SmartTable] 启动中... http://localhost:5000
echo 按 Ctrl+C 停止
start /B "" "%~dp0SmartTable.exe"
:loop
timeout /t 3600 >nul & goto loop
'''.format(ver=VERSION), encoding='utf-8')

    (d / 'stop.bat').write_text('''@echo off
echo 停止 SmartTable...
taskkill /F /IM SmartTable.exe >nul 2>&1
taskkill /F /IM redis-server.exe >nul 2>&1
echo ✓ 已停止 & pause''', encoding='utf-8')


def _create_linux_scripts(d):
    s = '''#!/bin/bash
echo "SmartTable v{ver}"
cd "$(dirname "$0")"
if ! pgrep -x redis-server >/dev/null; then
    ./redis-server --port 6379 --daemonize yes 2>/dev/null && echo "[Redis] ✓" || echo "[Redis] ⚠️"
fi
echo "启动中... http://localhost:5000"
./smarttable &
PID=$!
cleanup() {{ kill $PID 2>/dev/null; pkill -x redis-server 2>/dev/null; exit 0; }}
trap cleanup SIGINT SIGTERM
wait $PID
'''.format(ver=VERSION)
    sh = d / 'start.sh'
    sh.write_text(s, encoding='utf-8'); os.chmod(sh, 0o755)

    (d / 'stop.sh').write_text('#!/bin/bash\npkill -f smarttable; pkill -x redis-server; echo ✓ 已停止\n', encoding='utf-8')


def _create_readme(d, platform):
    plat = PLATFORMS[platform]['display_name'].upper()
    exe = 'SmartTable.exe' if platform == 'windows' else './smarttable'
    (d / 'README.md').write_text(f'''# SmartTable v{VERSION} 运行说明

> 平台: {plat} (x86_64) | 更新日期: {datetime.now().strftime("%Y-%m-%d")}

## 快速开始

1. 解压到目标目录（保持文件夹结构完整）
2. 编辑 `config/.env`，**修改 SECRET_KEY 和 JWT_SECRET_KEY**
3. {"双击 start.bat" if platform == "windows" else "运行 chmod +x start.sh && ./start.sh"}
4. 浏览器打开 http://localhost:5000

## 首次运行：创建管理员

{"SmartTable.exe create-admin admin@ex.com pass123 Admin" if platform == "windows" else "./smarttable create-admin admin@ex.com pass123 Admin"}

## 常见问题

- 端口被占用: 修改 .env 的 FLASK_PORT
- Redis 启动失败: 可忽略，核心功能正常
- 杀毒软件误报: 添加信任区域

## 技术支持

查看控制台输出和 logs/ 目录下的日志文件。
''', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=f'SmartTable v{VERSION} 构建工具')
    parser.add_argument('platform', choices=['windows', 'linux', 'all'])
    parser.add_argument('--skip-frontend', action='store_true')
    parser.add_argument('--clean-only', action='store_true')
    args = parser.parse_args()

    print(f'\n{"="*70}\n  SmartTable v{VERSION} 跨平台打包工具\n  {datetime.now()}\n{"="*70}\n')

    if args.clean_only: clean_build_artifacts(); return

    check_prerequisites(skip_frontend=args.skip_frontend)
    clean_build_artifacts(skip_frontend=args.skip_frontend)

    platforms = ['windows', 'linux'] if args.platform == 'all' else [args.platform]

    # 前端构建逻辑
    need_frontend = not args.skip_frontend and not DIST_DIR.exists()
    if need_frontend:
        try:
            build_frontend()
        except Exception as e:
            log(f'⚠️ 前端构建失败: {e}', 'WARNING')
            log('提示: 如果已有 dist/ 目录，可使用 --skip-frontend 参数', 'INFO')
            if not DIST_DIR.exists():
                log('❌ 缺少前端构建产物，无法继续', 'ERROR')
                sys.exit(1)
    elif DIST_DIR.exists():
        log(f'✓ 使用已有的前端构建产物: {DIST_DIR}', 'SUCCESS')
    else:
        log('⚠️ 跳过前端构建（--skip-frontend）', 'WARNING')

    for p in platforms:
        print(); build_backend(p); prepare_release_package(p)

    print(f'\n{"="*70}\n  ✅ 所有任务完成！\n{"="*70}')
    print(f'\n发布包: {RELEASE_DIR}')
    for p in platforms: print(f'  • {p.upper()}: {RELEASE_DIR / PLATFORMS[p]["display_name"]}')
    print(f'\n总耗时: {time.time()-globals().setdefault("_t", time.time()):.1f}s\n')


if __name__ == '__main__':
    globals()['_t'] = time.time()
    main()
