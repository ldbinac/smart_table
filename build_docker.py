#!/usr/bin/env python3
"""
SmartTable Docker 一键式构建脚本
负责：前端编译、依赖安装、Docker 镜像构建的全流程自动化

用法:
    python build_docker.py                    # 构建镜像（使用已有前端产物或重新构建）
    python build_docker.py --no-cache         # 不使用 Docker 缓存构建
    python build_docker.py --skip-frontend    # 跳过前端构建，使用已有 dist
    python build_docker.py --tag v1.0.0       # 指定镜像标签
    python build_docker.py --push             # 构建并推送到镜像仓库
    python build_docker.py --run              # 构建并启动容器
"""

import subprocess
import os
import sys
import json
import shutil
import argparse
import time
import platform
from pathlib import Path
from datetime import datetime

# ===== 路径配置 =====
PROJECT_ROOT = Path(__file__).parent.absolute()
FRONTEND_DIR = PROJECT_ROOT / "smart-table"
BACKEND_DIR = PROJECT_ROOT / "smarttable-backend"
DIST_DIR = FRONTEND_DIR / "dist"
DOCKER_DIR = PROJECT_ROOT / "docker"

# ===== 配置参数 =====
DEFAULT_IMAGE_NAME = "smarttable"
DEFAULT_TAG = "latest"
VERSION_FILE = PROJECT_ROOT / "version.json"

# ===== Python 3.7+ stdout 编码修复 =====
if sys.version_info >= (3, 7) and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ===== 颜色输出（Windows 兼容） =====
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def supports_color():
        if platform.system() == 'Windows':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                return kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7) != 0
            except:
                return False
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

_USE_COLOR = Colors.supports_color()

def color(text, color_code):
    return f"{color_code}{text}{Colors.RESET}" if _USE_COLOR else text


def safe_print(text):
    """安全打印：自动处理控制台编码问题"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Windows GBK 控制台无法显示 Unicode 字符，转义为 ASCII
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)


def log(message, level='INFO'):
    timestamp = datetime.now().strftime('%H:%M:%S')
    prefix_map = {
        'STEP': color('[STEP]', Colors.CYAN),
        'INFO': color('[INFO]', Colors.BLUE),
        'SUCCESS': color('[SUCCESS]', Colors.GREEN),
        'WARNING': color('[WARNING]', Colors.WARNING),
        'ERROR': color('[ERROR]', Colors.RED),
        'HEADER': color('[HEADER]', Colors.HEADER),
    }
    prefix = prefix_map.get(level, f'[{level}]')
    safe_print(f'{color(timestamp, Colors.BOLD)} {prefix} {message}')


def print_banner():
    version = ""
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                version = data.get('version', '')
        except:
            pass

    banner = f"""
{color('╔══════════════════════════════════════════════════════════╗', Colors.CYAN)}
{color('║', Colors.CYAN)}           {color('SmartTable Docker 构建工具', Colors.BOLD + Colors.HEADER)}           {color('║', Colors.CYAN)}
{color('║', Colors.CYAN)}           {color(f'Version: {version}', Colors.WARNING)}                {color('║', Colors.CYAN)}
{color('║', Colors.CYAN)}           {color(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), Colors.BLUE)}           {color('║', Colors.CYAN)}
{color('╚══════════════════════════════════════════════════════════╝', Colors.CYAN)}
"""
    print(banner)


def _normalize_cmd(cmd):
    """规范化命令：Windows 上处理 .cmd/.bat 脚本"""
    if isinstance(cmd, str):
        return cmd
    if platform.system() == 'Windows' and cmd:
        # npm 在 Windows 上实际是 npm.cmd，需要 shell 支持
        if cmd[0] in ('npm', 'npx', 'yarn', 'pnpm'):
            return subprocess.list2cmdline(cmd)
    return cmd


def run_command(cmd, cwd=None, capture=False, check=True, timeout=None, shell=None):
    """
    执行 shell 命令，带实时输出

    Args:
        cmd: 命令列表或字符串
        cwd: 工作目录
        capture: 是否捕获输出
        check: 失败时是否退出
        timeout: 超时时间（秒）
        shell: 是否使用 shell（None=自动判断）

    Returns:
        CompletedProcess
    """
    is_windows = platform.system() == 'Windows'
    raw_cmd = cmd

    # 规范化命令（Windows npm 兼容）
    cmd = _normalize_cmd(cmd)

    if shell is None:
        shell = isinstance(cmd, str)

    if capture:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or PROJECT_ROOT,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
            )
        except FileNotFoundError:
            log(f'命令未找到: {raw_cmd}', 'ERROR')
            log(f'请确认相关程序已正确安装且已添加到 PATH 环境变量', 'ERROR')
            sys.exit(1)

        if check and result.returncode != 0:
            log(f'命令失败: {raw_cmd}', 'ERROR')
            stderr = result.stderr.strip() if result.stderr else '无错误输出'
            log(f'错误信息: {stderr}', 'ERROR')
            sys.exit(1)
        return result

    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
        )

        for line in process.stdout:
            print(line, end='', flush=True)

        process.wait(timeout=timeout)

        if check and process.returncode != 0:
            log(f'命令失败 (返回码: {process.returncode})', 'ERROR')
            sys.exit(1)

        return subprocess.CompletedProcess(raw_cmd, process.returncode)

    except subprocess.TimeoutExpired:
        process.kill()
        log(f'命令执行超时 (>{timeout}s): {raw_cmd}', 'ERROR')
        sys.exit(1)
    except FileNotFoundError:
        log(f'命令未找到: {raw_cmd}', 'ERROR')
        log(f'请确认相关程序已正确安装且已添加到 PATH 环境变量', 'ERROR')
        sys.exit(1)
    except Exception as e:
        log(f'执行命令时出错: {e}', 'ERROR')
        sys.exit(1)


# ============================================
# 阶段 0: 环境检查
# ============================================
def check_prerequisites():
    log('检查运行环境...', 'STEP')
    log('-' * 50, 'INFO')

    errors = []

    log('  检查 Docker...', 'INFO')
    try:
        result = run_command(['docker', '--version'], capture=True)
        log(f'  ✓ Docker: {result.stdout.strip()}', 'SUCCESS')
    except:
        errors.append('Docker 未安装。请访问 https://docs.docker.com/get-docker/ 安装')

    log('  检查 Docker Compose...', 'INFO')
    compose_found = False
    for compose_cmd in ['docker compose', 'docker-compose']:
        try:
            cmd_parts = compose_cmd.split()
            result = run_command(cmd_parts + ['version'], capture=True)
            log(f'  ✓ {compose_cmd}: {result.stdout.strip()}', 'SUCCESS')
            compose_found = True
            break
        except:
            continue

    if not compose_found:
        errors.append('Docker Compose 未安装')

    log('  检查 Node.js...', 'INFO')
    node_found = False
    npm_found = False
    try:
        result = run_command(['node', '--version'], capture=True)
        log(f'  ✓ Node.js: {result.stdout.strip()}', 'SUCCESS')
        node_found = True
    except:
        log(f'  ⚠ Node.js 未安装，将使用 Docker 多阶段构建前端', 'WARNING')

    if node_found:
        log('  检查 npm...', 'INFO')
        try:
            result = run_command(['npm', '--version'], capture=True)
            log(f'  ✓ npm: {result.stdout.strip()}', 'SUCCESS')
            npm_found = True
        except:
            log(f'  ⚠ npm 未安装（Node.js 已安装但缺少 npm）', 'WARNING')
            log(f'    前端构建将依赖于 Docker 多阶段构建', 'INFO')
    else:
        log(f'  ⚠ npm 未安装（Node.js 不可用）', 'INFO')

    # 检查 Docker 镜像源配置
    log('  检查 Docker 镜像源...', 'INFO')
    try:
        result = run_command(['docker', 'info', '--format', '{{.RegistryConfig.Mirrors}}'], capture=True, check=False)
        mirrors = result.stdout.strip()
        if mirrors and mirrors != '[]':
            log(f'  ⚠ 检测到 Docker 镜像加速器配置: {mirrors}', 'WARNING')
            log(f'    如果构建失败，请检查镜像加速器是否可用', 'INFO')
            log(f'    或移除 Docker Desktop 设置中的镜像加速器', 'INFO')
        else:
            log(f'  ✓ Docker 镜像源配置正常（未使用加速器）', 'SUCCESS')
    except:
        log(f'  - 无法检查 Docker 镜像源配置', 'INFO')

    log('  检查项目结构...', 'INFO')
    if not FRONTEND_DIR.exists():
        errors.append(f'前端目录不存在: {FRONTEND_DIR}')
    if not BACKEND_DIR.exists():
        errors.append(f'后端目录不存在: {BACKEND_DIR}')
    if not DOCKER_DIR.exists():
        errors.append(f'Docker 配置目录不存在: {DOCKER_DIR}')
    if not (PROJECT_ROOT / 'Dockerfile').exists():
        errors.append('Dockerfile 不存在')

    log(f'  ✓ 项目结构完整', 'SUCCESS')

    if errors:
        log('环境检查失败:', 'ERROR')
        for err in errors:
            log(f'  ❌ {err}', 'ERROR')
        sys.exit(1)

    log('✅ 环境检查通过', 'SUCCESS')
    log('-' * 50, 'INFO')


# ============================================
# 阶段 1: 前端构建
# ============================================
def build_frontend(skip_frontend=False):
    if skip_frontend:
        if DIST_DIR.exists():
            log('跳过前端构建（--skip-frontend），使用现有 dist 目录', 'WARNING')
            size = sum(f.stat().st_size for f in DIST_DIR.rglob('*') if f.is_file()) / (1024 * 1024)
            log(f'  现有前端产物: {size:.1f} MB', 'INFO')
            return True
        else:
            log('错误: --skip-frontend 但 dist 目录不存在', 'ERROR')
            log('请先运行前端构建或移除 --skip-frontend 参数', 'ERROR')
            sys.exit(1)

    log('开始前端构建...', 'STEP')
    log('-' * 50, 'INFO')

    start_time = time.time()

    # 检查 Node.js 和 npm 可用性
    node_found = False
    npm_found = False
    try:
        run_command(['node', '--version'], capture=True)
        node_found = True
    except:
        pass

    if node_found:
        try:
            run_command(['npm', '--version'], capture=True)
            npm_found = True
        except:
            pass

    if not npm_found:
        if node_found:
            log('⚠ npm 不可用，将依赖 Docker 多阶段构建前端', 'WARNING')
        else:
            log('⚠ Node.js/npm 均不可用，将依赖 Docker 多阶段构建前端', 'WARNING')
        log('  提示: 确保 Docker 可正常访问 Docker Hub 以下载基础镜像', 'INFO')
        return False

    # 安装依赖
    log('  安装前端依赖...', 'INFO')
    try:
        run_command(['npm', 'install'], cwd=FRONTEND_DIR)
    except:
        log('npm install 失败', 'ERROR')
        return False

    # 构建前端
    log('  编译前端代码...', 'INFO')
    try:
        run_command(['npm', 'run', 'build'], cwd=FRONTEND_DIR)
    except:
        log('前端编译失败', 'ERROR')
        return False

    # 验证构建产物
    if not DIST_DIR.exists():
        log('错误: 前端构建完成后 dist 目录不存在', 'ERROR')
        sys.exit(1)

    size = sum(f.stat().st_size for f in DIST_DIR.rglob('*') if f.is_file()) / (1024 * 1024)
    duration = time.time() - start_time
    log(f'✅ 前端构建完成 ({duration:.1f}s, {size:.1f} MB)', 'SUCCESS')
    log('-' * 50, 'INFO')
    return True


# ============================================
# 阶段 2: Docker 镜像构建
# ============================================
def build_docker_image(no_cache=False, tag=None, push=False):
    log('构建 Docker 镜像...', 'STEP')
    log('-' * 50, 'INFO')

    # 确定镜像标签
    image_tag = tag or DEFAULT_TAG
    image_full = f'{DEFAULT_IMAGE_NAME}:{image_tag}'

    start_time = time.time()

    # 构建命令
    cmd = ['docker', 'buildx', 'build']

    if no_cache:
        cmd.append('--no-cache')
        log('  使用 --no-cache 模式（将重新构建所有层）', 'WARNING')

    # 添加标签
    cmd.extend(['-t', image_full])

    # 添加构建参数
    cmd.extend([
        '--build-arg', f'BUILD_DATE={datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}',
        '--build-arg', f'BUILD_VERSION={image_tag}',
    ])

    # 加载到本地 Docker 镜像仓库
    cmd.append('--load')

    # 构建上下文
    cmd.append('.')

    log(f'  镜像名称: {image_full}', 'INFO')
    log(f'  构建上下文: {PROJECT_ROOT}', 'INFO')
    log('  开始构建（这可能需要 5-15 分钟）...', 'INFO')
    log('', 'INFO')

    try:
        run_command(cmd, cwd=PROJECT_ROOT, timeout=1800)
    except SystemExit:
        log('Docker 镜像构建失败', 'ERROR')
        log('可能的原因:', 'INFO')
        log('  • Docker 守护进程未运行', 'INFO')
        log('  • 镜像加速器不可用（检测到阿里云等加速器可能出现 403）', 'INFO')
        log('  • 网络连接问题导致无法访问 Docker Hub', 'INFO')
        log('  • 磁盘空间不足', 'INFO')
        log('', 'INFO')
        log('解决方案:', 'INFO')
        log('  1. 检查 Docker Desktop 是否正常运行', 'INFO')
        log('  2. 在 Docker Desktop → Settings → Docker Engine 中', 'INFO')
        log('     移除 registry-mirrors 配置或更换可用镜像源', 'INFO')
        log('  3. 确保可以访问 https://hub.docker.com', 'INFO')
        log('', 'INFO')
        log('使用 --no-cache 参数重试:', 'INFO')
        log(f'  python build_docker.py --no-cache', 'INFO')
        sys.exit(1)

    duration = time.time() - start_time
    log(f'✅ Docker 镜像构建完成 ({duration:.1f}s)', 'SUCCESS')
    log('-' * 50, 'INFO')

    # 推送到镜像仓库
    if push:
        push_image(image_full)

    return image_full


# ============================================
# 阶段 3: 构建验证
# ============================================
def verify_build(image_full):
    log('验证镜像构建...', 'STEP')
    log('-' * 50, 'INFO')

    errors = []

    # 1. 检查镜像是否存在
    log('  检查镜像是否存在...', 'INFO')
    try:
        result = run_command(['docker', 'images', image_full, '--format', '{{.Repository}}:{{.Tag}}'], capture=True)
        if image_full in result.stdout.strip():
            log(f'  ✓ 镜像存在: {image_full}', 'SUCCESS')
        else:
            errors.append(f'镜像 {image_full} 不存在')
    except:
        errors.append('无法检查镜像列表')

    # 2. 获取镜像大小
    log('  获取镜像大小...', 'INFO')
    try:
        result = run_command(['docker', 'images', image_full, '--format', '{{.Size}}'], capture=True)
        size = result.stdout.strip()
        log(f'  ✓ 镜像大小: {size}', 'SUCCESS')
    except:
        log(f'  ⚠ 无法获取镜像大小', 'WARNING')

    # 3. 检查镜像层数（摘要）
    log('  检查镜像摘要...', 'INFO')
    try:
        result = run_command(['docker', 'images', '--digests', image_full, '--format', '{{.Digest}}'], capture=True)
        digest = result.stdout.strip()
        if digest:
            log(f'  ✓ 镜像摘要: {digest[:40]}...', 'SUCCESS')
        else:
            log(f'  ⚠ 无法获取镜像摘要', 'WARNING')
    except:
        log(f'  ⚠ 无法获取镜像摘要', 'WARNING')

    # 4. 检查 Dockerfile 中的关键配置
    log('  检查 Dockerfile 配置...', 'INFO')
    dockerfile_path = PROJECT_ROOT / 'Dockerfile'
    if dockerfile_path.exists():
        content = dockerfile_path.read_text(encoding='utf-8')
        checks = [
            ('Redis 安装', 'redis-server' in content),
            ('Nginx 安装', 'nginx' in content),
            ('Supervisor 配置', 'supervisor' in content),
            ('健康检查', 'HEALTHCHECK' in content),
            ('多阶段构建', 'FROM' in content and 'AS ' in content),
            ('端口暴露', 'EXPOSE 80' in content),
            ('入口脚本', 'ENTRYPOINT' in content),
        ]
        for name, passed in checks:
            status = '✓' if passed else '✗'
            level = 'SUCCESS' if passed else 'ERROR'
            log(f'  {status} {name}', level)
            if not passed:
                errors.append(f'Dockerfile 缺少 {name} 配置')
    else:
        errors.append('Dockerfile 不存在')

    # 5. 验证关键配置文件
    log('  检查配置文件...', 'INFO')
    config_checks = [
        ('Nginx 配置', DOCKER_DIR / 'nginx' / 'nginx.conf'),
        ('Supervisor 配置', DOCKER_DIR / 'supervisor' / 'supervisord.conf'),
        ('Redis 配置', DOCKER_DIR / 'redis' / 'redis.conf'),
        ('入口脚本', DOCKER_DIR / 'entrypoint.sh'),
    ]
    for name, path in config_checks:
        if path.exists():
            log(f'  ✓ {name} 存在', 'SUCCESS')
        else:
            log(f'  ✗ {name} 不存在', 'ERROR')
            errors.append(f'缺少 {name}')

    # 6. 检查 Supervisor 配置中是否包含 Redis
    supervisor_conf = DOCKER_DIR / 'supervisor' / 'supervisord.conf'
    if supervisor_conf.exists():
        content = supervisor_conf.read_text(encoding='utf-8')
        if '[program:redis]' in content:
            log(f'  ✓ Supervisor 已配置 Redis 进程管理', 'SUCCESS')
        else:
            errors.append('Supervisor 未配置 Redis 进程管理')

    if errors:
        log('', 'ERROR')
        log('构建验证发现以下问题:', 'ERROR')
        for err in errors:
            log(f'  ❌ {err}', 'ERROR')
        log('', 'ERROR')
        log('请修复上述问题后重新构建', 'ERROR')
        return False

    log('✅ 镜像构建验证通过', 'SUCCESS')
    log('-' * 50, 'INFO')
    return True


# ============================================
# 阶段 4: 推送镜像
# ============================================
def push_image(image_full):
    log('推送镜像到仓库...', 'STEP')
    log('-' * 50, 'INFO')

    log(f'  推送: {image_full}', 'INFO')

    start_time = time.time()

    try:
        run_command(['docker', 'push', image_full])
    except:
        log('推送失败', 'ERROR')
        log('请检查: Docker 登录状态、镜像仓库地址', 'ERROR')
        sys.exit(1)

    duration = time.time() - start_time
    log(f'✅ 镜像推送完成 ({duration:.1f}s)', 'SUCCESS')


# ============================================
# 阶段 5: 启动容器
# ============================================
def run_container(image_full, env_file=None):
    log('启动容器...', 'STEP')
    log('-' * 50, 'INFO')

    # 检查端口占用
    log('  检查端口 80...', 'INFO')
    try:
        result = run_command(
            ['docker', 'ps', '--format', '{{.Names}}', '--filter', 'publish=80'],
            capture=True, check=False
        )
        if result.stdout.strip():
            log(f'  ⚠ 端口 80 已被以下容器占用:', 'WARNING')
            for line in result.stdout.strip().split('\n'):
                log(f'     - {line}', 'WARNING')
    except:
        pass

    # 创建 .env 文件（如果不存在）
    env_path = PROJECT_ROOT / '.env'
    if not env_path.exists():
        env_example = PROJECT_ROOT / '.env.example'
        if env_example.exists():
            shutil.copy2(env_example, env_path)
            log(f'  📝 已创建 .env 文件（从 .env.example）', 'INFO')
            log(f'  ⚠ 请编辑 .env 文件修改 SECRET_KEY 和 JWT_SECRET_KEY', 'WARNING')

    # 准备 docker-compose 命令
    compose_cmd = 'docker compose'
    try:
        run_command(['docker', 'compose', 'version'], capture=True)
    except:
        try:
            run_command(['docker-compose', '--version'], capture=True)
            compose_cmd = 'docker-compose'
        except:
            log('Docker Compose 未安装，使用 docker run 启动', 'WARNING')
            _run_container_direct(image_full)
            return

    log(f'  使用 {compose_cmd} 启动服务...', 'INFO')
    log(f'  配置文件: docker-compose.yml', 'INFO')

    try:
        run_command([compose_cmd, '-f', 'docker-compose.yml', 'up', '-d'], cwd=PROJECT_ROOT)
    except:
        log('启动容器失败', 'ERROR')
        sys.exit(1)

    log('✅ 容器已启动', 'SUCCESS')
    log('', 'INFO')
    log('访问地址: http://localhost', 'INFO')
    log('查看日志: docker compose logs -f', 'INFO')
    log('停止服务: docker compose down', 'INFO')


def _run_container_direct(image_full):
    """直接使用 docker run 启动（不依赖 compose）"""
    log('直接使用 docker run 启动...', 'INFO')

    cmd = [
        'docker', 'run', '-d',
        '--name', 'smarttable',
        '--restart', 'unless-stopped',
        '-p', '80:80',
        '-v', f'{PROJECT_ROOT}/logs:/app/logs',
        '-e', 'FLASK_ENV=production',
    ]

    # 添加 .env 文件（如果存在）
    env_path = PROJECT_ROOT / '.env'
    if env_path.exists():
        cmd.extend(['--env-file', str(env_path)])

    cmd.append(image_full)

    try:
        run_command(cmd, cwd=PROJECT_ROOT)
        log(f'  容器 ID: ...', 'INFO')
    except:
        log('直接启动容器失败', 'ERROR')
        sys.exit(1)


# ============================================
# 清理
# ============================================
def clean_build():
    log('清理构建产物...', 'STEP')

    # 清理前端构建产物
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        log(f'  已删除: {DIST_DIR.relative_to(PROJECT_ROOT)}', 'INFO')

    # 清理 Docker 缓存（可选）
    log('  提示: 使用 "docker system prune" 可以清理 Docker 缓存', 'INFO')

    log('✅ 清理完成', 'SUCCESS')


# ============================================
# Dockerfile 语法检查
# ============================================
def check_dockerfile():
    """检查 Dockerfile 的基本语法"""
    log('检查 Dockerfile 语法...', 'STEP')

    dockerfile_path = PROJECT_ROOT / 'Dockerfile'
    if not dockerfile_path.exists():
        log('❌ Dockerfile 不存在', 'ERROR')
        return False

    content = dockerfile_path.read_text(encoding='utf-8')
    lines = content.split('\n')

    issues = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith('#'):
            continue

        # 检查 FROM 指令
        if stripped.upper().startswith('FROM '):
            parts = stripped.split()
            if len(parts) < 2:
                issues.append(f'第 {i} 行: FROM 指令缺少镜像名称')

        # 检查 COPY 指令的源路径
        if stripped.upper().startswith('COPY '):
            parts = stripped.split()
            if len(parts) < 3:
                issues.append(f'第 {i} 行: COPY 指令缺少参数')

    if issues:
        log(f'发现 {len(issues)} 个问题:', 'WARNING')
        for issue in issues:
            log(f'  ⚠ {issue}', 'WARNING')
    else:
        log('✅ Dockerfile 语法检查通过', 'SUCCESS')

    return len(issues) == 0


# ============================================
# 主函数
# ============================================
def main():
    parser = argparse.ArgumentParser(
        description='SmartTable Docker 一键式构建工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python build_docker.py                    # 完整构建流程
  python build_docker.py --no-cache         # 不使用缓存构建
  python build_docker.py --skip-frontend    # 跳过前端构建
  python build_docker.py --tag v1.0.0       # 自定义标签
  python build_docker.py --run              # 构建并启动
  python build_docker.py --push             # 构建并推送
  python build_docker.py --check-only       # 仅检查环境
  python build_docker.py --clean            # 清理构建产物
        """
    )

    parser.add_argument('--no-cache', action='store_true',
                        help='不使用 Docker 缓存，重新构建所有层')
    parser.add_argument('--skip-frontend', action='store_true',
                        help='跳过前端构建，使用已有的 dist 目录')
    parser.add_argument('--tag', default=None,
                        help='指定镜像标签（默认: latest）')
    parser.add_argument('--push', action='store_true',
                        help='构建完成后推送到镜像仓库')
    parser.add_argument('--run', action='store_true',
                        help='构建完成后启动容器')
    parser.add_argument('--check-only', action='store_true',
                        help='仅检查环境，不构建')
    parser.add_argument('--clean', action='store_true',
                        help='清理构建产物后退出')
    parser.add_argument('--verify-only', action='store_true',
                        help='仅验证上次构建的镜像')

    args = parser.parse_args()

    # 显示 Banner
    print_banner()

    # 仅检查环境
    if args.check_only:
        check_prerequisites()
        log('环境检查完成，系统就绪', 'SUCCESS')
        return

    # 仅清理
    if args.clean:
        clean_build()
        return

    # 仅验证
    if args.verify_only:
        image_tag = args.tag or DEFAULT_TAG
        verify_build(f'{DEFAULT_IMAGE_NAME}:{image_tag}')
        return

    # ===== 完整构建流程 =====
    total_start = time.time()

    # 步骤 0: 环境检查
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 0/4: 检查运行环境', 'HEADER')
    log('=' * 60, 'HEADER')
    check_prerequisites()

    # 步骤 1: 检查 Dockerfile
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 1/4: 检查 Dockerfile', 'HEADER')
    log('=' * 60, 'HEADER')
    check_dockerfile()

    # 步骤 2: 构建前端
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 2/4: 构建前端', 'HEADER')
    log('=' * 60, 'HEADER')
    build_frontend(skip_frontend=args.skip_frontend)

    # 步骤 3: 构建 Docker 镜像
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 3/4: 构建 Docker 镜像', 'HEADER')
    log('=' * 60, 'HEADER')
    image_full = build_docker_image(no_cache=args.no_cache, tag=args.tag, push=args.push)

    # 步骤 4: 验证构建结果
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 4/4: 验证构建结果', 'HEADER')
    log('=' * 60, 'HEADER')
    verify_success = verify_build(image_full)

    if not verify_success:
        log('', 'ERROR')
        log('❌ 构建验证未通过，请检查上述问题', 'ERROR')
        sys.exit(1)

    total_duration = time.time() - total_start

    # ===== 构建完成 =====
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log(f'  🎉 SmartTable Docker 镜像构建成功！', 'HEADER')
    log('=' * 60, 'HEADER')
    log(f'  镜像名称: {image_full}', 'INFO')

    # 获取镜像大小
    try:
        result = run_command(['docker', 'images', image_full, '--format', '{{.Size}}'], capture=True)
        log(f'  镜像大小: {result.stdout.strip()}', 'INFO')
    except:
        pass

    log(f'  总耗时: {total_duration:.1f} 秒', 'INFO')
    log('', 'INFO')
    log('快速启动:', 'INFO')
    log(f'  docker compose up -d', 'INFO')
    log('', 'INFO')
    log('查看日志:', 'INFO')
    log(f'  docker compose logs -f', 'INFO')
    log('', 'INFO')
    log('停止服务:', 'INFO')
    log(f'  docker compose down', 'INFO')
    log('=' * 60, 'HEADER')

    # 可选：启动容器
    if args.run:
        log('', 'INFO')
        run_container(image_full)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log('', 'WARNING')
        log('构建被用户中断', 'WARNING')
        sys.exit(1)
    except Exception as e:
        log(f'构建异常: {e}', 'ERROR')
        import traceback
        traceback.print_exc()
        sys.exit(1)