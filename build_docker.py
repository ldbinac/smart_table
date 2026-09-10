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
    python build_docker.py --image smarttable # 指定镜像名称
    python build_docker.py --platform linux/amd64,linux/arm64 # 指定平台
    python build_docker.py --registry xxx.cn-heyuan.personal.cr.aliyuncs.com/smart-table # 指定镜像仓库

快速构建指定仓库的多平台架构（linux/amd64,linux/arm64）：
    python build_docker.py --tag 1.6.6 --tag latest --registry xxx.cn-heyuan.personal.cr.aliyuncs.com/smart-table --image smarttable
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
DEFAULT_IMAGE_NAME = "ygbinac/smarttable"
DEFAULT_TAG = "latest"
DEFAULT_PLATFORMS = "linux/amd64,linux/arm64"
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
        log('  检查 pnpm...', 'INFO')
        try:
            result = run_command(['pnpm', '--version'], capture=True)
            log(f'  ✓ pnpm: {result.stdout.strip()}', 'SUCCESS')
            npm_found = True
        except:
            log(f'  ⚠ pnpm 未安装（Node.js 已安装但缺少 pnpm）', 'WARNING')
            log(f'    前端构建将依赖于 Docker 多阶段构建', 'INFO')
    else:
        log(f'  ⚠ pnpm 未安装（Node.js 不可用）', 'INFO')

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
        run_command(['pnpm', 'install'], cwd=FRONTEND_DIR)
    except:
        log('pnpm install 失败', 'ERROR')
        return False

    # 构建前端
    log('  编译前端代码...', 'INFO')
    try:
        run_command(['pnpm', 'run', 'build'], cwd=FRONTEND_DIR)
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
def ensure_buildx_builder(multi_platform=False):
    """
    确保存在一个可用于多平台构建的 buildx builder。
    多平台构建需要 docker-container 驱动 (default/desktop-linux 的 docker 驱动不支持)。
    优先复用名为 'multiarch' 的 builder, 否则自动创建。
    返回 builder 名称 (多平台时) 或 None (单平台使用默认驱动)。
    """
    if not multi_platform:
        return None

    builder_name = "multiarch"
    try:
        result = run_command(
            ['docker', 'buildx', 'ls'],
            capture=True, check=False
        )
        out = result.stdout
        if builder_name in out:
            # 通过 inspect 精确获取驱动类型
            # (buildx ls 输出中 DRIVER 与 NAME 同行, 逐行解析易误判导致误删;
            #  部分版本 buildx inspect 不支持 --format, 直接解析 Driver: 行)
            try:
                insp = run_command(
                    ['docker', 'buildx', 'inspect', builder_name],
                    capture=True, check=False
                )
                driver = ''
                for line in (insp.stdout or '').splitlines():
                    if line.strip().startswith('Driver:'):
                        driver = line.split(':', 1)[1].strip()
                        break
                if driver == 'docker-container':
                    log(f'  复用多平台 builder: {builder_name}', 'INFO')
                    run_command(['docker', 'buildx', 'use', builder_name], check=False)
                    return builder_name
            except Exception:
                pass
            # 存在但驱动不对则删除重建
            log(f'  builder {builder_name} 驱动不支持多平台，将重建', 'WARNING')
            run_command(['docker', 'buildx', 'rm', builder_name], check=False)
        # 创建新的 docker-container 驱动 builder
        # 通过 host.docker.internal 复用宿主的 HTTP 代理 (如 Clash 7890),
        # 解决 Windows Docker Desktop 下 buildx 容器直连 Docker Hub 不稳的问题。
        proxy_url = os.environ.get('BUILDX_PROXY', 'http://host.docker.internal:7890')
        log(f'  创建多平台 builder: {builder_name}', 'INFO')
        cmd_create = [
            'docker', 'buildx', 'create', '--name', builder_name,
            '--driver', 'docker-container', '--use',
            '--driver-opt', f'env.HTTP_PROXY={proxy_url}',
            '--driver-opt', f'env.HTTPS_PROXY={proxy_url}',
            '--driver-opt', 'env.NO_PROXY=',
        ]
        # 挂载国内可用的 Docker Hub 镜像代理配置 (docker/buildkitd.toml),
        # 使 buildkitd 无需直连 auth.docker.io / registry-1.docker.io
        buildkitd_config = DOCKER_DIR / 'buildkitd.toml'
        if buildkitd_config.exists():
            cmd_create += ['--buildkitd-config', str(buildkitd_config)]
        run_command(cmd_create, check=False)
        run_command(['docker', 'buildx', 'inspect', '--bootstrap'], check=False)
        return builder_name
    except Exception as e:
        log(f'  ⚠ 无法准备多平台 builder: {e}', 'WARNING')
        return None


def build_docker_image(no_cache=False, image=None, tags=None, push=False,
                        platforms=None):
    log('构建 Docker 镜像...', 'STEP')
    log('-' * 50, 'INFO')

    # 确定镜像名与标签
    image_name = image or DEFAULT_IMAGE_NAME
    tag_list = tags if tags else [DEFAULT_TAG]
    if not tags and not image:
        tag_list = [DEFAULT_TAG]
    # 规范化: 若用户只给了 image 没给 tag, 仍使用 latest
    if not tags:
        tag_list = [DEFAULT_TAG]
    full_tags = [f'{image_name}:{t}' for t in tag_list]

    # 多平台检测: --load 不支持多平台, 必须 --push
    plat_list = [p.strip() for p in (platforms or DEFAULT_PLATFORMS).split(',') if p.strip()]
    multi_platform = len(plat_list) > 1
    if multi_platform:
        push = True  # 多平台构建无法 --load 到本地, 强制推送
        log(f'  检测到多平台构建 ({", ".join(plat_list)})，自动启用 --push 模式', 'WARNING')

    # 多平台需使用支持跨架构的 buildx builder (docker-container 驱动)
    builder = ensure_buildx_builder(multi_platform)

    start_time = time.time()

    # 构建命令
    cmd = ['docker', 'buildx', 'build']
    if builder:
        cmd.extend(['--builder', builder])

    if no_cache:
        cmd.append('--no-cache')
        log('  使用 --no-cache 模式（将重新构建所有层）', 'WARNING')

    # 添加标签 (支持多标签, 用于 latest + 版本号)
    for t in full_tags:
        cmd.extend(['-t', t])

    # 目标平台
    if plat_list:
        cmd.extend(['--platform', ','.join(plat_list)])

    # 关闭 provenance attestation：阿里云 ACR 等仓库不支持 OCI attestation manifest
    # (推送时报 "unknown manifest class for application/vnd.oci.empty.v1+json")
    cmd.append('--provenance=false')

    # 添加构建参数
    cmd.extend([
        '--build-arg', f'BUILD_DATE={datetime.now().strftime("%Y-%m-%d_%H:%M:%S")}',
        '--build-arg', f'BUILD_VERSION={tag_list[0]}',
    ])

    # 多平台必须 --push; 单平台可 --load 到本地
    if push:
        cmd.append('--push')
    else:
        cmd.append('--load')

    # 构建上下文
    cmd.append('.')

    log(f'  镜像名称: {", ".join(full_tags)}', 'INFO')
    log(f'  目标平台: {", ".join(plat_list)}', 'INFO')
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

    # 推送到镜像仓库 (仅在单独 --push 且单平台时使用; 多平台已在构建时 --push)
    if push and not multi_platform:
        push_image(full_tags)

    return full_tags


# ============================================
# 阶段 3: 构建验证
# ============================================
def verify_build(image_full_list, platforms=None):
    log('验证镜像构建...', 'STEP')
    log('-' * 50, 'INFO')

    errors = []
    image_full_list = image_full_list if isinstance(image_full_list, list) else [image_full_list]

    # 多平台镜像通过 buildx imagetools 检查 manifest (本地 docker images 查不到)
    plat_list = [p.strip() for p in (platforms or DEFAULT_PLATFORMS).split(',') if p.strip()]
    multi_platform = len(plat_list) > 1

    for image_full in image_full_list:
        if multi_platform:
            # 1. 检查远程 manifest (含多平台)
            log(f'  检查多平台 manifest: {image_full}', 'INFO')
            try:
                result = run_command(
                    ['docker', 'buildx', 'imagetools', 'inspect', image_full],
                    capture=True, check=True
                )
                out = result.stdout
                # 校验每个目标平台都在 manifest 中
                missing = []
                for p in plat_list:
                    # imagetools inspect 输出含 "linux/amd64" / "linux/arm64"
                    if p not in out:
                        missing.append(p)
                if not missing:
                    log(f'  ✓ 多平台 manifest 完整: {", ".join(plat_list)}', 'SUCCESS')
                else:
                    errors.append(f'{image_full} 缺少平台: {", ".join(missing)}')
                # 显示摘要信息
                for line in out.splitlines():
                    if 'Digest:' in line or 'Name:' in line or 'Platform:' in line:
                        log(f'    {line.strip()}', 'INFO')
            except SystemExit:
                errors.append(f'无法获取远程 manifest: {image_full}')
            except Exception:
                errors.append(f'无法获取远程 manifest: {image_full}')
        else:
            # 1. 检查镜像是否存在（本地）
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
def push_image(image_full_list):
    log('推送镜像到仓库...', 'STEP')
    log('-' * 50, 'INFO')

    image_full_list = image_full_list if isinstance(image_full_list, list) else [image_full_list]
    start_time = time.time()

    for image_full in image_full_list:
        log(f'  推送: {image_full}', 'INFO')
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
    parser.add_argument('--image', default=DEFAULT_IMAGE_NAME,
                        help=f'镜像名 (默认: {DEFAULT_IMAGE_NAME})')
    parser.add_argument('--tag', action='append', default=None,
                        help='镜像标签，可重复指定；默认: latest')
    parser.add_argument('--registry', default='',
                        help='镜像仓库前缀, 例如 registry.example.com/ (默认: 空)')
    parser.add_argument('--platform', default=DEFAULT_PLATFORMS,
                        help=f'目标平台列表, 逗号分隔 (默认: {DEFAULT_PLATFORMS}). '
                             '多平台构建自动采用 --push 模式.')
    parser.add_argument('--push', action='store_true', default=None,
                        help='构建后推送到远程仓库 (多平台构建默认开启)')
    parser.add_argument('--run', action='store_true',
                        help='构建完成后启动容器 (仅单平台本地构建可用)')
    parser.add_argument('--check-only', action='store_true',
                        help='仅检查环境，不构建')
    parser.add_argument('--clean', action='store_true',
                        help='清理构建产物后退出')
    parser.add_argument('--verify-only', action='store_true',
                        help='仅验证已推送的镜像')

    args = parser.parse_args()

    # 显示 Banner
    print_banner()

    # 解析镜像名 (应用 registry 前缀)
    image_name = args.image
    if args.registry:
        image_name = f'{args.registry.rstrip("/")}/{image_name}'

    # 解析标签列表
    tag_list = args.tag if args.tag else [DEFAULT_TAG]

    # 多平台构建 => 默认推送
    plat_list = [p.strip() for p in args.platform.split(',') if p.strip()]
    multi_platform = len(plat_list) > 1
    push = True if args.push is None else args.push
    if multi_platform:
        push = True

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
        full_tags = [f'{image_name}:{t}' for t in tag_list]
        verify_build(full_tags, platforms=args.platform)
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
    full_tags = build_docker_image(
        no_cache=args.no_cache,
        image=image_name,
        tags=tag_list,
        push=push,
        platforms=args.platform,
    )

    # 步骤 4: 验证构建结果
    log('', 'INFO')
    log('=' * 60, 'HEADER')
    log('步骤 4/4: 验证构建结果', 'HEADER')
    log('=' * 60, 'HEADER')
    verify_success = verify_build(full_tags, platforms=args.platform)

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
    log(f'  镜像名称: {", ".join(full_tags)}', 'INFO')
    log(f'  目标平台: {", ".join(plat_list)}', 'INFO')
    log(f'  推送状态: {"已推送" if push else "未推送 (本地)"}', 'INFO')

    if not push:
        # 获取本地镜像大小
        try:
            result = run_command(['docker', 'images', full_tags[0], '--format', '{{.Size}}'], capture=True)
            log(f'  镜像大小: {result.stdout.strip()}', 'INFO')
        except:
            pass

    log(f'  总耗时: {total_duration:.1f} 秒', 'INFO')
    log('', 'INFO')
    if not multi_platform:
        log('快速启动:', 'INFO')
        log(f'  docker compose up -d', 'INFO')
        log('', 'INFO')
        log('查看日志:', 'INFO')
        log(f'  docker compose logs -f', 'INFO')
        log('', 'INFO')
        log('停止服务:', 'INFO')
        log(f'  docker compose down', 'INFO')
    log('=' * 60, 'HEADER')

    # 可选：启动容器 (多平台构建不自动启动, 因为本地无单架构镜像)
    if args.run and not multi_platform:
        log('', 'INFO')
        run_container(full_tags[0])


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