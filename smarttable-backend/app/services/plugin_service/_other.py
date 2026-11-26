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

log = logging.getLogger(__name__)

MAX_PACKAGE_SIZE = 50 * 1024 * 1024      # zip 解压总大小上限 50MB

MAX_FILE_COUNT = 500                      # 包内文件数上限

MAX_ENTRY_RATIO = 200                     # 单文件压缩率上限（解压/压缩），防 zip bomb

MAX_ICON_SIZE = 64 * 1024                 # 图标 ≤ 64KB

PLUGIN_STORAGE_ROOT_NAME = 'plugins'      # uploads/ 下插件包根目录

SUPPORTED_API_VERSIONS = {'1'}

ERR_INVALID_PACKAGE = 'INVALID_PACKAGE'

ERR_MANIFEST_INVALID = 'MANIFEST_INVALID'

ERR_ENTRY_MISSING = 'ENTRY_MISSING'

ERR_VERSION_INVALID = 'VERSION_INVALID'

ERR_ENGINES_INCOMPATIBLE = 'ENGINES_INCOMPATIBLE'

ERR_API_VERSION_MISMATCH = 'API_VERSION_MISMATCH'

ERR_DOWNGRADE_FORBIDDEN = 'DOWNGRADE_FORBIDDEN'

ERR_CONFIG_INCOMPATIBLE = 'CONFIG_INCOMPATIBLE'

ERR_PLUGIN_EXISTS_VERSION = 'VERSION_EXISTS'

ERR_PLUGIN_TYPE_NOT_INSTALLABLE = 'PLUGIN_TYPE_NOT_INSTALLABLE'

AUTO_ERROR_FAILURE_THRESHOLD = 5

_host_version_cache: Optional[str] = None

_SEMVER_RE = re.compile(
    r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    r'(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
    r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
    r'(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
)

_PLUGIN_ID_RE = re.compile(r'^[a-z0-9][a-z0-9.-]{2,199}$')

_VALID_PERMISSION_LEVELS = {'read', 'write'}

_VALID_EXTENSION_TYPES = {'toolbar-button', 'side-panel', 'base-menu',
                           'record-detail-block', 'home-menu', 'dashboard-widget'}

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
        except _PackageError as e:
            raise PluginValidationError(ERR_INVALID_PACKAGE, e.key, e.params)
        except ValueError as e:
            raise PluginValidationError(ERR_INVALID_PACKAGE, str(e))

        ok, code, detail, detail_params = _validate_manifest(manifest)
        if not ok:
            raise PluginValidationError(code, detail, detail_params)

        plugin_id = manifest['id']
        version = manifest['version']

        existing = db.session.get(Plugin, plugin_id)

        if existing is not None:
            if existing.current_version == version:
                raise PluginValidationError(
                    ERR_PLUGIN_EXISTS_VERSION,
                    'plugin_version_already_installed',
                    {'plugin_id': plugin_id, 'version': version})
            if not semver_gt(version, existing.current_version):
                raise PluginValidationError(
                    ERR_DOWNGRADE_FORBIDDEN,
                    'plugin_downgrade_forbidden',
                    {'current': existing.current_version, 'uploaded': version})

        # 解包到版本目录
        root = _plugin_storage_root() / plugin_id / version
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        try:
            extracted = _safe_extract(
                zipfile.ZipFile(io.BytesIO(zip_bytes)), root)
        except _PackageError as e:
            shutil.rmtree(root, ignore_errors=True)
            raise PluginValidationError(ERR_INVALID_PACKAGE, e.key, e.params)
        except ValueError as e:
            shutil.rmtree(root, ignore_errors=True)
            raise PluginValidationError(ERR_INVALID_PACKAGE, str(e))

        # 入口文件存在校验（entry 相对于包根）
        entry = manifest['entry']
        if entry not in extracted and f'./{entry}' not in extracted:
            shutil.rmtree(root, ignore_errors=True)
            raise PluginValidationError(
                ERR_ENTRY_MISSING, 'plugin_entry_missing', {'entry': entry})

        # 静态资源文件存在校验（assets.styles / assets.scripts）
        for css in (manifest.get('assets') or {}).get('styles') or []:
            if css not in extracted and f'./{css}' not in extracted:
                shutil.rmtree(root, ignore_errors=True)
                raise PluginValidationError(
                    ERR_ENTRY_MISSING, 'plugin_asset_missing', {'path': css})
        for js in (manifest.get('assets') or {}).get('scripts') or []:
            if js not in extracted and f'./{js}' not in extracted:
                shutil.rmtree(root, ignore_errors=True)
                raise PluginValidationError(
                    ERR_ENTRY_MISSING, 'plugin_asset_missing', {'path': js})

        # endpoints 入口文件存在校验
        for ep in (manifest.get('endpoints') or []):
            ep_entry = ep.get('entry', '')
            if ep_entry not in extracted and f'./{ep_entry}' not in extracted:
                shutil.rmtree(root, ignore_errors=True)
                raise PluginValidationError(
                    ERR_ENTRY_MISSING,
                    'plugin_endpoint_entry_missing', {'path': ep_entry})

        # configSchema 与存量配置兼容性检查（升级时）
        if existing is not None:
            incompatible = cls._check_config_compat(existing.id, manifest.get('configSchema'))
            if incompatible:
                shutil.rmtree(root, ignore_errors=True)
                raise PluginValidationError(
                    ERR_CONFIG_INCOMPATIBLE,
                    'plugin_config_incompatible', {'detail': incompatible})

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

        # 相对路径入库（如 uploads/plugins/<id>/<ver>）：EXE 目录迁移、
        # 临时解压目录重建时记录不失效；resolve_package_path 读取时锚定解析。
        # UPLOAD_FOLDER 为外部绝对路径时回退存绝对路径。
        try:
            package_path = str(root.relative_to(_backend_root()))
        except ValueError:
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
                'plugin_rollback_version_not_retained',
                {'version': target_version, 'plugin_id': plugin_id})

        # 目录必须存在（相对路径按后端根目录锚定解析）
        if not resolve_package_path(ver.package_path).exists():
            raise PluginValidationError(
                ERR_INVALID_PACKAGE, 'plugin_package_files_missing',
                {'path': ver.package_path})

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
            raise PluginValidationError(ERR_MANIFEST_INVALID,
                                        'plugin_invalid_status', {'status': status})
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
        # 仅 UI 插件支持 Base 级安装：脚本插件为纯后端形态，运行由触发者
        # 对 Base 的 RBAC（Editor+）+ 全局启用控制，不依赖 Base 安装
        # （见开发者指南 §5、设计 plan §5；前端 collectExtensionPoints 亦按
        #  type==ui 过滤，脚本插件不进入 UI 扩展点）
        if plugin.type != PluginType.UI:
            raise PluginValidationError(
                ERR_PLUGIN_TYPE_NOT_INSTALLABLE, 'plugin_type_not_installable')
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
                ERR_PLUGIN_TYPE_NOT_INSTALLABLE, 'plugin_type_not_installable')
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
            raise PluginValidationError(ERR_MANIFEST_INVALID,
                                        'plugin_invalid_scope', {'scope': scope})
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
            raise PluginValidationError(ERR_MANIFEST_INVALID,
                                        'plugin_invalid_scope', {'scope': scope})

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
                raise PluginValidationError(
                    ERR_CONFIG_INCOMPATIBLE, 'plugin_config_schema_invalid',
                    {'error': str(e.message if hasattr(e, 'message') else e)})

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
