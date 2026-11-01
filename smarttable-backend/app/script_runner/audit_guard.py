"""
脚本沙箱审计守卫（audit hook 深度防御层）

配合受限 builtins + 模块白名单使用：在 runner 进程内通过 sys.addaudithook
在 C 层拦截危险能力调用，阻断"逃逸回真实 builtins / importlib 之后调用
open、__import__、os.system、subprocess、socket、ctypes"等逃逸路径。
攻击者即使通过对象属性链（如 JSONDecoder.__init__.__globals__）取回真实
builtins，其后续能力调用也会被本守卫阻断。

接入方式（runner 顶部，注意顺序）：
    preload_allowed_modules(ALLOWED_MODULES)  # 必须在安装守卫之前
    install_audit_guard(ALLOWED_MODULES)

安全边界说明（深度防御，非完美沙箱）：
- audit hook 无法被纯 Python 移除/覆盖，覆盖 CPython 3.8+ 审计事件；
- 所有 os.* 能力事件（执行/进程/文件/权限/环境）默认阻断，仅放行 os.urandom；
- 子进程环境变量必须使用 build_sandbox_env() 白名单化，避免脚本读取宿主密钥；
- 个别无审计事件的原语（如读取已加载模块对象的 os.environ）无法拦截，
  因此环境变量白名单是必要防线；生产环境仍应以低权限 OS 用户运行 runner 子进程。
"""
import os
import sys
import traceback
from typing import Dict, Optional


class SandboxViolation(RuntimeError):
    """沙箱安全策略拦截异常：抛出即代表底层操作已被阻止"""


# 完全阻断的能力型审计事件（精确名称，避免误伤白名单功能）
_BLOCKED_EVENTS = frozenset({
    'open',                          # 任何 open() 调用（含逃逸后真实 builtins 的 open）
    'os.system',                     # 系统命令执行
    'os.fork', 'os.forkpty',         # 子进程（POSIX）
    'os.posix_spawn',                # 子进程（POSIX/Windows）
    'os.putenv', 'os.unsetenv',      # 进程环境变量篡改
    'pickle.find_class',             # 反序列化逃逸
    'marshal.loads',                 # 反序列化逃逸
    'builtins.input',                # 读取 stdin（挂进程 / 干扰 stdio 协议）
    'builtins.breakpoint',
})

# 完全阻断的事件前缀
_BLOCKED_PREFIXES = (
    'subprocess.',                   # Popen / exec / fork_exec
    'socket.',                       # connect / getaddrinfo / bind / sendto
    'ctypes.',                       # dlopen / dlsym / call_function
    'winreg.',                       # Windows 注册表
    'webbrowser.',                   # 打开外部浏览器
)

# 允许白名单模块依赖的无害 os.* 事件（如 uuid.uuid4 → os.urandom）
_OS_ALLOWED_EVENTS = frozenset({
    'os.urandom',
})

# 脚本子进程允许继承的环境变量：仅运行必需项，不含任何密钥/连接串
SAFE_ENV_KEYS = frozenset({
    'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR',
    'HOME', 'USERPROFILE', 'LANG', 'LC_ALL', 'LC_CTYPE',
    'PYTHONHOME', 'PYTHONPATH', 'PYTHONIOENCODING', 'PYTHONUTF8', 'PYTHONHASHSEED',
})


def build_sandbox_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """构建脚本子进程的最小环境变量集合。

    只保留运行必需的非敏感变量，避免脚本经属性链访问 os.environ 时
    拿到 SECRET_KEY / JWT_SECRET_KEY / DATABASE_URL / SMTP 密码等宿主密钥。
    """
    source = os.environ if base_env is None else base_env
    env = {
        key: value for key, value in source.items()
        if key.upper() in SAFE_ENV_KEYS
    }
    # 强制 UTF-8，避免中文 Windows 下本地编码破坏 stdio 协议
    env['PYTHONIOENCODING'] = 'utf-8'
    env.setdefault('PYTHONUTF8', '1')
    return env


def safe_format_exc(exc: Optional[BaseException] = None) -> str:
    """格式化异常栈，全程不读取源码文件，避免被 open 守卫拦截。

    标准 traceback 会经 linecache 打开白名单模块的 .py 源文件，触发 'open'
    审计事件导致异常处理本身再次抛错、runner 无法输出协议帧。此处直接遍历
    traceback 帧对象拼装文件/行号/函数名，并只格式化异常本身。
    """
    exc = exc or sys.exc_info()[1]
    if exc is None:
        return ''
    try:
        lines = ['Traceback (most recent call last):']
        tb = exc.__traceback__
        while tb is not None:
            code = tb.tb_frame.f_code
            lines.append(
                f'  File "{code.co_filename}", line {tb.tb_lineno}, in {code.co_name}')
            tb = tb.tb_next
        lines.append(''.join(traceback.format_exception_only(type(exc), exc)).rstrip())
        return '\n'.join(lines)
    except Exception:
        return f'{type(exc).__name__}: {exc}'


def preload_allowed_modules(modules):
    """预载白名单模块，其传递依赖的子导入发生在审计守卫生效前。

    必须在 install_audit_guard 之前调用：若由用户代码首次触发 import，
    模块内部依赖链的子导入（如 re → enum、uuid → os）会被守卫按
    "非白名单导入"误拦。
    """
    import importlib
    for name in sorted(set(modules)):
        try:
            importlib.import_module(name)
        except Exception:
            # 预载失败不阻断启动：用户运行时导入将走 safe_import 的原有错误路径
            pass


def install_audit_guard(allowed_modules, allowed_compiles=1):
    """安装审计守卫，返回 None。

    Args:
        allowed_modules: 允许导入的模块名集合（root 名匹配）
        allowed_compiles: 允许的 compile() 次数（供 runner 主执行使用，
            其余编译一律阻断，阻断 exec(字符串) 逃逸）
    """
    allowed_roots = {m.split('.')[0] for m in allowed_modules}
    state = {'compiles_left': int(allowed_compiles)}

    def _audit_guard(event, args):
        # 1) 导入事件：白名单放行，其余阻断。
        #    import 语句即使命中 sys.modules 缓存也会触发本事件；
        #    importlib.import_module 路径触发 'import' 事件，两者一并覆盖。
        if event in ('builtins.__import__', 'import'):
            module = args[0] if args else ''
            root = module.split('.')[0] if isinstance(module, str) else ''
            if root in allowed_roots:
                return
            raise SandboxViolation(
                f"模块 '{module}' 被沙箱安全策略禁止导入，仅允许: {sorted(allowed_roots)}")

        # 2) compile：一次性放行 runner 主执行，其余阻断
        #    （exec("...") 内部隐式 compile，可一并覆盖）
        if event == 'compile':
            if state['compiles_left'] > 0:
                state['compiles_left'] -= 1
                return
            raise SandboxViolation('动态编译代码 (compile/exec 字符串) 被沙箱安全策略禁止')

        # 3) 白名单功能依赖的无害 os.* 事件放行
        if event in _OS_ALLOWED_EVENTS:
            return

        # 4) 阻断所有其余 os.* 事件：命令执行（os.exec/os.spawn）、进程、
        #    文件系统（chdir/listdir/remove/rename 等）、权限与环境变量篡改
        if event.startswith('os.'):
            raise SandboxViolation(f'操作系统操作被沙箱安全策略禁止: {event}')

        # 5) 其他能力型事件全阻断
        if event in _BLOCKED_EVENTS or event.startswith(_BLOCKED_PREFIXES):
            raise SandboxViolation(f'操作被沙箱安全策略禁止: {event}')

    sys.addaudithook(_audit_guard)
