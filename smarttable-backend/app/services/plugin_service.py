"""
插件服务模块
负责安装包（.stplugin.zip）解包校验、manifest 清单校验、semver/宿主版本兼容检查、
生命周期状态机（安装/升级/回滚/启停/卸载）与两层 RBAC 辅助。

安全要点：
- zip 路径穿越防护（绝对路径 / .. / 盘符前缀）
- zip bomb 防护（解压总大小 / 文件数上限）
- manifest jsonschema 校验（入口存在、semver、engines 兼容、apiVersion 协商）
"""
import hashlib
import io
import json
import logging
import os
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.extensions import db
from app.models.plugin import (
    Plugin, PluginVersion, PluginConfig, PluginInstallation,
    PluginType, PluginStatus, PluginConfigScope,
)

log = logging.getLogger(__name__)

# ---- 安装包限制常量 ----
MAX_PACKAGE_SIZE = 50 * 1024 * 1024      # zip 解压总大小上限 50MB
MAX_FILE_COUNT = 500                      # 包内文件数上限
MAX_ENTRY_RATIO = 200                     # 单文件压缩率上限（解压/压缩），防 zip bomb
MAX_ICON_SIZE = 64 * 1024                 # 图标 ≤ 64KB
PLUGIN_STORAGE_ROOT_NAME = 'plugins'      # uploads/ 下插件包根目录

# ---- 宿主插件 API 版本 ----
SUPPORTED_API_VERSIONS = {'1'}

# ---- 错误码（与前端/文档协议保持一致）----
ERR_INVALID_PACKAGE = 'INVALID_PACKAGE'
ERR_MANIFEST_INVALID = 'MANIFEST_INVALID'
ERR_ENTRY_MISSING = 'ENTRY_MISSING'
ERR_VERSION_INVALID = 'VERSION_INVALID'
ERR_ENGINES_INCOMPATIBLE = 'ENGINES_INCOMPATIBLE'
ERR_API_VERSION_MISMATCH = 'API_VERSION_MISMATCH'
ERR_DOWNGRADE_FORBIDDEN = 'DOWNGRADE_FORBIDDEN'
ERR_CONFIG_INCOMPATIBLE = 'CONFIG_INCOMPATIBLE'
ERR_PLUGIN_EXISTS_VERSION = 'VERSION_EXISTS'
# installations 仅对 UI 插件有功能语义（Base 分发挂载）；脚本插件运行不依赖 Base 安装
ERR_PLUGIN_TYPE_NOT_INSTALLABLE = 'PLUGIN_TYPE_NOT_INSTALLABLE'

# 连续失败 N 次自动置 error
AUTO_ERROR_FAILURE_THRESHOLD = 5

# 宿主版本缓存
_host_version_cache: Optional[str] = None


# ==================== semver 轻量实现（约 60 行，避免新依赖） ====================

_SEMVER_RE = re.compile(
    r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    r'(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
    r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
    r'(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
)


def parse_semver(version: str) -> Optional[Tuple[int, int, int]]:
    """解析 semver 字符串为 (major, minor, patch)，非法返回 None"""
    if not isinstance(version, str):
        return None
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def semver_gt(a: str, b: str) -> bool:
    """a 是否严格大于 b（仅比较 major.minor.patch，忽略预发布/构建元数据）"""
    pa, pb = parse_semver(a), parse_semver(b)
    if pa is None or pb is None:
        return False
    return pa > pb


def _split_range(range_text: str) -> List[str]:
    """将 '>=1.7.0 <2.0.0' 拆为比较子句列表"""
    return [p for p in re.split(r'\s+', range_text.strip()) if p]


def satisfies_range(version: str, range_text: str) -> bool:
    """检查 semver 是否满足简单范围表达式（支持 > >= < <= = 与空=任意）"""
    v = parse_semver(version)
    if v is None:
        return False
    if not range_text or range_text.strip() in ('*', ''):
        return True
    for clause in _split_range(range_text):
        m = re.match(r'^(>=|<=|>|<|=|\^|~)?\s*(.+)$', clause)
        if not m:
            return False
        op, target = m.group(1) or '=', m.group(2)
        t = parse_semver(target)
        if t is None:
            return False
        if op == '>=' and not v >= t:
            return False
        if op == '<=' and not v <= t:
            return False
        if op == '>' and not v > t:
            return False
        if op == '<' and not v < t:
            return False
        if op == '=' and v != t:
            return False
        if op == '^':
            # ^1.2.3 := >=1.2.3 <2.0.0
            if not (t <= v < (t[0] + 1, 0, 0)):
                return False
        if op == '~':
            # ~1.2.3 := >=1.2.3 <1.3.0
            if not (t <= v < (t[0], t[1] + 1, 0)):
                return False
    return True


def get_host_version() -> str:
    """读取宿主版本（version.json），带缓存"""
    global _host_version_cache
    if _host_version_cache is None:
        try:
            # version.json 位于仓库根目录（smarttable-backend 的上一级）
            candidates = [
                Path(current_app.root_path).parent.parent / 'version.json',
                Path(current_app.root_path).parent / 'version.json',
            ]
            for c in candidates:
                if c.exists():
                    with open(c, 'r', encoding='utf-8') as f:
                        _host_version_cache = json.load(f).get('version', '0.0.0')
                    break
            else:
                _host_version_cache = '0.0.0'
        except Exception:
            log.exception('[PluginService] 读取宿主版本失败')
            _host_version_cache = '0.0.0'
    return _host_version_cache


# ==================== manifest 校验 ====================

_PLUGIN_ID_RE = re.compile(r'^[a-z0-9][a-z0-9.-]{2,199}$')

_VALID_PERMISSION_LEVELS = {'read', 'write'}
_VALID_EXTENSION_TYPES = {'toolbar-button', 'side-panel', 'base-menu', 'record-detail-block'}


def _validate_manifest(manifest: Dict[str, Any]) -> Tuple[bool, str, str]:
    """校验 manifest 结构

    Returns:
        (ok, error_code, error_detail)
    """
    try:
        import jsonschema
        from app.services.plugin_manifest_schema import MANIFEST_SCHEMA
        jsonschema.validate(instance=manifest, schema=MANIFEST_SCHEMA)
    except ImportError:
        # jsonschema 不可用时退化为关键字段手工校验
        for field in ('id', 'name', 'version', 'type', 'apiVersion', 'engines', 'entry', 'permissions'):
            if field not in manifest:
                return False, ERR_MANIFEST_INVALID, f'missing field: {field}'
    except Exception as e:
        return False, ERR_MANIFEST_INVALID, str(e)

    # id 格式（反向域名）
    if not _PLUGIN_ID_RE.match(manifest['id']):
        return False, ERR_MANIFEST_INVALID, 'id must be reverse-domain format (e.g. com.example.name)'

    # version 语义
    if parse_semver(manifest['version']) is None:
        return False, ERR_VERSION_INVALID, (
            f'version 字段 "{manifest.get("version", "")}" 不是合法的语义化版本号'
            f'（需为 x.y.z 形式，如 1.0.0）'
        )

    # type
    if manifest['type'] not in (PluginType.UI.value, PluginType.SCRIPT.value):
        return False, ERR_MANIFEST_INVALID, f'invalid type: {manifest["type"]}'

    # apiVersion 协商
    if str(manifest.get('apiVersion', '')) not in SUPPORTED_API_VERSIONS:
        return False, ERR_API_VERSION_MISMATCH, f'supported: {sorted(SUPPORTED_API_VERSIONS)}'

    # engines 兼容
    engines = manifest.get('engines') or {}
    smarttable_range = engines.get('smarttable', '*') if isinstance(engines, dict) else '*'
    host_ver = get_host_version()
    if not satisfies_range(host_ver, smarttable_range):
        # 提示同时给出中英文：宿主 i18n 仅支持静态 key 翻译，动态值无法插值
        return False, ERR_ENGINES_INCOMPATIBLE, (
            f'当前宿主版本 {host_ver} 不满足插件声明的引擎兼容范围 '
            f'engines.smarttable: "{smarttable_range}"'
            f'（请升级宿主版本，或放宽插件 manifest 的 engines 声明）'
            f' / Host version {host_ver} does not satisfy '
            f'engines.smarttable "{smarttable_range}"; upgrade the host '
            f'or relax the plugin engines range'
        )

    # entry 扩展名校验
    entry = manifest.get('entry', '')
    if manifest['type'] == PluginType.UI.value and not entry.endswith('.js'):
        return False, ERR_ENTRY_MISSING, f'ui plugin entry must be .js: {entry}'
    if manifest['type'] == PluginType.SCRIPT.value and not entry.endswith('.py'):
        return False, ERR_ENTRY_MISSING, f'script plugin entry must be .py: {entry}'

    # UI 插件需至少声明一个扩展点
    eps = manifest.get('extensionPoints') or []
    if manifest['type'] == PluginType.UI.value and not eps:
        return False, ERR_MANIFEST_INVALID, 'ui plugin requires at least one extensionPoint'
    for ep in eps:
        if ep.get('type') not in _VALID_EXTENSION_TYPES:
            return False, ERR_MANIFEST_INVALID, f'invalid extensionPoint type: {ep.get("type")}'

    # script.timeout 上限
    script_cfg = manifest.get('script') or {}
    timeout = script_cfg.get('timeout')
    if timeout is not None:
        try:
            t = int(timeout)
            if not (1 <= t <= 300):
                return False, ERR_MANIFEST_INVALID, 'script.timeout must be 1-300 seconds'
        except (TypeError, ValueError):
            return False, ERR_MANIFEST_INVALID, 'script.timeout must be an integer'

    return True, '', ''


# ==================== 安装包处理 ====================

def _backend_root() -> Path:
    """后端应用根目录（smarttable-backend/），与进程工作目录无关"""
    return Path(current_app.root_path).parent


def _plugin_storage_root() -> Path:
    # 相对 UPLOAD_FOLDER 锚定在后端根目录解析，避免受进程 CWD 影响
    # （CWD 随启动方式变化会导致读写位置漂移、静态文件 404）
    uploads_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads'))
    if not uploads_dir.is_absolute():
        uploads_dir = _backend_root() / uploads_dir
    root = uploads_dir / PLUGIN_STORAGE_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_package_path(package_path: str) -> Path:
    """解析插件版本目录路径

    兼容历史数据：DB 中可能存有相对路径（如 uploads/plugins/<id>/<ver>），
    按后端根目录锚定解析；绝对路径原样使用。
    """
    path = Path(package_path)
    if not path.is_absolute():
        path = _backend_root() / path
    return path


def _safe_extract(zip_file: zipfile.ZipFile, dest: Path) -> List[str]:
    """安全解压：路径穿越防护 + zip bomb 防护

    Returns:
        解压出的相对文件名列表

    Raises:
        ValueError: 校验失败（携带原因）
    """
    infos = zip_file.infolist()
    if len(infos) > MAX_FILE_COUNT:
        raise ValueError(f'package contains too many files: {len(infos)} > {MAX_FILE_COUNT}')

    total_size = 0
    extracted: List[str] = []
    dest_resolved = dest.resolve()

    for info in infos:
        name = info.filename

        # 统一分隔符并规范化
        normalized = name.replace('\\', '/')
        if normalized.startswith('/') or normalized.startswith('..'):
            raise ValueError(f'unsafe path entry: {name}')
        if re.match(r'^[A-Za-z]:', normalized):
            raise ValueError(f'unsafe path entry (drive letter): {name}')
        parts = [p for p in normalized.split('/') if p not in ('', '.')]
        if '..' in parts:
            raise ValueError(f'unsafe path entry (traversal): {name}')

        # zip bomb 检查
        total_size += info.file_size
        if total_size > MAX_PACKAGE_SIZE:
            raise ValueError(f'package extracted size exceeds {MAX_PACKAGE_SIZE // (1024 * 1024)}MB')
        if info.compress_size > 0 and info.file_size / info.compress_size > MAX_ENTRY_RATIO:
            raise ValueError(f'suspicious compression ratio: {name}')
        if info.file_size > MAX_PACKAGE_SIZE:
            raise ValueError(f'file too large: {name}')

        # 安全解压（逐条目）
        target = (dest_resolved / Path(*parts)).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise ValueError(f'path escapes destination: {name}')

        if info.is_dir() or normalized.endswith('/'):
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with zip_file.open(info) as src, open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        extracted.append('/'.join(parts))

    return extracted


def _read_manifest_from_zip(zip_bytes: bytes) -> Tuple[Dict[str, Any], bytes, str]:
    """从 zip 中读取 manifest.json

    Returns:
        (manifest, zip_bytes, checksum_sha256)

    Raises:
        ValueError: 包结构不合法
    """
    checksum = hashlib.sha256(zip_bytes).hexdigest()
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        raise ValueError(f'not a valid zip file: {e}')

    names = [n.replace('\\', '/') for n in zf.namelist()]
    manifest_names = [n for n in names if n in ('manifest.json', './manifest.json')]
    if not manifest_names:
        raise ValueError('manifest.json not found in package root')

    with zf.open(manifest_names[0]) as f:
        try:
            manifest = json.loads(f.read().decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError(f'manifest.json parse error: {e}')

    return manifest, zip_bytes, checksum


class PluginService:
    """插件生命周期服务"""

    # ---------- 安装/升级 ----------

    @classmethod
    def install_or_upgrade(cls, zip_bytes: bytes, operator_id: str) -> Dict[str, Any]:
        """上传安装/升级安装包

        - 新 plugin_id → 安装（状态 installed）
        - 已存在且版本更高 → 升级（保留 configs/installations，更新版本指针）
        - 已存在且版本相同 → 拒绝
        - 已存在且版本更低 → 拒绝（回滚走 rollback API）

        Returns:
            {action: 'installed'|'upgraded', plugin: {...}}

        Raises:
            PluginValidationError: 校验失败
        """
        try:
            manifest, _, checksum = _read_manifest_from_zip(zip_bytes)
        except ValueError as e:
            raise PluginValidationError(ERR_INVALID_PACKAGE, str(e))

        ok, code, detail = _validate_manifest(manifest)
        if not ok:
            raise PluginValidationError(code, detail)

        plugin_id = manifest['id']
        version = manifest['version']

        existing = db.session.get(Plugin, plugin_id)

        if existing is not None:
            if existing.current_version == version:
                raise PluginValidationError(
                    ERR_PLUGIN_EXISTS_VERSION,
                    f'{plugin_id} {version} already installed')
            if not semver_gt(version, existing.current_version):
                raise PluginValidationError(
                    ERR_DOWNGRADE_FORBIDDEN,
                    f'current={existing.current_version}, uploaded={version}; '
                    'use rollback API to switch to a lower version')

        # 解包到版本目录
        root = _plugin_storage_root() / plugin_id / version
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        try:
            extracted = _safe_extract(
                zipfile.ZipFile(io.BytesIO(zip_bytes)), root)
        except ValueError as e:
            shutil.rmtree(root, ignore_errors=True)
            raise PluginValidationError(ERR_INVALID_PACKAGE, str(e))

        # 入口文件存在校验（entry 相对于包根）
        entry = manifest['entry']
        if entry not in extracted and f'./{entry}' not in extracted:
            shutil.rmtree(root, ignore_errors=True)
            raise PluginValidationError(ERR_ENTRY_MISSING, entry)

        # configSchema 与存量配置兼容性检查（升级时）
        if existing is not None:
            incompatible = cls._check_config_compat(existing.id, manifest.get('configSchema'))
            if incompatible:
                shutil.rmtree(root, ignore_errors=True)
                raise PluginValidationError(
                    ERR_CONFIG_INCOMPATIBLE,
                    f'existing config incompatible with new configSchema: {incompatible}')

        action = 'installed'
        if existing is None:
            plugin = Plugin(
                id=plugin_id,
                name=manifest['name'],
                description=manifest.get('description'),
                icon=manifest.get('icon'),
                type=PluginType(manifest['type']),
                status=PluginStatus.INSTALLED,
                current_version=version,
                manifest=manifest,
                engines_text=(manifest.get('engines') or {}).get('smarttable'),
            )
            db.session.add(plugin)
        else:
            action = 'upgraded'
            existing.name = manifest['name']
            existing.description = manifest.get('description')
            existing.icon = manifest.get('icon')
            existing.manifest = manifest
            existing.current_version = version
            existing.engines_text = (manifest.get('engines') or {}).get('smarttable')
            # 升级后若处于 error 状态，恢复为 installed（需人工确认后启用）
            if existing.status == PluginStatus.ERROR:
                existing.status = PluginStatus.INSTALLED

        package_path = str(root)
        db.session.add(PluginVersion(
            plugin_id=plugin_id,
            version=version,
            package_path=package_path,
            checksum=checksum,
        ))
        db.session.commit()

        plugin = db.session.get(Plugin, plugin_id)
        log.info('[PluginService] 插件 %s：%s %s（操作者 %s）',
                 action, plugin_id, version, operator_id)
        return {'action': action, 'plugin': plugin.to_dict(include_versions=True)}

    @classmethod
    def _check_config_compat(cls, plugin_id: str,
                             config_schema: Optional[Dict]) -> Optional[List[str]]:
        """检查存量配置是否兼容新 configSchema，返回不兼容项列表（空=兼容）"""
        if not config_schema:
            return None
        try:
            import jsonschema
        except ImportError:
            return None
        configs = PluginConfig.query.filter_by(plugin_id=plugin_id).filter(
            PluginConfig.scope.in_([PluginConfigScope.GLOBAL, PluginConfigScope.BASE])
        ).all()
        incompatible = []
        for cfg in configs:
            try:
                jsonschema.validate(instance=cfg.config or {}, schema=config_schema)
            except Exception as e:
                incompatible.append(
                    f'{cfg.scope.value}:{cfg.base_id or "-"} ({e.message})')
        return incompatible or None

    # ---------- 回滚 ----------

    @classmethod
    def rollback(cls, plugin_id: str, target_version: str) -> Dict[str, Any]:
        """回滚到已保留的旧版本"""
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)

        ver = plugin.versions.filter_by(version=target_version).first()
        if ver is None:
            raise PluginValidationError(
                ERR_VERSION_INVALID,
                f'version {target_version} not retained for {plugin_id}; '
                'only previously installed versions can be rolled back')

        # 目录必须存在（相对路径按后端根目录锚定解析）
        if not resolve_package_path(ver.package_path).exists():
            raise PluginValidationError(ERR_INVALID_PACKAGE,
                                        f'package files missing: {ver.package_path}')

        plugin.current_version = target_version
        plugin.manifest = plugin.manifest  # 保留（回滚不回写清单，前端按版本目录加载）
        db.session.commit()
        log.info('[PluginService] 插件回滚 %s -> %s', plugin_id, target_version)
        return plugin.to_dict()

    # ---------- 全局启停/卸载 ----------

    @classmethod
    def set_status(cls, plugin_id: str, status: str) -> Dict[str, Any]:
        try:
            new_status = PluginStatus(status)
        except ValueError:
            raise PluginValidationError(ERR_MANIFEST_INVALID, f'invalid status: {status}')
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        # installed 仅在初始/升级后存在；API 层只允许 enabled/disabled/installed 转换
        plugin.status = new_status
        db.session.commit()
        return plugin.to_dict()

    @classmethod
    def uninstall(cls, plugin_id: str) -> bool:
        """卸载：删除全部记录（versions/configs/installations/run_logs）+ 包文件"""
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)

        package_root = _plugin_storage_root() / plugin_id
        db.session.delete(plugin)  # 级联删除 versions/configs/installations/run_logs
        db.session.commit()
        shutil.rmtree(package_root, ignore_errors=True)
        log.info('[PluginService] 插件卸载 %s（含全部数据与包文件）', plugin_id)
        return True

    # ---------- Base 级安装/启用 ----------

    @classmethod
    def install_to_base(cls, plugin_id: str, base_id: str, user_id: str) -> Dict[str, Any]:
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        if plugin.type != PluginType.UI:
            raise PluginValidationError(
                ERR_PLUGIN_TYPE_NOT_INSTALLABLE,
                '仅 UI 插件支持 Base 级安装（脚本插件运行由 RBAC 与全局启停控制，'
                '不依赖 Base 安装） / Only UI plugins support Base-level '
                'installation (script plugins are governed by RBAC and '
                'the global status)')
        existing = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id).first()
        if existing is None:
            existing = PluginInstallation(
                plugin_id=plugin_id, base_id=base_id,
                enabled=True, installed_by=user_id)
            db.session.add(existing)
        else:
            existing.enabled = True
        db.session.commit()
        return existing.to_dict()

    @classmethod
    def set_base_enabled(cls, plugin_id: str, base_id: str, enabled: bool) -> Dict[str, Any]:
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        if plugin.type != PluginType.UI:
            raise PluginValidationError(
                ERR_PLUGIN_TYPE_NOT_INSTALLABLE,
                '仅 UI 插件支持 Base 级安装（脚本插件运行由 RBAC 与全局启停控制，'
                '不依赖 Base 安装） / Only UI plugins support Base-level '
                'installation (script plugins are governed by RBAC and '
                'the global status)')
        inst = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id).first()
        if inst is None:
            raise PluginNotFoundError(f'installation {plugin_id}@{base_id}')
        inst.enabled = enabled
        db.session.commit()
        return inst.to_dict()

    @classmethod
    def uninstall_from_base(cls, plugin_id: str, base_id: str) -> bool:
        inst = PluginInstallation.query.filter_by(
            plugin_id=plugin_id, base_id=base_id).first()
        if inst is None:
            raise PluginNotFoundError(f'installation {plugin_id}@{base_id}')
        db.session.delete(inst)
        db.session.commit()
        return True

    # ---------- 配置 ----------

    @classmethod
    def get_effective_config(cls, plugin_id: str, base_id: Optional[str]) -> Dict[str, Any]:
        """读取生效配置：base 级深合并于 global 级之上"""
        merged: Dict[str, Any] = {}
        global_cfg = PluginConfig.query.filter_by(
            plugin_id=plugin_id, scope=PluginConfigScope.GLOBAL).first()
        if global_cfg:
            merged.update(global_cfg.config or {})
        if base_id:
            base_cfg = PluginConfig.query.filter_by(
                plugin_id=plugin_id, scope=PluginConfigScope.BASE, base_id=base_id).first()
            if base_cfg:
                merged.update(base_cfg.config or {})
        return merged

    @classmethod
    def get_scope_config(cls, plugin_id: str, scope: str,
                         base_id: Optional[str] = None) -> Dict[str, Any]:
        """读取指定作用域存储的配置（不做合并，供管理界面按页签展示）"""
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        try:
            cfg_scope = PluginConfigScope(scope)
        except ValueError:
            raise PluginValidationError(ERR_MANIFEST_INVALID, f'invalid scope: {scope}')
        row = PluginConfig.query.filter_by(
            plugin_id=plugin_id, scope=cfg_scope,
            base_id=base_id if cfg_scope == PluginConfigScope.BASE else None).first()
        return dict(row.config or {}) if row else {}

    @classmethod
    def set_config(cls, plugin_id: str, scope: str, base_id: Optional[str],
                   config: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        try:
            cfg_scope = PluginConfigScope(scope)
        except ValueError:
            raise PluginValidationError(ERR_MANIFEST_INVALID, f'invalid scope: {scope}')

        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)

        # configSchema 校验
        schema = (plugin.manifest or {}).get('configSchema')
        if schema:
            try:
                import jsonschema
                jsonschema.validate(instance=config, schema=schema)
            except ImportError:
                pass
            except Exception as e:
                raise PluginValidationError(ERR_CONFIG_INCOMPATIBLE, str(e.message if hasattr(e, 'message') else e))

        existing = PluginConfig.query.filter_by(
            plugin_id=plugin_id, scope=cfg_scope,
            base_id=base_id if cfg_scope == PluginConfigScope.BASE else None).first()
        if existing is None:
            existing = PluginConfig(
                plugin_id=plugin_id, scope=cfg_scope, base_id=base_id,
                config=config, updated_by=user_id)
            db.session.add(existing)
        else:
            existing.config = config
            existing.updated_by = user_id
        db.session.commit()
        return existing.to_dict()

    # ---------- 查询 ----------

    @classmethod
    def list_plugins(cls, base_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """插件列表；传入 base_id 时附带 Base 级安装/生效状态"""
        plugins = Plugin.query.order_by(Plugin.created_at.desc()).all()
        result = []
        for p in plugins:
            d = p.to_dict()
            if base_id:
                inst = p.installations.filter_by(base_id=base_id).first()
                d['baseInstalled'] = inst is not None
                # 原始 Base 级安装启用位（不含全局状态，供管理界面做启停切换）
                d['baseInstallEnabled'] = bool(inst and inst.enabled)
                d['baseEnabled'] = bool(inst and inst.enabled
                                        and p.status == PluginStatus.ENABLED)
            result.append(d)
        return result

    @classmethod
    def get_plugin(cls, plugin_id: str) -> Dict[str, Any]:
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        d = plugin.to_dict()
        d['versions'] = [v.to_dict() for v in
                         plugin.versions.order_by(PluginVersion.installed_at.desc()).all()]
        return d

    @classmethod
    def get_package_dir(cls, plugin_id: str, version: str) -> Path:
        """获取指定版本的包目录（供静态服务使用），与进程 CWD 无关"""
        plugin = db.session.get(Plugin, plugin_id)
        if plugin is None:
            raise PluginNotFoundError(plugin_id)
        ver = plugin.versions.filter_by(version=version).first()
        if ver is None:
            raise PluginNotFoundError(f'{plugin_id}@{version}')
        return resolve_package_path(ver.package_path)


# ==================== 异常定义 ====================

class PluginValidationError(Exception):
    """插件操作校验失败（error_code + detail）"""

    def __init__(self, error_code: str, detail: str = ''):
        super().__init__(f'{error_code}: {detail}')
        self.error_code = error_code
        self.detail = detail


class PluginNotFoundError(Exception):
    """插件资源不存在"""

    def __init__(self, target: str):
        super().__init__(f'plugin resource not found: {target}')
        self.target = target
