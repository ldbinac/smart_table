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
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.extensions import db
from app.models.plugin import (
    Plugin, PluginVersion, PluginConfig, PluginInstallation,
    PluginType, PluginStatus, PluginConfigScope,
)

def _validate_manifest(manifest: Dict[str, Any]) -> Tuple[bool, str, str, Dict[str, Any]]:
    """校验 manifest 结构

    Returns:
        (ok, error_code, error_detail_key, error_params)
        error_detail_key 为 i18n key（含 {占位符} 时由 error_params 插值），
        由路由层调用 translate() 渲染为当前语言文本。
    """
    try:
        import jsonschema
        from app.services.plugin_manifest_schema import MANIFEST_SCHEMA
        jsonschema.validate(instance=manifest, schema=MANIFEST_SCHEMA)
    except ImportError:
        # jsonschema 不可用时退化为关键字段手工校验
        for field in ('id', 'name', 'version', 'type', 'apiVersion', 'engines', 'entry', 'permissions'):
            if field not in manifest:
                return (False, ERR_MANIFEST_INVALID,
                        'plugin_manifest_missing_field', {'field': field})
    except Exception as e:
        return False, ERR_MANIFEST_INVALID, 'plugin_manifest_invalid', {'error': str(e)}

    # id 格式（反向域名）
    if not _PLUGIN_ID_RE.match(manifest['id']):
        return (False, ERR_MANIFEST_INVALID, 'plugin_invalid_id',
                {'id': str(manifest.get('id', ''))})

    # version 语义
    if parse_semver(manifest['version']) is None:
        return (False, ERR_VERSION_INVALID, 'plugin_version_invalid',
                {'version': str(manifest.get('version', ''))})

    # type
    if manifest['type'] not in (PluginType.UI.value, PluginType.SCRIPT.value):
        return (False, ERR_MANIFEST_INVALID, 'plugin_invalid_type',
                {'type': str(manifest.get('type', ''))})

    # apiVersion 协商
    if str(manifest.get('apiVersion', '')) not in SUPPORTED_API_VERSIONS:
        return (False, ERR_API_VERSION_MISMATCH, 'plugin_api_version_mismatch',
                {'supported': ', '.join(sorted(SUPPORTED_API_VERSIONS))})

    # engines 兼容
    engines = manifest.get('engines') or {}
    smarttable_range = engines.get('smarttable', '*') if isinstance(engines, dict) else '*'
    host_ver = get_host_version()
    if not satisfies_range(host_ver, smarttable_range):
        return (False, ERR_ENGINES_INCOMPATIBLE, 'plugin_engines_incompatible',
                {'host': host_ver, 'range': smarttable_range})

    # entry 扩展名校验
    entry = manifest.get('entry', '')
    if manifest['type'] == PluginType.UI.value and not entry.endswith('.js'):
        return False, ERR_ENTRY_MISSING, 'plugin_entry_must_be_js', {'entry': entry}
    if manifest['type'] == PluginType.SCRIPT.value and not entry.endswith('.py'):
        return False, ERR_ENTRY_MISSING, 'plugin_script_entry_must_be_py', {'entry': entry}

    # UI 插件需至少声明一个扩展点
    eps = manifest.get('extensionPoints') or []
    if manifest['type'] == PluginType.UI.value and not eps:
        return False, ERR_MANIFEST_INVALID, 'plugin_no_extension_points', {}
    for ep in eps:
        if ep.get('type') not in _VALID_EXTENSION_TYPES:
            return (False, ERR_MANIFEST_INVALID, 'plugin_invalid_extension_point',
                    {'type': str(ep.get('type'))})

    # script.timeout 上限
    script_cfg = manifest.get('script') or {}
    timeout = script_cfg.get('timeout')
    if timeout is not None:
        try:
            t = int(timeout)
            if not (1 <= t <= 300):
                return False, ERR_MANIFEST_INVALID, 'plugin_script_timeout_invalid', {}
        except (TypeError, ValueError):
            return False, ERR_MANIFEST_INVALID, 'plugin_script_timeout_invalid', {}

    # assets 资源扩展名校验（styles 仅 .css / scripts 仅 .js）
    assets = manifest.get('assets') or {}
    for css in (assets.get('styles') or []):
        if not isinstance(css, str) or not css.endswith('.css'):
            return (False, ERR_MANIFEST_INVALID, 'plugin_asset_style_must_be_css',
                    {'path': str(css)})
    for js in (assets.get('scripts') or []):
        if not isinstance(js, str) or not js.endswith('.js'):
            return (False, ERR_MANIFEST_INVALID, 'plugin_asset_script_must_be_js',
                    {'path': str(js)})

    # endpoints 校验（name 格式 / entry 仅 .py / timeout 范围）
    for ep in (manifest.get('endpoints') or []):
        ep_name = ep.get('name', '')
        if not re.match(r'^[a-z][a-z0-9-]*$', ep_name):
            return (False, ERR_MANIFEST_INVALID, 'plugin_invalid_endpoint_name',
                    {'name': ep_name})
        ep_entry = ep.get('entry', '')
        if not ep_entry.endswith('.py'):
            return (False, ERR_MANIFEST_INVALID, 'plugin_endpoint_entry_must_be_py',
                    {'entry': ep_entry})
        ep_timeout = ep.get('timeout')
        if ep_timeout is not None:
            try:
                t = int(ep_timeout)
                if not (1 <= t <= 300):
                    return False, ERR_MANIFEST_INVALID, 'plugin_endpoint_timeout_invalid', {}
            except (TypeError, ValueError):
                return False, ERR_MANIFEST_INVALID, 'plugin_endpoint_timeout_invalid', {}

    return True, '', '', {}

def _backend_root() -> Path:
    """数据锚定根目录，与进程工作目录无关。

    打包模式（PyInstaller）：sys._MEIPASS 是每次启动重新生成的临时解压目录
    （进程退出即删除、易被系统清理），插件数据必须锚定到 EXE 所在目录，
    与 config（data/logs）、attachment_service（uploads）的策略保持一致；
    开发模式：smarttable-backend 根目录。
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
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

class _PackageError(ValueError):
    """安装包结构/安全错误

    携带 i18n key 与插值参数，由路由层 translate() 渲染为当前语言文本；
    继承 ValueError 以兼容既有的 except ValueError 兜底分支。
    """

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params

def _safe_extract(zip_file: zipfile.ZipFile, dest: Path) -> List[str]:
    """安全解压：路径穿越防护 + zip bomb 防护

    Returns:
        解压出的相对文件名列表

    Raises:
        _PackageError: 校验失败（携带 i18n key 与插值参数）
    """
    infos = zip_file.infolist()
    if len(infos) > MAX_FILE_COUNT:
        raise _PackageError('plugin_package_too_many_files',
                            count=len(infos), limit=MAX_FILE_COUNT)

    total_size = 0
    extracted: List[str] = []
    dest_resolved = dest.resolve()

    for info in infos:
        name = info.filename

        # 统一分隔符并规范化
        normalized = name.replace('\\', '/')
        if normalized.startswith('/') or normalized.startswith('..'):
            raise _PackageError('plugin_package_unsafe_path', path=name)
        if re.match(r'^[A-Za-z]:', normalized):
            raise _PackageError('plugin_package_unsafe_path', path=name)
        parts = [p for p in normalized.split('/') if p not in ('', '.')]
        if '..' in parts:
            raise _PackageError('plugin_package_unsafe_path', path=name)

        # zip bomb 检查
        total_size += info.file_size
        if total_size > MAX_PACKAGE_SIZE:
            raise _PackageError('plugin_package_too_large',
                                limit=MAX_PACKAGE_SIZE // (1024 * 1024))
        if info.compress_size > 0 and info.file_size / info.compress_size > MAX_ENTRY_RATIO:
            raise _PackageError('plugin_package_suspicious_compression', path=name)
        if info.file_size > MAX_PACKAGE_SIZE:
            raise _PackageError('plugin_package_file_too_large', path=name)

        # 安全解压（逐条目）
        target = (dest_resolved / Path(*parts)).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise _PackageError('plugin_package_unsafe_path', path=name)

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
    except zipfile.BadZipFile:
        raise _PackageError('plugin_package_not_valid_zip')

    names = [n.replace('\\', '/') for n in zf.namelist()]
    manifest_names = [n for n in names if n in ('manifest.json', './manifest.json')]
    if not manifest_names:
        raise _PackageError('plugin_manifest_missing_in_package')

    with zf.open(manifest_names[0]) as f:
        try:
            manifest = json.loads(f.read().decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise _PackageError('plugin_manifest_parse_error', error=str(e))

    return manifest, zip_bytes, checksum

class PluginValidationError(Exception):
    """插件操作校验失败（error_code + i18n detail + 插值参数）

    detail 统一使用 i18n key（如 'plugin_entry_missing'），由路由层调用
    translate() 结合 params 渲染为当前语言文本；未命中词条时按原文返回，
    保证与既有硬编码文案的向后兼容。
    """

    def __init__(self, error_code: str, detail: str = '',
                 params: Optional[Dict[str, Any]] = None):
        super().__init__(f'{error_code}: {detail}')
        self.error_code = error_code
        self.detail = detail
        self.params = params or {}

class PluginNotFoundError(Exception):
    """插件资源不存在"""

    def __init__(self, target: str):
        super().__init__(f'plugin resource not found: {target}')
        self.target = target
