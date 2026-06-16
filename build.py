#!/usr/bin/env python3
"""
SmartTable 跨平台自动化构建脚本
支持自动生成 Windows EXE 文件属性信息
版本号由 version.json 统一管理
"""

import subprocess
import os
import sys
import json  # 新增：用于解析 version.json
import shutil
import argparse
import time
import platform
from pathlib import Path
from datetime import datetime

# ===== 版本号集中管理（从 version.json 动态读取）=====
VERSION_FILE = Path(__file__).parent / 'version.json'

def load_version():
    """
    从 version.json 加载版本信息（唯一真实来源）

    Returns:
        dict: 包含版本号、产品信息等的字典

    Raises:
        SystemExit: 当文件不存在或格式错误时退出程序
    """
    if not VERSION_FILE.exists():
        log(f'❌ 错误: version.json 不存在', 'ERROR')
        log(f'   请在项目根目录创建 version.json', 'ERROR')
        log(f'\n示例内容:', 'INFO')
        example = {
            "version": "0.0.1",
            "product_name": "Your Product",
            "company_name": "Your Company",
            "copyright": f"Copyright © {datetime.now().year} Your Company. All rights reserved.",
            "description": {
                "zh_CN": "产品描述",
                "en_US": "Product description"
            }
        }
        print(json.dumps(example, indent=2, ensure_ascii=False))
        sys.exit(1)

    try:
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log(f'❌ 错误: version.json 格式无效', 'ERROR')
        log(f'   位置: 第 {e.lineno} 行, 第 {e.colno} 列', 'ERROR')
        log(f'   详情: {e.msg}', 'ERROR')
        sys.exit(1)

    # 校验必填字段
    required_fields = ['version', 'product_name', 'company_name']
    missing = [f for f in required_fields if f not in data]
    if missing:
        log(f'❌ 错误: version.json 缺少必填字段: {", ".join(missing)}', 'ERROR')
        sys.exit(1)

    return data


def parse_version_tuple(version_str):
    """
    将版本字符串转换为元组格式

    Args:
        version_str: 如 "1.2.3"

    Returns:
        tuple: 如 (1, 2, 3, 0) 用于 Windows 版本资源
    """
    parts = list(map(int, version_str.split('.')))
    return tuple(parts + [0] * (4 - len(parts)))


# 启动时立即加载一次（全局单例）
_VERSION_DATA = load_version()
VERSION = _VERSION_DATA['version']  # "1.2.3"
FILE_VERSION_TUPLE = parse_version_tuple(VERSION)  # (1, 2, 3, 0)
PRODUCT_VERSION_TUPLE = FILE_VERSION_TUPLE

PROJECT_NAME = "SmartTable"
PROJECT_ROOT = Path(__file__).parent.absolute()
FRONTEND_DIR = PROJECT_ROOT / "smart-table"
BACKEND_DIR = PROJECT_ROOT / "smarttable-backend"
DIST_DIR = FRONTEND_DIR / "dist"
RELEASE_DIR = PROJECT_ROOT / "release"
SPEC_FILE = PROJECT_ROOT / "smarttable.spec"
VERSION_INFO_FILE = BACKEND_DIR / "version_info.txt"

# ===== 版本信息配置（从 version.json 动态生成）=====
VERSION_INFO = {
    'file_version': FILE_VERSION_TUPLE,
    'product_version': PRODUCT_VERSION_TUPLE,
    'file_description': {
        'zh_CN': f'{_VERSION_DATA["description"]["zh_CN"]} v{VERSION}',
        'en_US': f'{_VERSION_DATA["description"]["en_US"]} v{VERSION}',
    },
    'product_name': _VERSION_DATA.get('product_name', 'SmartTable'),
    'company_name': _VERSION_DATA.get('company_name', 'SmartTable Team'),
    'copyright': _VERSION_DATA.get('copyright', '').format(year=datetime.now().year),
    'comments': {
        'zh_CN': _VERSION_DATA.get('description', {}).get('zh_CN', ''),
        'en_US': _VERSION_DATA.get('description', {}).get('en_US', ''),
    },
    'original_filename': _VERSION_DATA.get('metadata', {}).get('original_filename', 'SmartTable.exe'),
    'internal_name': _VERSION_DATA.get('metadata', {}).get('internal_name', 'smarttable'),
    'private_build': 'PyInstaller Packaged Application',
    'special_build': f'Production Release v{VERSION} with SQLite + Redis Integration',
}

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


def generate_version_info():
    """
    自动生成 Windows 版本信息文件 (version_info.txt)
    
    该文件用于 PyInstaller 打包时设置 EXE 文件的属性信息：
    - 文件说明 (FileDescription)
    - 文件版本 (FileVersion)
    - 产品名称 (ProductName)
    - 产品版本 (ProductVersion)
    - 版权信息 (LegalCopyright)
    - 公司名 (Company Name)
    - 注释 (Comments)
    
    Returns:
        bool: 是否成功生成
    """
    log('生成 Windows 版本信息...', 'STEP')
    
    try:
        # 获取当前日期
        now = datetime.now()
        
        # 构建版本号元组
        fv = VERSION_INFO['file_version']      # FileVersion
        pv = VERSION_INFO['product_version']   # ProductVersion
        
        version_content = f'''# UTF-8
#
# SmartTable Windows Version Info
# Auto-generated by build.py on {now.strftime('%Y-%m-%d %H:%M:%S')}
# Version: {VERSION}
#

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={fv},
    prodvers={pv},
    mask=0x3f,
    flags=0x0,
    os=0x40004,  # VOS_NT Windows NT
    subtype=0x0,  # VFT_APP Application
    date=({now.year}, {now.month}, {now.day}),
  ),

  kids=[
    StringFileInfo(
      [
        StringTable(
          '080404B0',  # 简体中文 + Unicode
          'FileDescription': '{VERSION_INFO["file_description"]["zh_CN"]}',
          'FileVersion': '{".".join(map(str, fv))}',
          'InternalName': '{VERSION_INFO["internal_name"]}',
          'LegalCopyright': '{VERSION_INFO["copyright"]}',
          'OriginalFilename': '{VERSION_INFO["original_filename"]}',
          'ProductName': '{VERSION_INFO["product_name"]}',
          'ProductVersion': '{".".join(map(str, pv))}',
          'Company Name': '{VERSION_INFO["company_name"]}',
          'Comments': '{VERSION_INFO["comments"]["zh_CN"]}',
          'Private Build': '{VERSION_INFO["private_build"]}',
          'Special Build': '{VERSION_INFO["special_build"]}',
        ),
        StringTable(
          '040904B0',  # 英语(美国) + Unicode
          'FileDescription': '{VERSION_INFO["file_description"]["en_US"]}',
          'FileVersion': '{".".join(map(str, fv))}',
          'InternalName': '{VERSION_INFO["internal_name"]}',
          'LegalCopyright': '{VERSION_INFO["copyright"]}',
          'OriginalFilename': '{VERSION_INFO["original_filename"]}',
          'ProductName': '{VERSION_INFO["product_name"]}',
          'ProductVersion': '{".".join(map(str, pv))}',
          'Company Name': '{VERSION_INFO["company_name"]}',
          'Comments': '{VERSION_INFO["comments"]["en_US"]}',
          'Private Build': '{VERSION_INFO["private_build"]}',
          'Special Build': '{VERSION_INFO["special_build"]}',
        ),
      ]
    ),
    VarFileInfo(
      [VarStruct('Translation', [1033, 1200]),  # 简体中文
       VarStruct('Translation', [1033, 1252]),  # 简体中文(代码页)
       VarStruct('Translation', [2052, 1200]),  # 英语(美国)
       VarStruct('Translation', [2052, 1252]),  # 英语(美国)(代码页)
      ]
    ),
  ]
)
'''
        
        # 写入文件
        with open(VERSION_INFO_FILE, 'w', encoding='utf-8') as f:
            f.write(version_content)
        
        log(f'✅ 版本信息文件已生成: {VERSION_INFO_FILE}', 'SUCCESS')
        log(f'   文件说明: {VERSION_INFO["file_description"]["zh_CN"][:40]}')
        log(f'   文件版本: {".".join(map(str, fv))}')
        log(f'   产品版本: {".".join(map(str, pv))}')
        log(f'   版权: {VERSION_INFO["copyright"][:50]}')
        
        return True

    except Exception as e:
        log(f'❌ 生成版本信息失败: {e}', 'ERROR')
        return False


def sync_package_json():
    """
    将 version.json 的版本号同步到 package.json

    仅当版本不同时才写入，避免不必要的文件变更。
    这确保了前端 npm 生态系统的版本一致性。
    """
    pkg_path = FRONTEND_DIR / 'package.json'

    if not pkg_path.exists():
        log(f'⚠️ package.json 不存在，跳过同步', 'WARNING')
        return False

    try:
        with open(pkg_path, 'r', encoding='utf-8') as f:
            pkg_data = json.load(f)

        current_version = pkg_data.get('version', '')

        if current_version == VERSION:
            log(f'✓ package.json 版本已是最新 ({VERSION})', 'SUCCESS')
            return True

        # 更新版本号
        pkg_data['version'] = VERSION

        with open(pkg_path, 'w', encoding='utf-8') as f:
            json.dump(pkg_data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # 确保文件以换行符结尾

        log(f'✅ 已同步 package.json: {current_version} → {VERSION}', 'SUCCESS')
        return True

    except Exception as e:
        log(f'⚠️ 同步 package.json 失败: {e}', 'WARNING')
        return False


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
    # 清理 PyInstaller 产物（添加错误处理，避免因文件锁定导致构建失败）
    for d in [PROJECT_ROOT / 'build', PROJECT_ROOT / 'dist', RELEASE_DIR]:
        if d.exists():
            try:
                shutil.rmtree(d)
                log(f'  删除: {d.relative_to(PROJECT_ROOT)}')
            except (PermissionError, OSError) as e:
                log(f'  ⚠️ 无法删除 {d.relative_to(PROJECT_ROOT)}: {e}', 'WARNING')
                log(f'     （可能有程序正在使用该目录，尝试继续构建...）', 'WARNING')
    
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
    # PyInstaller .spec 文件中定义的 name 是 'SmartTable'（不带平台后缀）
    exe_name = 'SmartTable'  # 与 smarttable.spec 中的 name 保持一致
    cmd = [sys.executable, '-m', 'PyInstaller', '--clean', '-y', str(SPEC_FILE)]
    run_command(cmd)
    
    ext = '.exe' if platform == 'windows' else ''
    out = PROJECT_ROOT / 'dist' / f'{exe_name}{ext}'
    if not out.exists(): 
        # 尝试查找可能的变体
        candidates = list(PROJECT_ROOT.glob(f'dist/*{ext}')) or list(PROJECT_ROOT.glob(f'dist/{PROJECT_NAME}*{ext}'))
        if candidates:
            out = candidates[0]
            log(f'⚠️ 找到替代文件: {out.name}', 'WARNING')
        else:
            log(f'❌ 构建失败: 未找到可执行文件 (期望: {out})', 'ERROR')
            log(f'   dist/ 目录内容:', 'ERROR')
            dist_dir = PROJECT_ROOT / 'dist'
            if dist_dir.exists():
                for f in dist_dir.iterdir():
                    if f.is_file(): log(f'     - {f.name} ({f.stat().st_size/1e6:.1f} MB)', 'ERROR')
            sys.exit(1)
    size = out.stat().st_size / (1024*1024)
    log(f'✅ 后端完成 ({time.time()-t:.1f}s, {size:.1f} MB) -> {out}', 'SUCCESS')


def prepare_release_package(platform):
    log('='*60, 'STEP'); log(f'第 3 步：准备 {PLATFORMS[platform]["display_name"]} 发布包', 'STEP'); log('='*60, 'STEP')
    info = PLATFORMS[platform]
    release_subdir = RELEASE_DIR / info['display_name']
    release_subdir.mkdir(parents=True, exist_ok=True)

    # 复制主程序
    ext = '.exe' if platform == 'windows' else ''
    # .spec 文件中的 name 是 'SmartTable'（不带平台后缀），与 build_backend 函数保持一致
    exe_name = 'SmartTable'
    src = PROJECT_ROOT / 'dist' / f'{exe_name}{ext}'
    
    if not src.exists():
        # 智能查找：尝试匹配任何 exe 文件
        candidates = list(PROJECT_ROOT.glob(f'dist/*{ext}'))
        if candidates:
            src = candidates[0]
            log(f'⚠️ 使用替代文件: {src.name}', 'WARNING')
        else:
            log(f'❌ 未找到构建产物: {src}', 'ERROR')
            log(f'   请先运行: python build.py {platform}', 'ERROR')
            return
    
    shutil.copy2(src, release_subdir / info['exe_name'])
    log(f'  主程序: {info["exe_name"]} ({src.stat().st_size/1e6:.1f} MB)')

    # Redis
    redis_dst = release_subdir / info['redis_dest']
    if info['redis_src'].exists():
        shutil.copy2(info['redis_src'], redis_dst)
        if platform == 'linux': os.chmod(redis_dst, 0o755)
        log(f'  Redis: {info["redis_dest"]}')
    else: log(f'  ⚠️ Redis 未找到', 'WARNING')

    # 配置文件（优先级：config/.env > smarttable-backend/.env.example）
    config_dir = release_subdir / 'config'; config_dir.mkdir(exist_ok=True)

    # 1. 优先查找用户自定义配置（config/.env）
    user_env = PROJECT_ROOT / 'config' / '.env'
    if user_env.exists():
        shutil.copy2(user_env, config_dir / '.env')
        log(f'  Config: config/.env (用户配置)')
    else:
        # 2. 回退到示例配置
        env_src = BACKEND_DIR / '.env.example'
        if env_src.exists():
            shutil.copy2(env_src, config_dir / '.env')
            log(f'  Config: .env.example (默认模板)')
        else:
            log(f'  ⚠️ 未找到配置文件', 'WARNING')

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
echo   --                                     
echo   GitHub（主仓库）：https://github.com/ldbinac/smart_table
echo   Gitee国内镜像）：https://gitee.com/binac/smart_table
echo   微信公众号：程序员吕洞宾
echo   CSDN：程序员吕洞宾 
echo   稀土掘金：程序员吕洞宾 
echo   知乎：程序员吕洞宾 
echo   邮箱：ldengbin@126.com                                 
echo ============================================
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server">NUL
if "%ERRORLEVEL%"=="0" (echo [Redis] 已运行) else (start /B "" "%~dp0redis-server.exe" --port 6379 >nul 2>&1 & timeout /t 2 >nul)
echo.
echo [SmartTable] 启动中......
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
echo "启动中......"
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
- 数据库切换: 修改 .env 的 DATABASE_URL

## 技术支持

| 平台 | 账号 / 地址 |
|------|------------|
| 🌐 **GitHub**（主仓库） | [https://github.com/ldbinac/smart_table](https://github.com/ldbinac/smart_table) |
| 🇨🇳 **Gitee**（国内镜像） | [https://gitee.com/binac/smart_table](https://gitee.com/binac/smart_table) |
| 💬 **微信公众号** | 程序员吕洞宾 |
| 💻 **CSDN** | 程序员吕洞宾 |
| ⛏ **稀土掘金** | 程序员吕洞宾 |
| 📝 **知乎** | 程序员吕洞宾 |
| 📮 **邮箱** | ldengbin@126.com |

关注不迷路，版本持续迭代中～

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

    # 自动生成 Windows 版本信息文件（用于 EXE 属性设置）
    if platform.system() == 'Windows' or args.platform in ['windows', 'all']:
        generate_version_info()

    platforms = ['windows', 'linux'] if args.platform == 'all' else [args.platform]

    # 同步版本号到 package.json（保持前后端一致）
    sync_package_json()

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
